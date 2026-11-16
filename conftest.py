# Root conftest: registers the --engine and --device options.
#
#   pytest                                Playwright (default), headless
#   pytest --engine=selenium              same tests on Selenium
#   pytest --device="iPhone 13"           Playwright emulating a phone (any Playwright device name)
#   pytest --device="iPhone 13, Pixel 7"  the suite once per device, one after the other
#   pytest --device="iPhone 13, Pixel 7" --parallel   the same, all devices at the same time
#
# Every run writes its own HTML report unless --html is given: reports/report.html (Playwright,
# desktop), reports/report-selenium.html, reports/report-iphone-13.html (--device="iPhone 13")...

import os
import re
import subprocess
import sys
import tempfile
import time

import pytest

from Core.factory import DEFAULT_ENGINE, ENGINES, resolve_device
from Utilities.readProperties import ReadConfig

# Set by the parent run for every device but the first: the all_devices tests already check every
# device by themselves, so they run once per pytest call and are deselected in the other runs
ALREADY_RAN_ENV = 'TAF_ALL_DEVICES_TESTS_RAN'


def pytest_addoption(parser):
    parser.addoption(
        '--engine',
        action='store',
        default=None,
        choices=list(ENGINES),
        help=f'Browser engine to run the tests with (default: {DEFAULT_ENGINE})',
    )
    parser.addoption(
        '--device',
        action='store',
        default=None,
        help='Playwright only: emulate a device, e.g. --device="iPhone 13", or several separated by commas, '
             'each with its own run and report (default: desktop 1280x900)',
    )
    parser.addoption(
        '--parallel',
        action='store_true',
        default=False,
        help='With several devices: run them all at the same time instead of one after the other',
    )


def report_path(engine, device):
    """reports/report.html for Playwright on desktop; otherwise the engine or device goes in the name."""
    name = device or (engine if engine != DEFAULT_ENGINE else '')
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return f'reports/report-{slug}.html' if slug else 'reports/report.html'


EXIT_NAMES = {code.value: code.name for code in pytest.ExitCode}  # 0 OK, 1 TESTS_FAILED...


def resolve_devices(engine, value):
    """'iphone 13, Pixel 7' -> ['iPhone 13', 'Pixel 7'] (exact Playwright names, no repeats).
    One UsageError listing every wrong device, so nothing runs if any of them is wrong."""
    names, errors = [], []
    for device in (d.strip() for d in (value or '').split(',')):
        if not device:
            continue
        try:
            name = resolve_device(engine, device)
        except ValueError as error:
            if str(error) not in errors:
                errors.append(str(error))
            continue
        if name not in names:
            names.append(name)
    if errors:
        raise pytest.UsageError('\n'.join(errors))
    return names


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config):
    """Runs before any test is collected: check --device, and with several devices run pytest once per
    device (each run is a normal single-device run with its own report), then print a summary."""
    if config.option.help or config.option.version:
        return None
    engine = config.getoption('--engine') or ReadConfig.getDefaultEngine()
    devices = resolve_devices(engine, config.getoption('--device') or ReadConfig.getDevice())
    if len(devices) < 2:
        config.option.device = devices[0] if devices else None
        return None  # normal run
    if getattr(config.option, 'htmlpath', None):
        raise pytest.UsageError('--html cannot be used with several devices: each device writes its own report')

    # The last --device wins, so the same command runs with only that device
    commands = {device: [sys.executable, '-m', 'pytest', *config.invocation_params.args, f'--device={device}']
                for device in devices}
    envs = {device: dict(os.environ, **({ALREADY_RAN_ENV: devices[0]} if device != devices[0] else {}))
            for device in devices}
    parallel = config.getoption('--parallel')
    from app.server import start_if_needed
    stop_app = start_if_needed(ReadConfig.getApplicationUrl())  # one app for all runs: no race for the port
    started = time.monotonic()
    try:
        run = run_at_the_same_time if parallel else run_one_after_the_other
        results = run(commands, envs, config.invocation_params.dir)
    except KeyboardInterrupt:
        print('\n=== Interrupted: the device runs were stopped', flush=True)
        return pytest.ExitCode.INTERRUPTED
    finally:
        stop_app()
    total = time.monotonic() - started

    how = 'at the same time' if parallel else 'one after the other'
    print(f'\n=== Devices: {len(devices)} runs {how}, {total:.1f}s in total')
    for device, (code, seconds) in results.items():
        result = EXIT_NAMES.get(code, f'exit code {code}')
        print(f'  {device:<22} {result:<20} {seconds:6.1f}s  {report_path(engine, device)}')
    return next((code for code, _ in results.values() if code), 0)


def run_one_after_the_other(commands, envs, cwd):
    """{device: (exit code, seconds)}; the output of each run goes straight to the console."""
    results = {}
    for number, (device, command) in enumerate(commands.items(), 1):
        print(f'\n=== Device {number}/{len(commands)}: {device}', flush=True)
        started = time.monotonic()
        code = subprocess.call(command, cwd=cwd, env=envs[device])
        results[device] = (code, time.monotonic() - started)
    return results


def run_at_the_same_time(commands, envs, cwd):
    """{device: (exit code, seconds)}. Every run writes to its own temporary file, printed in one block
    when the run ends, so the lines of different devices do not mix."""
    print(f'\n=== Starting {len(commands)} devices at the same time: {", ".join(commands)}', flush=True)
    started = time.monotonic()
    running, results = {}, {}
    try:
        for device, command in commands.items():
            output = tempfile.TemporaryFile()
            process = subprocess.Popen(command, cwd=cwd, env=envs[device], stdout=output, stderr=subprocess.STDOUT)
            running[device] = (process, output)
        while len(results) < len(running):
            for device, (process, output) in running.items():
                if device in results or process.poll() is None:
                    continue
                results[device] = (process.returncode, time.monotonic() - started)
                print(f'\n=== Device {len(results)}/{len(commands)} finished: {device}', flush=True)
                output.seek(0)
                sys.stdout.write(output.read().decode(errors='replace'))
                sys.stdout.flush()
            time.sleep(0.2)
    finally:  # Ctrl+C or an error: do not leave runs behind
        for process, output in running.values():
            if process.poll() is None:
                process.terminate()
                process.wait()
            output.close()
    return {device: results[device] for device in commands}


def pytest_collection_modifyitems(config, items):
    """In a device run started by a several-devices run (not the first one), leave out the
    all_devices tests: the first device run already ran them."""
    first_device = os.environ.get(ALREADY_RAN_ENV)
    if not first_device:
        return
    deselected = [item for item in items if item.get_closest_marker('all_devices')]
    if deselected:
        items[:] = [item for item in items if not item.get_closest_marker('all_devices')]
        config.hook.pytest_deselected(items=deselected)


@pytest.hookimpl(tryfirst=True)  # before pytest-html reads --html
def pytest_configure(config):
    engine = config.getoption('--engine') or ReadConfig.getDefaultEngine()
    if hasattr(config.option, 'htmlpath') and not config.option.htmlpath:
        config.option.htmlpath = report_path(engine, config.option.device)


def pytest_report_header(config):
    engine = config.getoption('--engine') or ReadConfig.getDefaultEngine()
    device = config.getoption('--device') or 'desktop'
    header = [f'engine: {engine}, device: {device}, base url: {ReadConfig.getApplicationUrl()}, '
              f'headless: {ReadConfig.isHeadless()}']
    if os.environ.get(ALREADY_RAN_ENV):
        header.append(f'all_devices tests: left out (deselected), they already ran with {os.environ[ALREADY_RAN_ENV]}')
    return header
