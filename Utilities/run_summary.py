# Prints one table with the results of every pytest run of ./run_tests.sh.
#
# Every pytest run saves its counts in reports/summary*.json (root conftest.py). This reads the ones
# written since the pipeline started and prints:
#
#   Category                      Passed  Failed  Skipped  Errors     Time  Report
#   API tests                        113       0        0       0    37.7s  reports/report-api.html
#   ...
#   TOTAL                            429       0       13       0
#
# Run by run_tests.sh; by hand: python -m Utilities.run_summary (every summary file in reports/).
# Exit code 0 when nothing failed, 1 otherwise.

import argparse
import glob
import json
import os
import sys

import pytest

EXIT_NAMES = {code.value: code.name for code in pytest.ExitCode}  # 5: NO_TESTS_COLLECTED...

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
COLUMNS = ('passed', 'failed', 'skipped', 'errors')


def load(since):
    runs = []
    for path in glob.glob(os.path.join(ROOT_DIR, 'reports', 'summary*.json')):  # summary.json, summary-api.json...
        with open(path, encoding='utf-8') as f:
            run = json.load(f)
        if run.get('finished_at', 0) >= since:
            runs.append(run)
    return sorted(runs, key=lambda run: run['finished_at'])


def print_table(runs, total_seconds=None):
    width = max([len('Category'), len('TOTAL')] + [len(run['label']) for run in runs])
    header = f"{'Category':<{width}}  {'Passed':>6}  {'Failed':>6}  {'Skipped':>7}  {'Errors':>6}  {'Time':>7}  Report"
    print()
    print('=' * len(header))
    print('SUMMARY' + (f' (total time {total_seconds / 60:.1f} min)' if total_seconds else ''))
    print('=' * len(header))
    print(header)
    print('-' * len(header))
    for run in runs:
        print(f"{run['label']:<{width}}  {run['passed']:>6}  {run['failed']:>6}  {run['skipped']:>7}  "
              f"{run['errors']:>6}  {run['seconds']:>6.1f}s  {run['report']}")
    print('-' * len(header))
    totals = {column: sum(run[column] for run in runs) for column in COLUMNS}
    print(f"{'TOTAL':<{width}}  {totals['passed']:>6}  {totals['failed']:>6}  {totals['skipped']:>7}  "
          f"{totals['errors']:>6}")
    not_repeated = sum(run['deselected'] for run in runs if run.get('later_device_run'))
    filtered = sum(run['deselected'] for run in runs if not run.get('later_device_run'))
    if not_repeated:
        print(f'(+ {not_repeated} not repeated on the later devices: they already ran with the first one)')
    if filtered:
        print(f'(+ {filtered} left out by -k / -m)')
    for run in runs:  # a run can end badly without a failed test, e.g. nothing matched -k
        if run['exit_status'] not in (0, 1):
            print(f"({run['label']}: pytest ended with {EXIT_NAMES.get(run['exit_status'], run['exit_status'])})")
    ok = bool(runs) and totals['failed'] == 0 and totals['errors'] == 0 and \
        all(run['exit_status'] == 0 for run in runs)
    print(f"RESULT: {'ALL PASSED' if ok else 'NOT PASSED' if runs else 'NO RESULTS'}")
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description='Summary table of the test runs')
    parser.add_argument('--since', type=float, default=0, help='only runs that finished after this Unix time')
    parser.add_argument('--total-seconds', type=float, default=None)
    args = parser.parse_args(argv)
    return 0 if print_table(load(args.since), args.total_seconds) else 1


if __name__ == '__main__':
    sys.exit(main())
