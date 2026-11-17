# Start a separate copy of the shop app, with its own settings, port and empty database.
#
# For tests of settings that must not change the app the rest of the run uses, e.g. a token lifetime of
# 2 seconds (TOKEN_TTL_SECONDS=2). It is started exactly like a person would: python app/server.py with
# environment variables. Everything stays local: no internet needed.

import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager

import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT_DIR, 'app', 'server.py')


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run_app(settings, timeout=30):
    """Start python app/server.py with these environment variables and wait until it stops.
    Returns (exit code, what it printed on stderr). For settings that must stop the app at once."""
    env = dict(os.environ, APP_PORT=str(free_port()), SHOP_DB=os.path.join(tempfile.mkdtemp(), 'shop.db'),
               **settings)
    result = subprocess.run([sys.executable, SERVER], env=env, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stderr


@contextmanager
def separate_app(settings, startup_seconds=20):
    """Run python app/server.py with these extra environment variables; yields its base URL."""
    port = free_port()
    with tempfile.TemporaryDirectory(prefix='separate-app-') as folder:
        env = dict(os.environ, APP_PORT=str(port), SHOP_DB=os.path.join(folder, 'shop.db'), **settings)
        log = open(os.path.join(folder, 'server.log'), 'w')
        process = subprocess.Popen([sys.executable, SERVER], env=env, stdout=log, stderr=subprocess.STDOUT)
        url = f'http://127.0.0.1:{port}/'
        try:
            deadline = time.monotonic() + startup_seconds
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f'The separate app stopped at start: {open(log.name).read()}')
                try:
                    if requests.get(url + 'api/v1/health', timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError(f'The separate app did not start in {startup_seconds}s')
                time.sleep(0.2)
            yield url
        finally:
            process.terminate()
            process.wait(timeout=10)
            log.close()
