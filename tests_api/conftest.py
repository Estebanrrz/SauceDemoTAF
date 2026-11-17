# Fixtures of the API tests. They talk to the local app over HTTP with requests: no browser.
#
# base_url (root conftest.py) starts the local app when nothing is running, as for the UI tests.
#
#   api              client without a token (login, health, "what happens without a token?")
#   token_for        function: username -> a new token for that user (password from Data/users.json)
#   user_api         client already logged in as standard_user (a new token for every test)
#   ids              {product name: id}, read from the API
#   shop_db          read-only connection to the app's SQLite database, to check what the API saved
#   payment_mock     what charges did the payment mock receive

import os
import sqlite3

import pytest

from tests_api.clients.api_client import ApiClient
from tests_api.clients.payment_mock_client import PaymentMockClient
from Utilities.testData import TestData

API_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.hookimpl(tryfirst=True)  # before the root conftest.py reads the markers
def pytest_collection_modifyitems(items):
    """Every test in tests_api/ gets the marker api, so "pytest -m api" and "-m 'not api'" work."""
    for item in items:
        if os.path.abspath(str(item.path)).startswith(API_TESTS_DIR + os.sep):
            item.add_marker(pytest.mark.api)


@pytest.fixture
def api(base_url):
    return ApiClient(base_url)


@pytest.fixture
def token_for(api):
    def get(username='standard_user'):
        return api.token_for(username, TestData.password(username))

    return get


@pytest.fixture
def user_api(api, token_for):
    return api.with_token(token_for('standard_user'))


@pytest.fixture
def ids(user_api):
    return user_api.product_ids()


@pytest.fixture
def shop_db(base_url):
    """Read-only connection to the database of the app. Tests only read it: the API is the only writer.
    Skipped when the app was started outside the test run (its file is unknown): set SHOP_DB to the
    same file for both to use it then."""
    path = os.environ.get('SHOP_DB_FILE') or os.environ.get('SHOP_DB')
    if not path or not os.path.exists(path):
        pytest.skip('The database file of the app is unknown (app started outside the tests, SHOP_DB not set)')
    connection = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


@pytest.fixture
def payment_mock(base_url):  # base_url also starts the payment mock with the app
    """The payment mock, checked to be reachable (a mock started by another process may have stopped)."""
    client = PaymentMockClient()
    client.check_reachable()
    return client
