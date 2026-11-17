# JSON API of the local shop, under /api/v1/.
#
#   GET  /api/v1/health                 is the app up and the database reachable? (no token needed)
#   POST /api/v1/auth/login             {"username": ..., "password": ...} -> {"token": ..., "expires_in": 300, ...}
#   POST /api/v1/auth/logout            the token stops working (204, no body)
#   GET  /api/v1/products?sort=az       the catalog (sort: az, za, lohi, hilo; default az)
#   GET  /api/v1/products/<id>          one product
#   GET    /api/v1/cart/items           the cart of this login: {"items": [product, ...]} in the order added
#   POST   /api/v1/cart/items           {"product_id": 1} adds a product (201); quantity is always 1
#   DELETE /api/v1/cart/items/<id>      removes that product
#   DELETE /api/v1/cart/items           empties the cart
#   POST   /api/v1/orders               pays the cart: {"first_name", "last_name", "postal_code", "card"}
#   GET    /api/v1/orders/<id>          one order of the logged-in user
#
# Everything except health and login needs the header "Authorization: Bearer <token>", like the web
# pages need a logged-in user.
#
# Tokens expire TOKEN_TTL_SECONDS after the login (environment variable, default 300 = 5 minutes).
# An expired token gets 401 token_expired ("log in again"); a token that never existed or was logged
# out gets 401 invalid_token.
#
# Every error has the same shape, so a test (or a person in Postman) always knows where to look:
#   {"error": {"code": "invalid_token", "message": "The token is not valid"}}
# The login errors use the same messages as the login page (app/messages.py).

import os
import secrets
import sqlite3
import uuid
from functools import wraps

from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import HTTPException

from app import messages, payments
from app.db import get_db, password_matches, token_hash, utc_timestamp

api = Blueprint('api', __name__, url_prefix='/api/v1')

TAX_RATE = 0.08
DEFAULT_TOKEN_TTL_SECONDS = 300  # 5 minutes


def token_ttl_seconds():
    """How long a token works after the login: TOKEN_TTL_SECONDS, default 300. Read at every login, so
    the app started with another value uses it. ValueError with a clear message for a wrong value."""
    value = os.environ.get('TOKEN_TTL_SECONDS', '').strip() or str(DEFAULT_TOKEN_TTL_SECONDS)
    try:
        seconds = float(value)
    except ValueError:
        seconds = 0
    if not seconds > 0:
        raise ValueError(f'TOKEN_TTL_SECONDS must be a number of seconds greater than 0, got {value!r}')
    return int(seconds) if seconds.is_integer() else seconds

# Same orders as the sort box of the products page. Equal prices are ordered by name.
SORTS = {
    'az': 'name ASC',
    'za': 'name DESC',
    'lohi': 'price_cents ASC, name ASC',
    'hilo': 'price_cents DESC, name ASC',
}


class ApiError(Exception):
    """Raise it anywhere in the API to answer with the standard error shape."""

    def __init__(self, status, code, message, authenticate=None):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.authenticate = authenticate  # WWW-Authenticate header of a 401, if not the plain one


def error_response(status, code, message, authenticate=None):
    response = jsonify({'error': {'code': code, 'message': message}})
    response.status_code = status
    if status == 401:
        # Tells the client which kind of credentials it needs (and, for a bad token, what went wrong)
        response.headers['WWW-Authenticate'] = authenticate or 'Bearer'
    return response


@api.errorhandler(ApiError)
def handle_api_error(error):
    return error_response(error.status, error.code, error.message, error.authenticate)


@api.app_errorhandler(HTTPException)
def handle_http_error(error):
    """Unknown URL, wrong method...: JSON under /api/, the normal HTML page everywhere else."""
    if not request.path.startswith(api.url_prefix + '/') or error.code is None or error.code < 400:
        return error  # web pages and redirects stay as they are
    code = (error.name or 'error').lower().replace(' ', '_')  # "Not Found" -> not_found
    return error_response(error.code, code, error.description)


