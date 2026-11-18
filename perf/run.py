# Runs one performance profile from start to end: starts the app, runs Locust, stops the app.
# Use it through ./perf/run.sh, which prepares .venv-perf first:
#
#   ./perf/run.sh smoke                 run the smoke profile of perf/config.toml
#   ./perf/run.sh --list                the profiles
#   ./perf/run.sh soak --config x.toml  another config file
#   ./perf/run.sh smoke --threshold p95_ms=1      override a limit (repeatable), see --help
#
# Steps:
#   1. reads and checks the config (a mistake stops here, before anything starts)
#   2. starts "python app/server.py" as its own process, on a free port, with its own payment mock on another
#      free port and a new temporary database, so it never touches app/shop.db nor an app you have open
#   3. waits for GET /api/v1/health = 200 and for the payment mock to answer
#   4. runs Locust headless with perf/locustfile.py (the scenarios and the stages of the profile), which
#      records every request in results.json
#   5. always stops the app and deletes the temporary database, also after an error or Ctrl+C
#   6. perf/analysis.py turns results.json into the console table, report.html and the threshold checks
#
# Everything of the run is kept in reports/perf/<profile>-<date>-<time>/: results.json (every request),
# report.html (opens offline) and app.log (what the app printed).
#
# Exit code: 0 every threshold passed; 1 a threshold failed (listed with limit and measured value); 2 the run
# could not be done (config mistake, the app did not start or stopped during the run, Locust failed, a bug in
# the scenario code); 130 stopped by Ctrl+C or SIGTERM (the part that ran is still analysed).

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root: "perf" package
from perf import analysis, settings  # noqa: E402 (needs the path above)

REPORTS_DIR = os.path.join(settings.ROOT_DIR, 'reports', 'perf')
LOCUSTFILE = os.path.join(settings.PERF_DIR, 'locustfile.py')

EXIT_OK, EXIT_THRESHOLDS, EXIT_NOT_RUN, EXIT_INTERRUPTED = 0, 1, 2, 130

_locust = None  # the running Locust process, to pass a SIGTERM of the runner on to it


class RunError(Exception):
    """The run could not be done (not a result of the load test)."""


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def answers(url, timeout=1.0):
    """HTTP status of GET url, or None if nothing answers."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, OSError):
        return None


class App:
    """The app under test (app/server.py, which also starts the payment mock) in its own process."""

    def __init__(self, run_dir, token_ttl_seconds):
        self.port, self.payment_port = free_port(), free_port()
        while self.payment_port == self.port:
            self.payment_port = free_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self.payment_url = f'http://127.0.0.1:{self.payment_port}/'
        self.log_path = os.path.join(run_dir, 'app.log')
        self.token_ttl_seconds = token_ttl_seconds
        self.db_dir = None
        self.process = None
        self.log = None

    def start(self, timeout):
        self.db_dir = tempfile.mkdtemp(prefix='perf-shop-db-')
        env = dict(os.environ, APP_PORT=str(self.port), PAYMENT_URL=self.payment_url,
                   PAYMENT_PORT=str(self.payment_port), SHOP_DB=os.path.join(self.db_dir, 'shop.db'),
                   TOKEN_TTL_SECONDS=str(self.token_ttl_seconds), PYTHONUNBUFFERED='1')
        self.log = open(self.log_path, 'w', encoding='utf-8')
        # Own session: Ctrl+C in the terminal reaches Locust (which then prints its summary) but not the app,
        # which keeps answering until the users are done and is stopped here afterwards.
        self.process = subprocess.Popen([sys.executable, os.path.join(settings.ROOT_DIR, 'app', 'server.py')],
                                        cwd=settings.ROOT_DIR, env=env, stdout=self.log, stderr=subprocess.STDOUT,
                                        start_new_session=True)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RunError(f'the app stopped at start (exit code {self.process.returncode}):\n{self.log_tail()}')
            if answers(f'{self.url}/api/v1/health') == 200 and answers(f'{self.payment_url}__requests') == 200:
                return
            time.sleep(0.2)
        raise RunError(f'the app did not answer GET /api/v1/health within {timeout} s:\n{self.log_tail()}')

    def alive(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.log:
            self.log.close()
        if self.db_dir:
            shutil.rmtree(self.db_dir, ignore_errors=True)

    def log_tail(self, lines=15):
        self.log.flush()
        with open(self.log_path, encoding='utf-8', errors='replace') as file:
            return ''.join(file.readlines()[-lines:]).rstrip() or '(app.log is empty)'


def run_locust(config, profile_name, host, results_path):
    """Run Locust in its own process (it patches the standard library with gevent; the runner and the app
    stay normal Python). Returns its exit code (0 or 1 are both normal: errors are judged by the thresholds).

    --skip-log-setup: Locust's own summary table is not shown. Its percentiles are rounded ("approximated"),
    so it would disagree with ours; our table comes from results.json. Locust's warnings still show."""
    command = [sys.executable, '-m', 'locust', '-f', LOCUSTFILE, '--headless', '--host', host,
               '--stop-timeout', str(config['run']['stop_timeout']), '--only-summary', '--skip-log-setup']
    env = dict(os.environ, PERF_CONFIG=config['path'], PERF_PROFILE=profile_name, PERF_RESULTS=results_path)
    global _locust
    process = _locust = subprocess.Popen(command, cwd=settings.ROOT_DIR, env=env)
    try:
        return process.wait()
    except KeyboardInterrupt:
        # Ctrl+C reached Locust too (a SIGTERM is passed on to it as SIGINT): give it time to stop the users
        # and print its summary
        try:
            process.wait(timeout=config['run']['stop_timeout'] + 15)
        except subprocess.TimeoutExpired:
            process.kill()
        raise
    finally:
        _locust = None


