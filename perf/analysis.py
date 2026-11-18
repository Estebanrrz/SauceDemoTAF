# Analysis of one performance run, from its results file only (reports/perf/<run>/results.json).
#
# The results file holds every request of the run (time, endpoint, response time, error). From it this module
# computes ONE summary, and the console table, the HTML report and the threshold checks are all made from that
# same summary with the same number formatting, so they always show the same numbers.
#
# perf/run.py calls it at the end of every run. To look at a run again (or check it against other limits):
#
#   python3 perf/analysis.py reports/perf/smoke-20261118-100737/results.json
#   python3 perf/analysis.py <results.json> --threshold p95_ms=1     (exit code 1: that limit fails)
# It writes report-reanalysed.html (or --html FILE), never the report.html of the run itself.
#
# Standard library only, so any Python 3.11+ can run it.
#
# Definitions (also printed in the HTML report):
#   requests   all requests recorded (also those of the login/logout around the flows)
#   errors     requests with a wrong answer (see perf/locustfile.py); the expected 402 of the declined card is
#              not an error
#   error %    errors / requests * 100, rounded UP to 2 decimals, so one error is never shown as 0.00
#   p50/95/99  nearest-rank percentile of the response times: the smallest time that at least that % of the
#              requests did not exceed (an actual measured value, not interpolated), rounded to 0.1 ms
#   req/s      requests / duration of the run (from the start of the load until the last user stopped)
# The thresholds compare exactly these rounded values, so the number shown is the number checked.

import argparse
import html
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root: "perf" package
from perf import settings  # noqa: E402 (needs the path above)

TOTAL = 'TOTAL'
UNITS = {'p50_ms': 'ms', 'p95_ms': 'ms', 'p99_ms': 'ms', 'error_pct': '%'}


class ResultsError(Exception):
    """The results file is missing or is not a results file."""


# ---- numbers ----