def json_body():
    """The request body as a JSON object (dict), or a 400 error."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, 'invalid_json', 'The request body must be a JSON object')
    return body


def text_field(body, name):
    """A string field of the body; missing counts as empty. Any other type is a 400 error."""
    value = body.get(name, '')
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise ApiError(400, 'invalid_field', f'{name} must be a string')
    return value


def whole_number_field(body, name):
    """A whole-number field of the body (true/false, "1" or 1.5 are not accepted), or a 400 error."""
    value = body.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(400, 'invalid_field', f'{name} must be a whole number')
    return value


def token_required(view):
    """The request needs "Authorization: Bearer <token>" with a token from /auth/login. Sets g.username."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        scheme, _, token = request.headers.get('Authorization', '').partition(' ')
        token = token.strip()
        if scheme.lower() != 'bearer' or not token:
            raise ApiError(401, 'missing_token', 'The Authorization header must be "Bearer <token>"')
        row = get_db().execute('SELECT username, expires_at FROM api_tokens WHERE token_hash = ?',
                               (token_hash(token),)).fetchone()
        if row is None:
            raise ApiError(401, 'invalid_token', 'The token is not valid')
        if row['expires_at'] is None or row['expires_at'] <= utc_timestamp():
            raise ApiError(401, 'token_expired', 'The token has expired, please log in again',
                           authenticate='Bearer error="invalid_token", error_description="The token has expired"')
        g.username = row['username']
        g.token_hash = token_hash(token)
        return view(*args, **kwargs)

    return wrapper


def product_json(row):
    return {
        'id': row['id'],
        'slug': row['slug'],
        'name': row['name'],
        'description': row['description'],
        'price': row['price_cents'] / 100,  # 2999 -> 29.99
    }


# ---- health ----
@api.get('/health')
def health():
    try:
        get_db().execute('SELECT 1').fetchone()
    except sqlite3.Error:
        return jsonify({'status': 'error', 'database': 'error'}), 503
    return jsonify({'status': 'ok', 'database': 'ok'})


# ---- auth ----
@api.post('/auth/login')
def login():
    """Same checks, in the same order, as the login page: username, password, locked, match.
    An unknown user and a wrong password get the same answer, so nobody can find out which users exist."""
    body = json_body()
    username = text_field(body, 'username')
    password = text_field(body, 'password')
    if username == '':
        raise ApiError(400, 'username_required', messages.LOGIN_USERNAME_REQUIRED)
    if password == '':
        raise ApiError(400, 'password_required', messages.LOGIN_PASSWORD_REQUIRED)
    user = get_db().execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user is None or not password_matches(user, password):
        raise ApiError(401, 'invalid_credentials', messages.LOGIN_NO_MATCH)
    if user['locked']:
        raise ApiError(403, 'user_locked', messages.LOGIN_LOCKED)

    token = secrets.token_urlsafe(32)
    lifetime = token_ttl_seconds()
    database = get_db()
    database.execute('INSERT INTO api_tokens (token_hash, username, expires_at) VALUES (?, ?, ?)',
                     (token_hash(token), username, utc_timestamp(lifetime)))
    database.commit()
    return jsonify({'token': token, 'token_type': 'Bearer', 'username': username, 'expires_in': lifetime})


@api.post('/auth/logout')
@token_required
def logout():
    """Delete the token: any later call with it gets 401 invalid_token."""
    database = get_db()
    database.execute('DELETE FROM api_tokens WHERE token_hash = ?', (g.token_hash,))
    database.commit()
    return '', 204


# ---- products ----
@api.get('/products')
@token_required
def list_products():
    sort = request.args.get('sort', 'az')
    if sort not in SORTS:
        raise ApiError(400, 'invalid_sort', f"sort must be one of: {', '.join(SORTS)}")
    rows = get_db().execute(f'SELECT * FROM products ORDER BY {SORTS[sort]}').fetchall()  # only values from SORTS
    return jsonify({'products': [product_json(row) for row in rows]})


@api.get('/products/<int:product_id>')
@token_required
def get_product(product_id):
    row = get_db().execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if row is None:
        raise ApiError(404, 'product_not_found', f'There is no product with id {product_id}')
    return jsonify(product_json(row))


# ---- cart ----
# The cart belongs to the token (g.token_hash): another token, even of the same user, never sees it.
def cart_json():
    rows = get_db().execute(
        'SELECT products.* FROM cart_items JOIN products ON products.id = cart_items.product_id '
        'WHERE cart_items.token_hash = ? ORDER BY cart_items.id', (g.token_hash,)).fetchall()
    return {'items': [product_json(row) for row in rows]}


@api.get('/cart/items')
@token_required
def get_cart():
    return jsonify(cart_json())


@api.post('/cart/items')
@token_required
def add_to_cart():
    product_id = whole_number_field(json_body(), 'product_id')
    database = get_db()
    if database.execute('SELECT 1 FROM products WHERE id = ?', (product_id,)).fetchone() is None:
        raise ApiError(404, 'product_not_found', f'There is no product with id {product_id}')
    try:
        database.execute('INSERT INTO cart_items (token_hash, product_id) VALUES (?, ?)', (g.token_hash, product_id))
        database.commit()
    except sqlite3.IntegrityError:  # the UNIQUE rule: it is already in this cart
        raise ApiError(409, 'already_in_cart', f'Product {product_id} is already in the cart (quantity is always 1)')
    return jsonify(cart_json()), 201