def print_profiles(config):
    print(f'Profiles in {os.path.relpath(config["path"], settings.ROOT_DIR)}:')
    for name, profile in config['profiles'].items():
        print(f'  {name:<8} {settings.total_duration(profile):5.0f} s  peak {settings.peak_users(profile):3d} users'
              f'  {profile.get("description", "")}')


def stop_on_sigterm():
    """kill / CI cancel: clean up like Ctrl+C (the app is stopped in the finally below)."""
    def handler(_signum, _frame):
        if _locust is not None and _locust.poll() is None:
            # Passed on as SIGINT (like Ctrl+C): Locust 2.46.6 stops its users and prints its summary on SIGINT,
            # but on SIGTERM it dies at once without a summary
            _locust.send_signal(signal.SIGINT if os.name != 'nt' else signal.SIGTERM)
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='perf/run.sh', description='Run one performance profile against a '
                                     'fresh copy of the local app (started and stopped automatically).')
    parser.add_argument('profile', nargs='?', help='profile of the config file, e.g. smoke')
    parser.add_argument('--config', default=settings.DEFAULT_CONFIG, help='config file (default: perf/config.toml)')
    parser.add_argument('--list', action='store_true', help='show the profiles and stop')
    parser.add_argument('--threshold', action='append', default=[], metavar='[SCOPE:]METRIC=VALUE',
                        help='override a limit of the profile for this run (repeatable). METRIC: p50_ms, p95_ms, '
                             'p99_ms, error_pct. SCOPE: total (default), each_endpoint or an endpoint. Examples: '
                             '--threshold p95_ms=1   --threshold "POST /orders:p99_ms=50"')
    args = parser.parse_args(argv)

    try:
        config = settings.load(args.config)
        if args.list:
            print_profiles(config)
            return EXIT_OK
        if not args.profile:
            print_profiles(config)
            print('\nperf: say which profile to run, e.g. ./perf/run.sh smoke', file=sys.stderr)
            return EXIT_NOT_RUN
        profile = settings.profile(config, args.profile)
        thresholds = settings.apply_overrides(profile['thresholds'], args.threshold)
    except settings.ConfigError as error:
        print(f'perf: config error: {error}', file=sys.stderr)
        return EXIT_NOT_RUN

    run_dir = os.path.join(REPORTS_DIR, f'{args.profile}-{datetime.now():%Y%m%d-%H%M%S}')
    os.makedirs(run_dir, exist_ok=True)
    results_path = os.path.join(run_dir, 'results.json')
    stop_on_sigterm()
    app = App(run_dir, config['run']['token_ttl_seconds'])
    code = None  # decided by the thresholds, unless the run could not be done or was stopped
    try:
        print(f'=== Profile {args.profile}: {profile.get("description", "")}')
        print(f'    {len(profile["stages"])} stage(s), {settings.total_duration(profile):.0f} s, '
              f'peak {settings.peak_users(profile)} users')
        print(f'=== Starting the app on {app.url} (payment mock on {app.payment_url}, temporary database)')
        started = time.monotonic()
        app.start(config['run']['app_start_timeout'])
        print(f'    ready in {time.monotonic() - started:.1f} s')
        print('=== Running Locust')
        locust_code = run_locust(config, args.profile, app.url, results_path)
        if not app.alive():
            raise RunError(f'the app stopped during the run (exit code {app.process.returncode}):\n{app.log_tail()}')
        if locust_code not in (0, 1):
            raise RunError(f'Locust ended with exit code {locust_code}')
    except RunError as error:
        print(f'perf: {error}', file=sys.stderr)
        code = EXIT_NOT_RUN
    except KeyboardInterrupt:
        print('perf: stopped (Ctrl+C or SIGTERM)', file=sys.stderr)
        code = EXIT_INTERRUPTED
    finally:
        print('=== Stopping the app')
        app.stop()

    if os.path.exists(results_path):  # also after Ctrl+C: the part that ran
        try:
            summary, checks, text, html_path = analysis.analyse(
                results_path, thresholds,
                thresholds_source=analysis.source_text(config, args.profile, args.threshold))
        except analysis.ResultsError as error:
            print(f'perf: {error}', file=sys.stderr)
            code = EXIT_NOT_RUN if code is None else code
        else:
            print(text)
            print(f'=== HTML report: {os.path.relpath(html_path, settings.ROOT_DIR)}')
            if code is None:
                if summary['script_errors']:
                    print(f'perf: the scenario code failed {len(summary["script_errors"])} time(s), see SCRIPT ERROR '
                          f'above: the numbers cannot be trusted', file=sys.stderr)
                    code = EXIT_NOT_RUN
                else:
                    code = EXIT_OK if all(check['passed'] for check in checks) else EXIT_THRESHOLDS
    elif code is None:
        print(f'perf: Locust wrote no results file ({os.path.relpath(results_path, settings.ROOT_DIR)})',
              file=sys.stderr)
        code = EXIT_NOT_RUN

    result = {EXIT_OK: 'PASSED (every threshold passed)',
              EXIT_THRESHOLDS: 'FAILED (thresholds failed, see FAILED above)',
              EXIT_NOT_RUN: 'NOT RUN (see the message above)',
              EXIT_INTERRUPTED: 'STOPPED (Ctrl+C or SIGTERM)'}[code]
    print(f'=== Result: {result}, exit code {code}')
    print(f'    Run folder: {os.path.relpath(run_dir, settings.ROOT_DIR)}')
    return code


if __name__ == '__main__':
    sys.exit(main())
