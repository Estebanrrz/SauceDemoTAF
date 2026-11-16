#!/usr/bin/env bash
# Local pipeline: prepares .venv (setup.sh), runs the suite and leaves the HTML reports in reports/.
#
#   ./run_tests.sh                        everything: Playwright, Selenium, then Playwright on every device
#   ./run_tests.sh playwright             only Playwright (desktop)
#   ./run_tests.sh selenium               only Selenium
#   ./run_tests.sh mobile                 only Playwright on every device below
#   ./run_tests.sh "iPhone 13, Pixel 7"   only Playwright on those devices (any Playwright device names)
#
# Anything after the first argument goes to pytest, e.g. run the devices at the same time:
#   ./run_tests.sh mobile --parallel
#
# Each run writes its own report (reports/report.html, report-selenium.html, report-pixel-7.html...).
# Nothing has to be running or installed before: setup.sh creates .venv if needed and the suite
# starts the local app by itself. Exits with 1 if any test fails.

set -u
cd "$(dirname "$0")"

. ./setup.sh || exit 1

DEVICES="iPhone 13, Pixel 7, iPhone 13 landscape, iPad Mini"
EXTRA=("${@:2}")

case "${1:-all}" in
  all)    RUNS=(playwright selenium "${DEVICES}") ;;
  mobile) RUNS=("${DEVICES}") ;;
  *)      RUNS=("$1") ;;
esac

STATUS=0
for RUN in "${RUNS[@]}"; do
  if [ "${RUN}" = "playwright" ] || [ "${RUN}" = "selenium" ]; then
    echo "=== Engine: ${RUN}"
    python -m pytest --engine="${RUN}" ${EXTRA[@]+"${EXTRA[@]}"} || STATUS=1
  else
    echo "=== Engine: playwright, devices: ${RUN}"
    python -m pytest --engine=playwright --device="${RUN}" ${EXTRA[@]+"${EXTRA[@]}"} || STATUS=1
  fi
done

exit ${STATUS}
