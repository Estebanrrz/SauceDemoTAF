# HTTP client the web pages use to talk to the shop API (/api/v1/).
#
# The pages do not read the database: they call the API over HTTP, like any other client (a phone
# app, Postman, the API tests). So a bug in the API shows up in the pages too.
#
# The login page stores the API token in the session cookie of the browser; every later call sends it
# as "Authorization: Bearer <token>". By default the API is the same app (request.host_url + api/v1/);
# SHOP_API_URL points the pages to another one.
#
# Errors:
#   NotLoggedIn     the API answered 401 to a call with a token (logged out elsewhere, new database...):
#                   the page clears the session and goes back to the login page
#   ApiUnavailable  the API did not answer, or answered something the page cannot use: error page

import os

import requests
from flask import g, request, session

TIMEOUT_SECONDS = 10


class NotLoggedIn(Exception):
    pass


class ApiUnavailable(Exception):
    pass


def _url(path):
    base = os.environ.get('SHOP_API_URL') or request.host_url + 'api/v1/'
    return base.rstrip('/') + '/' + path


def _call(method, path, expected, json=None, params=None, with_token=True):
    """Send the call and return the response. Any status outside expected is turned into an exception."""
    headers = {}
    token = session.get('api_token') if with_token else None
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        response = requests.request(method, _url(path), json=json, params=params, headers=headers,
                                    timeout=TIMEOUT_SECONDS)
    except requests.RequestException as error:
        raise ApiUnavailable(f'{method} {path}: {error}') from error
    if response.status_code == 401 and token:
        raise NotLoggedIn()
    if response.status_code not in expected:
        raise ApiUnavailable(f'{method} {path}: unexpected answer {response.status_code} {response.text[:200]}')
    return response


def error_message(response):
    return response.json()['error']['message']


# ---- auth ----
def login(username, password):
    """(token, None) when the login works, (None, message for the page) when it does not."""
    response = _call('POST', 'auth/login', expected=(200, 400, 401, 403),
                     json={'username': username, 'password': password}, with_token=False)
    if response.status_code == 200:
        return response.json()['token'], None
    return None, error_message(response)


def logout():
    """End the token of this browser. Errors are ignored: the page logs out anyway."""
    if session.get('api_token'):
        try:
            _call('POST', 'auth/logout', expected=(204,))
        except (NotLoggedIn, ApiUnavailable):
            pass


# ---- products ----
def products(sort='az'):
    """The catalog in the order of sort (az, za, lohi, hilo): list of {id, slug, name, description, price}."""
    return _call('GET', 'products', expected=(200,), params={'sort': sort}).json()['products']


# ---- cart (one per login: the token in this browser's session) ----
# The cart is read at most once per page view (kept in flask.g); add, remove and empty answer with the
# new cart, which replaces the kept one.
def cart():
    """Products in the cart, in the order they were added."""
    if 'cart' not in g:
        g.cart = _call('GET', 'cart/items', expected=(200,)).json()['items']
    return g.cart


def _keep(response):
    if response.status_code in (200, 201):
        g.cart = response.json()['items']
    else:
        g.pop('cart', None)  # 404/409: read it again when needed


def add_to_cart(product_id):
    """409 (already in the cart, e.g. a double click) and 404 (unknown product) change nothing."""
    _keep(_call('POST', 'cart/items', expected=(201, 404, 409), json={'product_id': product_id}))


def remove_from_cart(product_id):
    """404 (not in the cart, e.g. a double click) changes nothing."""
    _keep(_call('DELETE', f'cart/items/{product_id}', expected=(200, 404)))


# ---- orders ----
def place_order(card, customer):
    """Pay the whole cart with the card. Returns the order, or None when the cart was already empty
    (e.g. Finish clicked twice: the first click placed the order). customer holds the names of the
    checkout form (firstName, lastName, postalCode)."""
    response = _call('POST', 'orders', expected=(201, 409), json={
        'first_name': customer.get('firstName', ''),
        'last_name': customer.get('lastName', ''),
        'postal_code': customer.get('postalCode', ''),
        'card': card,
    })
    g.pop('cart', None)  # the order emptied the cart
    return response.json() if response.status_code == 201 else None
