# Local copy of saucedemo.com so the suite can run without internet.
#
# It keeps what the tests rely on: same URLs, same ids / data-test attributes / CSS classes,
# same error messages, same validation order and the same 8% tax.
#
# Run it alone:  python app/server.py   ->  http://127.0.0.1:5055/  (JSON API under /api/v1/)
# The test suite starts it by itself when nothing is listening on that port (start_if_needed).

import logging
import os
import shutil
import socket
import sys
import tempfile
import threading
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, redirect, render_template, request, session, url_for

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if __package__ in (None, ''):  # run as "python app/server.py": make the app package importable
    sys.path.insert(0, ROOT_DIR)

from app import db, messages, shop_api  # noqa: E402 (needs the path above)
from mocks.payment_mock import start_if_needed as start_payment_mock_if_needed  # noqa: E402
from app.api import api, token_ttl_seconds  # noqa: E402

DEFAULT_PORT = 5055
DB_FILE_ENV = 'SHOP_DB_FILE'  # set by start_if_needed: the database file of the app it started

app = Flask(__name__)
app.secret_key = 'local-copy-not-a-secret'  # only signs the session cookie of this local app
app.json.sort_keys = False  # API answers keep the field order of the code, easier to read
app.register_blueprint(api)
app.teardown_appcontext(db.close_db)

TAX_RATE = 0.08  # shown on the overview page; the orders API applies the same rate when it charges
CARD = 'SauceCard #31337'  # the fixed card of the shop: the payment service approves it

# The pages keep no shop data: users, products and carts live in the database and the pages reach
# them only through the API (app/shop_api.py). The session cookie holds the user name and the API token.

SORTS = ('az', 'za', 'lohi', 'hilo')  # values of the sort box; the API does the sorting


def money(value):
    return f'{value:.2f}'


app.jinja_env.globals['money'] = money


def login_required(view):
    """The page needs a logged-in user, that is, an API token in the session."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'api_token' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapper


@app.errorhandler(shop_api.NotLoggedIn)
def token_no_longer_valid(error):
    """The API rejected the token of this browser: start again from the login page."""
    session.clear()
    return redirect(url_for('login'))


@app.errorhandler(shop_api.ApiUnavailable)
def api_unavailable(error):
    app.logger.error('Shop API problem: %s', error)
    return 'The shop service is not available right now. Please try again later.', 503


@app.context_processor
def inject_cart():
    """Number on the cart badge of every page (none on the login page)."""
    return {'cart_count': len(shop_api.cart()) if 'api_token' in session else 0}


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None, username='')

    username = request.form.get('user-name', '')
    password = request.form.get('password', '')
    # The API checks everything (same checks, order and messages as before) and gives the token
    token, error = shop_api.login(username, password)
    if error:
        return render_template('login.html', error=error, username=username)

    shop_api.logout()  # this browser was already logged in: end the old token
    session.clear()
    session['user'] = username
    session['api_token'] = token  # a new login has a new, empty cart
    return redirect(url_for('inventory'))


@app.route('/logout')
def logout():
    shop_api.logout()  # the token stops working in the API too, not only in this browser
    session.clear()
    return redirect(url_for('login'))


@app.route('/inventory.html')
@login_required
def inventory():
    sort = request.args.get('sort', 'az')
    if sort not in SORTS:  # the page ignores an unknown value (the API would answer 400)
        sort = 'az'
    in_cart = {p['id'] for p in shop_api.cart()}
    return render_template('inventory.html', products=shop_api.products(sort), in_cart=in_cart)


@app.route('/cart/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_cart(product_id):
    """The same button adds the product or, if it is already in the cart, removes it."""
    if any(p['id'] == product_id for p in shop_api.cart()):
        shop_api.remove_from_cart(product_id)
    else:
        shop_api.add_to_cart(product_id)
    return redirect(request.form.get('back') or url_for('inventory'))


@app.route('/cart.html')
@login_required
def cart_page():
    return render_template('cart.html', items=shop_api.cart())


@app.route('/checkout-step-one.html', methods=['GET', 'POST'])
@login_required
def checkout_step_one():
    first = last = postal = ''
    error = None
    if request.method == 'POST':
        first = request.form.get('firstName', '')
        last = request.form.get('lastName', '')
        postal = request.form.get('postalCode', '')
        # Fields are checked in order and only the first error is shown, like the real site
        if first == '':
            error = messages.CHECKOUT_FIRST_NAME_REQUIRED
        elif last == '':
            error = messages.CHECKOUT_LAST_NAME_REQUIRED
        elif postal == '':
            error = messages.CHECKOUT_POSTAL_CODE_REQUIRED
        else:
            session['customer'] = {'firstName': first, 'lastName': last, 'postalCode': postal}
            return redirect(url_for('checkout_step_two'))
    return render_template('checkout_step_one.html', error=error, first=first, last=last, postal=postal)


@app.route('/checkout-step-two.html')
@login_required
def checkout_step_two():
    items = shop_api.cart()
    subtotal = round(sum(p['price'] for p in items), 2)
    tax = round(subtotal * TAX_RATE, 2)
    return render_template('checkout_step_two.html', items=items, card=CARD,
                           subtotal=subtotal, tax=tax, total=round(subtotal + tax, 2))


@app.route('/checkout-complete.html', methods=['GET', 'POST'])
@login_required
def checkout_complete():
    if request.method == 'POST':  # Finish: the order is paid through the API and the cart empties with it
        customer = session.get('customer')
        if not customer:
            return redirect(url_for('checkout_step_one'))
        order = shop_api.place_order(CARD, customer)
        if order:  # None: the cart was already empty (e.g. Finish clicked twice), keep the first order
            session['last_order'] = order['id']
        return redirect(url_for('checkout_complete'))
    return render_template('checkout_complete.html', order_number=session.get('last_order'))


def start_if_needed(url):
    """Start the app in a background thread unless something already listens on the port of url.
    Returns a function that stops it (it does nothing if the app was already running).

    The app gets a new, empty database for this run only (deleted by stop), so every run starts from
    the same data. Set SHOP_DB to use a fixed file instead. The file in use is left in SHOP_DB_FILE,
    so the tests (and the device runs started from this process) can read it."""
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or 80
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex((host, port)) == 0:
            return lambda: None
    token_ttl_seconds()  # a wrong TOKEN_TTL_SECONDS stops here with a clear message, before anything starts
    stop_payment_mock = start_payment_mock_if_needed()  # the orders API needs the payment service
    temp_dir = None if os.environ.get('SHOP_DB') else tempfile.mkdtemp(prefix='shop-db-')
    db.init_db(app, os.path.join(temp_dir, 'shop.db') if temp_dir else db.default_path())
    os.environ[DB_FILE_ENV] = app.config['SHOP_DB']
    from werkzeug.serving import make_server
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # one line per request would bury the output
    server = make_server(host, port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop():
        server.shutdown()
        thread.join(timeout=5)
        stop_payment_mock()
        os.environ.pop(DB_FILE_ENV, None)
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return stop


def main():
    try:
        ttl = token_ttl_seconds()
    except ValueError as error:
        sys.exit(f'Configuration error: {error}')  # exit code 1, message on stderr
    start_payment_mock_if_needed()
    db.init_db(app, db.default_path())
    print(f"Database: {app.config['SHOP_DB']}")
    print(f'API tokens expire after {ttl} seconds (TOKEN_TTL_SECONDS)')
    app.run(host='127.0.0.1', port=int(os.environ.get('APP_PORT', DEFAULT_PORT)))


if __name__ == '__main__':
    main()
