# Client of the shop API for the tests: a thin layer over requests.
#
# It does three things and nothing more:
#   1. builds the URL (base URL + "api/v1/" + path) and adds "Authorization: Bearer <token>" if it has one
#   2. prints one readable step per call, like the page objects: "Step: GET /api/v1/products?sort=az"
#   3. always uses a timeout, so a hanging server fails the test instead of blocking the run
#
# It returns the requests.Response as it is: the tests check the status code and the body themselves,
# so what is being tested stays visible in the test.

import requests

from Utilities.readProperties import ReadConfig
from Utilities.steps import step, step_scope

API_PREFIX = 'api/v1/'


class ApiClient:
    def __init__(self, base_url, token=None):
        """base_url: the app, e.g. http://127.0.0.1:5055/ (the API is under api/v1/)."""
        self.base_url = base_url
        self.token = token
        self.timeout = ReadConfig.getExplicitWait()
        self.session = requests.Session()

    def with_token(self, token):
        """A new client that sends this token (None: no token)."""
        return ApiClient(self.base_url, token)

    def url(self, path):
        return self.base_url + API_PREFIX + path.lstrip('/')

    def request(self, method, path, json=None, params=None, headers=None, data=None):
        """Send a request and return the response, whatever its status code."""
        headers = dict(headers or {})
        if self.token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.token}'
        prepared = self.session.prepare_request(
            requests.Request(method, self.url(path), json=json, params=params, headers=headers, data=data))
        label = prepared.path_url + (' (with token)' if 'Authorization' in prepared.headers else '')
        with step_scope(f'{method} {label}'):
            return self.session.send(prepared, timeout=self.timeout)

    def get(self, path, **kwargs):
        return self.request('GET', path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('POST', path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request('DELETE', path, **kwargs)

    # ---- shortcuts for the calls most tests need ----
    @step('log in to the API as {username} with password {password}')
    def login(self, username, password):
        """POST auth/login. Returns the response (check it yourself, e.g. for the error cases)."""
        return self.post('auth/login', json={'username': username, 'password': password})

    @step('read the product ids from the API')
    def product_ids(self):
        """{product name: id}. Needs a token."""
        response = self.get('products')
        assert response.status_code == 200, f'Could not read the products: {describe(response)}'
        return {p['name']: p['id'] for p in response.json()['products']}

    @step('add {name} to the cart')
    def add_to_cart(self, name, ids):
        """POST cart/items with the id of name (ids from product_ids). Fails the test if it does not work."""
        response = self.post('cart/items', json={'product_id': ids[name]})
        assert response.status_code == 201, f'Could not add {name}: {describe(response)}'
        return response

    @step('read the names in the cart')
    def cart_names(self):
        response = self.get('cart/items')
        assert response.status_code == 200, f'Could not read the cart: {describe(response)}'
        return [p['name'] for p in response.json()['items']]

    @step('get an API token for {username}')
    def token_for(self, username, password):
        """Log in and return the token. Fails the test if the login does not work."""
        response = self.login(username, password)
        assert response.status_code == 200, f'Login as {username} failed: {describe(response)}'
        return response.json()['token']


def describe(response):
    """One line for failure messages: 'POST /api/v1/auth/login -> 401 {"error": ...}'."""
    body = response.text if len(response.text) <= 500 else response.text[:500] + '...'
    return f'{response.request.method} {response.request.path_url} -> {response.status_code} {body}'
