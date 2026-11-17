# Token expiry: a token works for TOKEN_TTL_SECONDS after the login (default 300 = 5 minutes), then the
# API answers 401 token_expired with a clear message
#
# Waiting 5 minutes in a test is not an option, and shortening the lifetime for the whole run would break
# the other tests. So the expiry tests start their own copy of the app with TOKEN_TTL_SECONDS=2
# (tests_api/separate_app.py), exactly as a person would configure it.
import hashlib
import os
import time
from datetime import datetime

import pytest

from mocks.payment_mock import DECLINE_CARD
from tests_api.checks import LOGIN, check_contract, check_error, json_of
from tests_api.clients.api_client import ApiClient
from tests_api.separate_app import run_app, separate_app
from Utilities.testData import TestData

SHORT_TTL = 2  # seconds, for the separate app
EXPIRED_MESSAGE = 'The token has expired, please log in again'
EXPIRED_HEADER = 'Bearer error="invalid_token", error_description="The token has expired"'


def configured_ttl():
    """What the app of this run uses: TOKEN_TTL_SECONDS if set, otherwise 5 minutes."""
    return float(os.environ.get('TOKEN_TTL_SECONDS') or 300)


def parse(timestamp):
    return datetime.strptime(timestamp.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f%z' if '.' in timestamp
                             else '%Y-%m-%dT%H:%M:%S%z')


@pytest.fixture(scope='module')
def short_ttl_app(base_url):  # base_url: the payment mock is already running for the separate app too
    with separate_app({'TOKEN_TTL_SECONDS': str(SHORT_TTL)}) as url:
        yield url


@pytest.fixture(scope='module')
def expired_token(short_ttl_app):
    """A token of the separate app that has already expired (one wait for all the tests that use it)."""
    client = ApiClient(short_ttl_app)
    token = client.token_for('standard_user', TestData.password('standard_user'))
    time.sleep(SHORT_TTL + 0.5)
    return token


class TestTokenLifetime:
    def test_login_says_how_long_the_token_works(self, api):
        """The login answer has expires_in: the lifetime in seconds (5 minutes unless configured)"""
        body = json_of(api.login('standard_user', TestData.password('standard_user')), 200)
        check_contract(body, LOGIN)
        assert body['expires_in'] == configured_ttl()

    def test_the_database_keeps_the_expiry_time(self, shop_db, token_for):
        """api_tokens.expires_at is the login time plus the lifetime"""
        token = token_for('standard_user')
        row = shop_db.execute('SELECT created_at, expires_at FROM api_tokens WHERE token_hash = ?',
                              (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        lifetime = (parse(row['expires_at']) - parse(row['created_at'])).total_seconds()
        assert abs(lifetime - configured_ttl()) < 2, f'Expected about {configured_ttl()}s, got {lifetime}s: {dict(row)}'


class TestExpiredToken:
    def test_a_token_works_until_it_expires(self, short_ttl_app):
        """With TOKEN_TTL_SECONDS=2: the token works at once, and after 2 seconds gets 401 token_expired"""
        client = ApiClient(short_ttl_app)
        body = json_of(client.login('standard_user', TestData.password('standard_user')), 200)
        assert body['expires_in'] == SHORT_TTL
        user = client.with_token(body['token'])
        json_of(user.get('products'), 200)
        time.sleep(SHORT_TTL + 0.5)
        response = user.get('products')
        check_error(response, 401, 'token_expired', EXPIRED_MESSAGE)
        assert response.headers.get('WWW-Authenticate') == EXPIRED_HEADER

    @pytest.mark.parametrize('method, path, body', [
        pytest.param('GET', 'products', None, id='products'),
        pytest.param('GET', 'cart/items', None, id='read-cart'),
        pytest.param('POST', 'cart/items', {'product_id': 1}, id='add-to-cart'),
        pytest.param('POST', 'orders', {'first_name': 'A', 'last_name': 'B', 'postal_code': 'C',
                                        'card': DECLINE_CARD}, id='place-order'),
        pytest.param('POST', 'auth/logout', None, id='logout'),
    ])
    def test_every_protected_endpoint_rejects_an_expired_token(self, short_ttl_app, expired_token, method, path, body):
        """No endpoint accepts an expired token, and they all say the same clear thing"""
        response = ApiClient(short_ttl_app, expired_token).request(method, path, json=body)
        check_error(response, 401, 'token_expired', EXPIRED_MESSAGE)

    def test_expired_is_not_confused_with_invalid(self, short_ttl_app, expired_token):
        """A token that never existed still says invalid_token: the client can tell the two cases apart"""
        check_error(ApiClient(short_ttl_app, 'never-issued-' + 'x' * 30).get('products'), 401, 'invalid_token')

    def test_logging_in_again_gives_a_working_token(self, short_ttl_app, expired_token):
        """After expiry the user logs in again and the new token works"""
        client = ApiClient(short_ttl_app)
        fresh = client.with_token(client.token_for('standard_user', TestData.password('standard_user')))
        json_of(fresh.get('products'), 200)


class TestLifetimeSetting:
    @pytest.mark.parametrize('value', ['abc', '0', '-5'])
    def test_a_wrong_value_stops_the_app_with_a_clear_message(self, value):
        """TOKEN_TTL_SECONDS that is not a positive number: the app does not start and says why"""
        exit_code, printed = run_app({'TOKEN_TTL_SECONDS': value})
        assert exit_code != 0, 'The app started with a wrong TOKEN_TTL_SECONDS'
        assert 'TOKEN_TTL_SECONDS must be a number of seconds greater than 0' in printed, printed
