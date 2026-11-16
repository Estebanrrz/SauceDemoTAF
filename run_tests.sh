#!/usr/bin/env bash
# Local pipeline: runs the whole suite and leaves the HTML reports in reports/.
#
#   ./run_tests.sh              both engines (Playwright, then Selenium)
#   ./run_tests.sh playwright   only Playwright
#   ./run_tests.sh selenium     only Selenium
#
# Nothing has to be running before: the suite starts the local app by itself.
# Exits with 1 if any test fails.

set -u
cd "$(dirname "$0")"

PY="${PYTHON:-$(command -v python3 || command -v python)}"

if [ $# -eq 0 ]; then
  ENGINES=(playwright selenium)
else
  ENGINES=("$1")
fi

STATUS=0
for ENGINE in "${ENGINES[@]}"; do
  REPORT="reports/report.html"
  [ "${ENGINE}" != "playwright" ] && REPORT="reports/report-${ENGINE}.html"
  echo "=== Engine: ${ENGINE}"
  "${PY}" -m pytest --engine="${ENGINE}" --html="${REPORT}" --self-contained-html || STATUS=1
  echo "=== Report: ${REPORT}"
done

exit ${STATUS}
