#!/usr/bin/env bash
# Performance tests: one command that prepares .venv-perf, starts the app, runs a profile and stops the app.
#
#   ./perf/run.sh smoke                   run a profile of perf/config.toml: smoke, normal, stress, spike, soak
#   ./perf/run.sh --list                  the profiles, with duration and peak users
#   ./perf/run.sh smoke --config my.toml  another config file
#   ./perf/run.sh smoke --threshold p95_ms=1   override a limit for this run (here one that cannot pass)
#
# Locust lives in its own virtual environment, .venv-perf (perf/requirements.txt), so the test environment
# .venv is not changed. It is created the first time (needs the package index once), later runs reuse it.
# Set PYTHON to create it with another Python (3.11 or newer).
# Each run leaves reports/perf/<profile>-<date>-<time>/: results.json (every request), report.html, app.log.
# Exit code: 0 every threshold passed, 1 a threshold failed, 2 the run could not be done, 130 stopped (see perf/run.py).

set -u
cd "$(dirname "$0")/.." || exit 2

VENV=.venv-perf
if [ ! -d "${VENV}" ]; then
  echo "=== Creating ${VENV}"
  if ! "${PYTHON:-$(command -v python3 || command -v python)}" -m venv "${VENV}"; then
    echo "perf/run.sh: could not create ${VENV} (on Debian/Ubuntu: apt install python3-venv)" >&2
    exit 2
  fi
fi

# Linux / macOS: bin/python; Windows (Git Bash): Scripts/python.exe
PY="${VENV}/bin/python"
[ -x "${PY}" ] || PY="${VENV}/Scripts/python.exe"
if [ ! -x "${PY}" ]; then
  echo "perf/run.sh: ${VENV} has no python; delete ${VENV} and run again" >&2
  exit 2
fi

echo "=== Installing perf/requirements.txt into ${VENV}"
if ! "${PY}" -m pip install --quiet --disable-pip-version-check -r perf/requirements.txt; then
  echo "perf/run.sh: pip install -r perf/requirements.txt failed" >&2
  exit 2
fi

exec "${PY}" perf/run.py "$@"
