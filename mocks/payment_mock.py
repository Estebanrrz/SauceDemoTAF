# Mock of the external payment service. The shop never talks to a real card company: the orders API
# posts every charge here (PAYMENT_URL, default http://127.0.0.1:5056/).
#
# What it answers depends only on the card ("magic cards", like the test cards of real providers), so
# it needs no set-up calls and parallel runs cannot disturb each other:
#
#   any other card               201 {"status": "approved", "payment_id": "pay-..."}
#   SauceCard #DECLINED          402 {"status": "declined", "reason": "The card was declined"}
#   SauceCard #ERROR             500 (the payment service is broken)
#   SauceCard #SLOW              waits SLOW_SECONDS before answering (the shop gives up first)
#
# For the tests it also records every charge it receives:
#   GET /__requests?reference=order-abc   the recorded charges (all of them, or those of one reference)
#
# Run it alone:  python mocks/payment_mock.py   (the shop starts it by itself when it is not running)

import logging
import os
import socket
import threading
import time
import uuid
from urllib.parse import urlparse

from flask import Flask, jsonify, request

DEFAULT_PORT = 5056
DECLINE_CARD = 'SauceCard #DECLINED'
ERROR_CARD = 'SauceCard #ERROR'
SLOW_CARD = 'SauceCard #SLOW'
SLOW_SECONDS = 6  # longer than the shop waits for a payment

app = Flask(__name__)
_received = []  # every charge request, in order


@app.post('/payments')
def charge():
    body = request.get_json(silent=True) or {}
    _received.append(body)
    card = body.get('card')
    if not isinstance(card, str) or card == '' or not isinstance(body.get('amount_cents'), int):
        return jsonify({'status': 'rejected', 'reason': 'card and amount_cents are required'}), 400
    if card == ERROR_CARD:
        return jsonify({'status': 'error', 'reason': 'the payment service is broken'}), 500
    if card == SLOW_CARD:
        time.sleep(SLOW_SECONDS)
    if card == DECLINE_CARD:
        return jsonify({'status': 'declined', 'reason': 'The card was declined'}), 402
    return jsonify({'status': 'approved', 'payment_id': f'pay-{uuid.uuid4().hex[:12]}'}), 201


@app.get('/__requests')
def requests_seen():
    """Test hook: the charges received so far, newest last. ?reference=... keeps only that order's."""
    reference = request.args.get('reference')
    charges = [body for body in _received if reference is None or body.get('reference') == reference]
    return jsonify({'requests': charges})


def start_if_needed(url=None):
    """Start the mock in a background thread unless something already listens on its port (or the URL
    is not local: then a real service is meant to be there). Returns a function that stops it."""
    parsed = urlparse(url or os.environ.get('PAYMENT_URL') or f'http://127.0.0.1:{DEFAULT_PORT}/')
    host, port = parsed.hostname, parsed.port or 80
    if host not in ('127.0.0.1', 'localhost'):
        return lambda: None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex((host, port)) == 0:
            return lambda: None
    from werkzeug.serving import make_server
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    server = make_server(host, port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop():
        server.shutdown()
        thread.join(timeout=5)

    return stop


def main():
    app.run(host='127.0.0.1', port=int(os.environ.get('PAYMENT_PORT', DEFAULT_PORT)))


if __name__ == '__main__':
    main()
