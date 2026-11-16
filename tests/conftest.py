# Fixtures: local app, engine and page objects.
#
# The suite does not need anything running before it: if nothing is listening on the configured
# port it starts the local app (app/server.py) in a thread, and then drives it with the engine
# chosen with --engine.

import logging
import socket
import threading
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from Core.factory import create_engine
from PageObjects.CheckOutStepOnePage import CheckOutStepOnePage
from PageObjects.CheckoutCompletePage import CheckoutCompletePage
from PageObjects.InventoryPage import InventoryPage
from PageObjects.LoginPage import LoginPage
from PageObjects.MenuComponent import MenuComponent
from PageObjects.OverviewPage import OverviewPage
from PageObjects.ShoppingCartPage import ShoppingCartPage
from Utilities.readProperties import ReadConfig
from Utilities.testData import TestData

# One log line per request from the local app would bury the steps
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def port_is_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope='session')
def base_url():
    """URL of the app under test. Starts the local app if it is not already running."""
    url = ReadConfig.getApplicationUrl()
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or 80
    if port_is_open(host, port):
        yield url
        return
    from werkzeug.serving import make_server

    from app.server import app
    server = make_server(host, port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield url
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture(scope='session')
def engine_name(request):
    return request.config.getoption('--engine') or ReadConfig.getDefaultEngine()


@pytest.fixture
def engine(engine_name, base_url):
    """A new browser session for every test."""
    browser = create_engine(engine_name, headless=ReadConfig.isHeadless())
    yield browser
    browser.quit()


@pytest.fixture
def pages(engine):
    """Every page object, all sharing the same engine."""
    return SimpleNamespace(
        login=LoginPage(engine),
        inventory=InventoryPage(engine),
        cart=ShoppingCartPage(engine),
        checkout_one=CheckOutStepOnePage(engine),
        overview=OverviewPage(engine),
        complete=CheckoutCompletePage(engine),
        menu=MenuComponent(engine),
    )


@pytest.fixture
def open_login(engine, base_url):
    engine.goto(base_url)
    return base_url


@pytest.fixture
def login_as(open_login, pages):
    """Returns a function that logs in with a user from Data/users.json (the password is looked up there)."""

    def login(username='standard_user'):
        pages.login.Login(username, TestData.password(username))
        return pages

    return login


@pytest.fixture
def logged_in(login_as):
    """Starts the test already logged in as standard_user."""
    return login_as('standard_user')


@pytest.fixture
def go_to_page(logged_in, pages):
    """Returns a function that walks the real UI to a page with one product in the cart (no URL shortcuts)."""
    product = TestData.productNames()[0]

    def go(page_name):
        pages.inventory.AddtoCartItem(product)
        if page_name == 'inventory':
            return product
        pages.inventory.ClickShoppingCartButton()
        if page_name == 'cart':
            return product
        pages.cart.ClickButtonCheckout()
        if page_name == 'checkout step one':
            return product
        customer = TestData.customer()
        pages.checkout_one.FillInformation(customer['firstName'], customer['lastName'], customer['postalCode'])
        pages.checkout_one.ClickOnContinueButton()
        if page_name == 'checkout overview':
            return product
        pages.overview.ClickFinishButton()
        assert page_name == 'checkout complete', f'Unknown page: {page_name}'
        return product

    return go