def percentile(sorted_values, percent):
    """Nearest-rank percentile of an already sorted list."""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(percent / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def error_pct(errors, requests):
    if not requests:
        return None
    return math.ceil(errors / requests * 100 * 100 - 1e-9) / 100  # rounded up to 2 decimals


def row_for(name, times, errors, duration):
    times = sorted(times)
    requests = len(times)
    def ms(percent):
        value = percentile(times, percent)
        return None if value is None else round(value, 1)
    return {'endpoint': name, 'requests': requests, 'errors': errors, 'error_pct': error_pct(errors, requests),
            'p50_ms': ms(50), 'p95_ms': ms(95), 'p99_ms': ms(99),
            'rps': round(requests / duration, 2) if duration else None}


def fmt(metric, value):
    """The one formatting of every number, used by the console and the HTML alike."""
    if value is None:
        return '-'
    if metric in ('requests', 'errors'):
        return str(value)
    if metric.endswith('_ms'):
        return f'{value:.1f}'
    return f'{value:.2f}'  # error_pct, rps


def fmt_limit(value):
    return f'{value:g}'


# ---- results file -> summary ----

def load_results(path):
    try:
        with open(path, encoding='utf-8') as file:
            results = json.load(file)
    except FileNotFoundError:
        raise ResultsError(f'no results file at {path}')
    except ValueError as error:
        raise ResultsError(f'{path} is not valid JSON: {error}')
    if not isinstance(results, dict) or results.get('format') != 1 or not isinstance(results.get('samples'), list):
        raise ResultsError(f'{path} is not a results file of perf/run.py (format 1)')
    return results


def summarize(results):
    duration = results['duration_s']
    times, errors = defaultdict(list), Counter()
    messages = Counter()
    for t_s, endpoint, response_ms, error in results['samples']:
        times[endpoint].append(response_ms)
        if error is not None:
            errors[endpoint] += 1
            messages[(endpoint, error)] += 1
    order = [name for name in settings.ENDPOINTS if name in times] + sorted(set(times) - set(settings.ENDPOINTS))
    rows = [row_for(name, times[name], errors[name], duration) for name in order]
    total = row_for(TOTAL, [ms for name in order for ms in times[name]], sum(errors.values()), duration)
    return {
        'profile': results['profile'], 'description': results.get('description', ''),
        'stages': results.get('stages', []), 'locust_version': results.get('locust_version', '?'),
        'started_at': results['started_at'], 'duration_s': duration,
        'rows': rows, 'total': total,
        'errors': [{'endpoint': endpoint, 'message': message, 'count': count}
                   for (endpoint, message), count in messages.most_common()],
        'script_errors': results.get('script_errors', []),
        'timeline': timeline(results),
    }


def timeline(results):
    """Per time bucket (about 100 of them): requests/s, errors, p95 and users, for the charts."""
    duration = max(results['duration_s'], 1)
    size = max(1, math.ceil(duration / 100))
    buckets = defaultdict(list)
    for t_s, _endpoint, response_ms, error in results['samples']:
        buckets[int(t_s // size)].append((response_ms, error is not None))
    users = defaultdict(int)
    for t_s, count in results.get('users', []):
        users[int(t_s // size)] = max(users[int(t_s // size)], count)
    points = []
    for index in range(int(math.ceil(duration / size))):
        bucket = buckets.get(index, [])
        points.append({'t_s': index * size, 'rps': round(len(bucket) / size, 2),
                       'errors': sum(1 for _, failed in bucket if failed),
                       'p95_ms': percentile(sorted(ms for ms, _ in bucket), 95), 'users': users.get(index, 0)})
    return {'bucket_s': size, 'points': points}


# ---- thresholds ----

def evaluate(summary, thresholds):
    """One check per limit: total, every endpoint that had requests (each_endpoint merged with its own limits),
    and endpoints with their own limits but no requests at all (those fail: nothing was measured)."""
    checks = []

    def add(scope, limits, row):
        for metric in settings.METRICS:
            if metric not in limits:
                continue
            measured = row[metric] if row else None
            checks.append({'scope': scope, 'metric': metric, 'limit': limits[metric], 'measured': measured,
                           'passed': measured is not None and measured <= limits[metric]})

    add('total', thresholds['total'], summary['total'])
    measured_rows = {row['endpoint']: row for row in summary['rows']}
    for name in [name for name in settings.ENDPOINTS if name in measured_rows or name in thresholds['endpoints']]:
        limits = {**thresholds['each_endpoint'], **thresholds['endpoints'].get(name, {})}
        add(name, limits, measured_rows.get(name))
    return checks


def describe(check):
    unit = UNITS[check['metric']]
    if check['measured'] is None:
        return f"{check['scope']} {check['metric']}: no requests measured (limit {fmt_limit(check['limit'])} {unit})"
    sign = '<=' if check['passed'] else '>'
    return (f"{check['scope']} {check['metric']}: measured {fmt(check['metric'], check['measured'])} {unit} "
            f"{sign} limit {fmt_limit(check['limit'])} {unit}")


def used(check):
    """How much of the limit the measured value uses, in % (None when it cannot be said)."""
    if check['measured'] is None:
        return None
    if check['limit'] == 0:
        return 0.0 if check['measured'] == 0 else math.inf
    return check['measured'] / check['limit'] * 100


# ---- console ----

COLUMNS = (('requests', 'Requests'), ('errors', 'Errors'), ('error_pct', 'Error %'), ('p50_ms', 'p50 ms'),
           ('p95_ms', 'p95 ms'), ('p99_ms', 'p99 ms'), ('rps', 'Req/s'))


def console_report(summary, checks, results_path=None):
    width = max(len(TOTAL), *(len(row['endpoint']) for row in summary['rows'])) if summary['rows'] else len(TOTAL)
    header = f'{"Endpoint":<{width}}' + ''.join(f'{title:>10}' for _, title in COLUMNS)
    line = '-' * len(header)
    out = [f'=== Results of profile {summary["profile"]}: {summary["duration_s"]:.1f} s'
           + (f' ({os.path.relpath(results_path)})' if results_path else ''), line, header, line]
    for row in summary['rows'] + [None, summary['total']]:
        if row is None:
            out.append(line)
            continue
        out.append(f'{row["endpoint"]:<{width}}' + ''.join(f'{fmt(key, row[key]):>10}' for key, _ in COLUMNS))
    out.append(line)
    if summary['errors']:
        out.append(f'Errors ({summary["total"]["errors"]}):')
        for error in summary['errors'][:10]:
            out.append(f'  {error["count"]:5d} x {error["endpoint"]}: {error["message"]}')
        if len(summary['errors']) > 10:
            out.append(f'  ... and {len(summary["errors"]) - 10} other error messages (see the HTML report)')
    for message in summary['script_errors'][:10]:
        out.append(f'  SCRIPT ERROR (a bug in perf/locustfile.py): {message}')

    failed = [check for check in checks if not check['passed']]
    verdict = f'{len(failed)} FAILED' if failed else 'all passed'
    out.append(f'=== Thresholds of profile {summary["profile"]}: {len(checks)} checks, {verdict}')
    for check in failed:
        out.append(f'  FAILED  {describe(check)}')
    closest = sorted((check for check in checks if check['passed'] and used(check)),
                     key=used, reverse=True)[:3]
    if closest:
        out.append('  Closest to their limit: ' + '; '.join(
            f"{check['scope']} {check['metric']} {fmt(check['metric'], check['measured'])} of "
            f"{fmt_limit(check['limit'])} ({used(check):.0f}%)" for check in closest))
    return '\n'.join(out)


# ---- HTML (one file, no scripts, no external files: opens offline) ----

def svg_chart(points, key, title, unit, color, stage_ends, bars=False):
    width, height, left, bottom, top = 760, 170, 52, 24, 12
    values = [point[key] for point in points]
    present = [value for value in values if value is not None]
    x_max = max((point['t_s'] for point in points), default=0) + (points[1]['t_s'] - points[0]['t_s']
                                                                   if len(points) > 1 else 1)
    y_max = max(present, default=0) or 1
    y_max = y_max * 1.1

    def x(t):
        return left + (width - left - 8) * t / x_max

    def y(value):
        return top + (height - top - bottom) * (1 - value / y_max)

    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{html.escape(title)}">',
             f'<text x="{left}" y="10" class="ct">{html.escape(title)}</text>']
    for fraction in (0, 0.5, 1):
        value = y_max / 1.1 * fraction
        parts.append(f'<line x1="{left}" x2="{width - 8}" y1="{y(value):.1f}" y2="{y(value):.1f}" class="grid"/>'
                     f'<text x="{left - 6}" y="{y(value) + 4:.1f}" class="ax" text-anchor="end">{value:.3g}</text>')
    for end in stage_ends[:-1]:
        parts.append(f'<line x1="{x(end):.1f}" x2="{x(end):.1f}" y1="{top}" y2="{height - bottom}" class="stage"/>')
    for t in range(0, int(x_max) + 1, max(1, int(x_max // 6) or 1)):
        parts.append(f'<text x="{x(t):.1f}" y="{height - 6}" class="ax" text-anchor="middle">{t}s</text>')
    if bars:
        step = (width - left - 8) / max(len(points), 1)
        for point in points:
            if point[key]:
                parts.append(f'<rect x="{x(point["t_s"]):.1f}" y="{y(point[key]):.1f}" width="{max(step - 1, 1):.1f}"'
                             f' height="{height - bottom - y(point[key]):.1f}" fill="{color}"/>')
    else:
        segment = []
        for point in points + [{'t_s': 0, key: None}]:
            if point[key] is None:
                if segment:
                    parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.8" '
                                 f'points="{" ".join(segment)}"/>')
                segment = []
            else:
                segment.append(f'{x(point["t_s"]):.1f},{y(point[key]):.1f}')
    parts.append(f'<text x="{width - 8}" y="10" class="ax" text-anchor="end">{html.escape(unit)}</text></svg>')
    return ''.join(parts)


CSS = '''
body{font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:24px auto;max-width:1000px;color:#222;padding:0 16px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid #ddd;padding-bottom:4px}
.meta{color:#555}.verdict{padding:10px 14px;border-radius:6px;font-weight:600;margin:14px 0}
.pass{background:#e6f4ea;color:#145c2c;border:1px solid #9bd3ab}.fail{background:#fce8e6;color:#8a1c12;border:1px solid #f0a8a0}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:4px 8px;border-bottom:1px solid #eee;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{background:#f6f6f6;font-weight:600}
tr.total td{font-weight:700;border-top:2px solid #999}td.msg{text-align:left;white-space:normal}
tr.bad td{background:#fdeceb}.ok{color:#145c2c}.no{color:#8a1c12;font-weight:700}
.chart{width:100%;height:auto;margin:6px 0 10px}.chart .ct{font-size:12px;font-weight:600}
.chart .ax{font-size:10px;fill:#666}.chart .grid{stroke:#eee}.chart .stage{stroke:#bbb;stroke-dasharray:4 3}
.note{color:#555;font-size:13px}code{background:#f3f3f3;padding:1px 4px;border-radius:3px}
'''


def html_report(summary, checks, thresholds_source=''):
    esc = html.escape
    failed = [check for check in checks if not check['passed']]
    started = datetime.fromtimestamp(summary['started_at']).strftime('%Y-%m-%d %H:%M:%S')
    stages = ', '.join(f"{stage['users']} users for {fmt_limit(stage['duration'])} s" for stage in summary['stages'])
    out = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
           f'<title>Performance: {esc(summary["profile"])} {started}</title><style>{CSS}</style></head><body>',
           f'<h1>Performance run: {esc(summary["profile"])}</h1>',
           f'<div class="meta">{esc(summary["description"])}<br>Started {started}, lasted '
           f'{summary["duration_s"]:.1f} s. Stages: {esc(stages)}. Locust {esc(summary["locust_version"])}.</div>']
    if failed:
        out.append(f'<div class="verdict fail">FAILED: {len(failed)} of {len(checks)} thresholds failed<ul>'
                   + ''.join(f'<li>{esc(describe(check))}</li>' for check in failed) + '</ul></div>')
    else:
        out.append(f'<div class="verdict pass">PASSED: all {len(checks)} thresholds passed</div>')
    if summary['script_errors']:
        out.append('<div class="verdict fail">The scenario code itself failed (a bug in perf/locustfile.py):<ul>'
                   + ''.join(f'<li>{esc(message)}</li>' for message in summary['script_errors'][:20]) + '</ul></div>')

    out.append('<h2>Per endpoint and in total</h2><table><tr><th>Endpoint</th>'
               + ''.join(f'<th>{esc(title)}</th>' for _, title in COLUMNS) + '</tr>')
    for row in summary['rows'] + [summary['total']]:
        css = ' class="total"' if row['endpoint'] == TOTAL else (' class="bad"' if row['errors'] else '')
        out.append(f'<tr{css}><td>{esc(row["endpoint"])}</td>'
                   + ''.join(f'<td>{fmt(key, row[key])}</td>' for key, _ in COLUMNS) + '</tr>')
    out.append('</table>')

    out.append(f'<h2>Thresholds</h2><p class="note">{esc(thresholds_source)}</p><table><tr><th>Scope</th>'
               '<th>Limit on</th><th>Limit</th><th>Measured</th><th>Of the limit</th><th>Result</th></tr>')
    for check in checks:
        share = used(check)
        share_text = '-' if share is None else ('over' if share == math.inf else f'{share:.0f}%')
        unit = UNITS[check['metric']]
        out.append(f'<tr{"" if check["passed"] else " class=bad"}><td>{esc(check["scope"])}</td>'
                   f'<td>{check["metric"]}</td><td>{fmt_limit(check["limit"])} {unit}</td>'
                   f'<td>{fmt(check["metric"], check["measured"])} {unit if check["measured"] is not None else ""}</td>'
                   f'<td>{share_text}</td>'
                   f'<td class="{"ok" if check["passed"] else "no"}">{"passed" if check["passed"] else "FAILED"}</td></tr>')
    out.append('</table>')

    out.append('<h2>Errors</h2>')
    if summary['errors']:
        out.append('<table><tr><th>Endpoint</th><th>Count</th><th>Message</th></tr>' + ''.join(
            f'<tr><td>{esc(error["endpoint"])}</td><td>{error["count"]}</td><td class="msg">{esc(error["message"])}</td></tr>'
            for error in summary['errors']) + '</table>')
    else:
        out.append('<p>No errors.</p>')

    points = summary['timeline']['points']
    ends, elapsed = [], 0
    for stage in summary['stages']:
        elapsed += stage['duration']
        ends.append(elapsed)
    bucket = summary['timeline']['bucket_s']
    out.append(f'<h2>Over time</h2><p class="note">Per {bucket} s; dashed lines: start of the next stage.</p>')
    out.append(svg_chart(points, 'users', 'Active users', 'users', '#6a5acd', ends))
    out.append(svg_chart(points, 'rps', 'Requests per second', 'req/s', '#1f77b4', ends))
    out.append(svg_chart(points, 'p95_ms', 'p95 response time', 'ms', '#e67e22', ends))
    out.append(svg_chart(points, 'errors', 'Errors', 'errors', '#c0392b', ends, bars=True))

    out.append('<h2>How the numbers are made</h2><ul class="note">'
               '<li>Everything on this page comes from <code>results.json</code> in the same folder (every request '
               'of the run); the console table shows the same numbers.</li>'
               '<li><b>Errors</b>: wrong status code, no JSON, wrong data, or no answer in time. The expected 402 '
               'of the declined card is not an error. <b>Error %</b> is rounded up to 2 decimals.</li>'
               '<li><b>p50 / p95 / p99</b>: nearest-rank percentiles of the measured response times, in ms, '
               'rounded to 0.1 ms. With few requests (e.g. 3 logins) p95 and p99 are the slowest one.</li>'
               '<li><b>Req/s</b>: requests divided by the duration of the run.</li>'
               '<li>The thresholds compare exactly the numbers shown.</li></ul></body></html>')
    return '\n'.join(out)


# ---- everything at once ----

def analyse(results_path, thresholds, html_path=None, thresholds_source=''):
    """Summary, checks, console text; writes the HTML report. The single place that turns a results file
    into what the user sees."""
    results = load_results(results_path)
    summary = summarize(results)
    checks = evaluate(summary, thresholds)
    html_path = html_path or os.path.join(os.path.dirname(os.path.abspath(results_path)), 'report.html')
    with open(html_path, 'w', encoding='utf-8') as file:
        file.write(html_report(summary, checks, thresholds_source))
    return summary, checks, console_report(summary, checks, results_path), html_path


def main(argv=None):
    parser = argparse.ArgumentParser(prog='perf/analysis.py', description='Table, HTML report and thresholds '
                                     'of a finished run, from its results.json')
    parser.add_argument('results', help='reports/perf/<run>/results.json')
    parser.add_argument('--config', default=settings.DEFAULT_CONFIG, help='config with the thresholds')
    parser.add_argument('--threshold', action='append', default=[], metavar='[SCOPE:]METRIC=VALUE',
                        help='override a limit, e.g. p95_ms=1 or "POST /orders:p99_ms=50" (repeatable)')
    parser.add_argument('--html', help='where to write the HTML report (default: report-reanalysed.html next to '
                        'the results file; the report.html of the run itself is never overwritten)')
    args = parser.parse_args(argv)
    try:
        config = settings.load(args.config)
        results = load_results(args.results)
        thresholds = settings.apply_overrides(settings.profile(config, results['profile'])['thresholds'],
                                              args.threshold)
        html_path = args.html or os.path.join(os.path.dirname(os.path.abspath(args.results)),
                                              'report-reanalysed.html')
        summary, checks, text, html_path = analyse(
            args.results, thresholds, html_path=html_path,
            thresholds_source=source_text(config, results['profile'], args.threshold))
    except (settings.ConfigError, ResultsError) as error:
        print(f'perf: {error}', file=sys.stderr)
        return 2
    print(text)
    print(f'=== HTML report: {os.path.relpath(html_path)}')
    return 0 if all(check['passed'] for check in checks) else 1


def source_text(config, profile, overrides):
    path = config['path']
    inside = os.path.commonpath([path, settings.ROOT_DIR]) == settings.ROOT_DIR
    where = f'Limits of profile {profile} in {os.path.relpath(path, settings.ROOT_DIR) if inside else path}'
    return where + (f', with from the command line: {", ".join(overrides)}' if overrides else '') + '.'


if __name__ == '__main__':
    sys.exit(main())