@api.delete('/cart/items/<int:product_id>')
@token_required
def remove_from_cart(product_id):
    database = get_db()
    removed = database.execute('DELETE FROM cart_items WHERE token_hash = ? AND product_id = ?',
                               (g.token_hash, product_id)).rowcount
    database.commit()
    if not removed:
        raise ApiError(404, 'not_in_cart', f'Product {product_id} is not in the cart')
    return jsonify(cart_json())


@api.delete('/cart/items')
@token_required
def empty_cart():
    database = get_db()
    database.execute('DELETE FROM cart_items WHERE token_hash = ?', (g.token_hash,))
    database.commit()
    return jsonify(cart_json())


# ---- orders ----
# An order belongs to the user (unlike the cart, which belongs to the login): see the schema in app/db.py.
def order_json(order, items):
    return {
        'id': order['id'],
        'status': 'paid',
        'reference': order['reference'],
        'payment_id': order['payment_id'],
        'items': [{'id': i['product_id'], 'name': i['name'], 'price': i['price_cents'] / 100} for i in items],
        'subtotal': order['subtotal_cents'] / 100,
        'tax': order['tax_cents'] / 100,
        'total': order['total_cents'] / 100,
    }


@api.post('/orders')
@token_required
def create_order():
    """Charge the whole cart of this login to the card and save the order. The cart is emptied only
    when the payment worked; a declined card or a broken payment service leaves everything as it was."""
    body = json_body()
    fields = {name: text_field(body, name) for name in ('first_name', 'last_name', 'postal_code', 'card')}
    # Same order and texts as the checkout page checks its form
    for name, message in (('first_name', messages.CHECKOUT_FIRST_NAME_REQUIRED),
                          ('last_name', messages.CHECKOUT_LAST_NAME_REQUIRED),
                          ('postal_code', messages.CHECKOUT_POSTAL_CODE_REQUIRED),
                          ('card', messages.CHECKOUT_CARD_REQUIRED)):
        if fields[name] == '':
            raise ApiError(400, f'{name}_required', message)

    database = get_db()
    items = database.execute(
        'SELECT products.* FROM cart_items JOIN products ON products.id = cart_items.product_id '
        'WHERE cart_items.token_hash = ? ORDER BY cart_items.id', (g.token_hash,)).fetchall()
    if not items:
        raise ApiError(409, 'cart_empty', 'The cart is empty: there is nothing to order')
    subtotal = sum(item['price_cents'] for item in items)
    tax = round(subtotal * TAX_RATE)
    total = subtotal + tax

    reference = f'order-{uuid.uuid4().hex[:12]}'
    try:
        payment_id = payments.charge(fields['card'], total, reference)
    except payments.PaymentDeclined as declined:
        raise ApiError(402, 'payment_declined', f'The payment was declined: {declined}')
    except payments.PaymentUnavailable:
        raise ApiError(502, 'payment_unavailable', 'The payment service is not available, please try again later')

    cursor = database.execute(
        'INSERT INTO orders (username, reference, card, payment_id, first_name, last_name, postal_code, '
        'subtotal_cents, tax_cents, total_cents) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (g.username, reference, fields['card'], payment_id, fields['first_name'], fields['last_name'],
         fields['postal_code'], subtotal, tax, total))
    order_id = cursor.lastrowid
    database.executemany(
        'INSERT INTO order_items (order_id, product_id, name, price_cents) VALUES (?, ?, ?, ?)',
        [(order_id, item['id'], item['name'], item['price_cents']) for item in items])
    database.execute('DELETE FROM cart_items WHERE token_hash = ?', (g.token_hash,))
    database.commit()
    return jsonify(read_order(order_id)), 201


@api.get('/orders/<int:order_id>')
@token_required
def get_order(order_id):
    order = read_order(order_id)
    if order is None:
        # Also for an order of another user: not revealing that it exists
        raise ApiError(404, 'order_not_found', f'There is no order with id {order_id}')
    return jsonify(order)


def read_order(order_id):
    database = get_db()
    order = database.execute('SELECT * FROM orders WHERE id = ? AND username = ?',
                             (order_id, g.username)).fetchone()
    if order is None:
        return None
    items = database.execute('SELECT * FROM order_items WHERE order_id = ? ORDER BY id', (order_id,)).fetchall()
    return order_json(order, items)
