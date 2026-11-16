#!/usr/bin/env bash
# Prepares the Python environment: creates .venv only if it is missing, activates it and installs
# requirements.txt (quick when everything is already installed; no internet needed then).
#
#   ./setup.sh          prepare .venv
#   source setup.sh     prepare .venv and keep it activated in your shell
#
# run_tests.sh sources it, so the tests always run with the pinned packages.
# .venv is created with python3 (or python); set PYTHON to use another one.
# On an error it stops: "return" when sourced, "exit" when run as a script.

_setup_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "${_setup_root}/.venv" ]; then
  echo "=== Creating .venv"
  if ! "${PYTHON:-$(command -v python3 || command -v python)}" -m venv "${_setup_root}/.venv"; then
    echo "setup.sh: could not create .venv (on Debian/Ubuntu: apt install python3-venv)" >&2
    return 1 2>/dev/null || exit 1
  fi
fi

# Linux / macOS: bin/activate; Windows (Git Bash): Scripts/activate
_setup_activate="${_setup_root}/.venv/bin/activate"
[ -f "${_setup_activate}" ] || _setup_activate="${_setup_root}/.venv/Scripts/activate"
if [ ! -f "${_setup_activate}" ]; then
  echo "setup.sh: .venv has no activate script; delete .venv and run again" >&2
  return 1 2>/dev/null || exit 1
fi
. "${_setup_activate}"

echo "=== Installing requirements.txt into .venv"
if ! python -m pip install --quiet --disable-pip-version-check -r "${_setup_root}/requirements.txt"; then
  echo "setup.sh: pip install -r requirements.txt failed" >&2
  return 1 2>/dev/null || exit 1
fi
