# Orders through the API (POST /api/v1/orders, GET /api/v1/orders/<id>) and the payment service
#
# An order charges the whole cart to the card. The payment service is mocked (mocks/payment_mock.py):
# the card decides if it approves, declines or breaks, so every outcome can be tested. The checkout
# page always pays with an ordinary card, so decline and error can only be reached through the API.
import pytest

from mocks.payment_mock import DECLINE_CARD, ERROR_CARD, SLOW_CARD
from tests_api.checks import ORDER, ORDER_ITEM, check_contract, check_error, json_of
from Utilities.testData import TestData

pytestmark = pytest.mark.usefixtures('payment_mock')  # every test here needs it: check it is reachable first

GOOD_CARD = 'SauceCard #31337'  # the card the checkout page uses; any normal card approves
TAX_RATE = 0.08
PRODUCTS = ['Sauce Labs Backpack', 'Sauce Labs Bike Light']
CUSTOMER = {'first_name': 'FirstName', 'last_name': 'LastName', 'postal_code': '12345'}


def fill_cart(client, ids, products=tuple(PRODUCTS)):
    for name in products:
        client.add_to_cart(name, ids)


def place_order(client, card=GOOD_CARD, **overrides):
    return client.post('orders', json={**CUSTOMER, 'card': card, **overrides})


def expected_totals(products):
    prices = TestData.products()
    subtotal = round(sum(prices[name] for name in products), 2)
    tax = round(subtotal * TAX_RATE, 2)
    return subtotal, tax, round(subtotal + tax, 2)


class TestCreateOrder:
    def test_order_is_created_and_the_cart_is_emptied(self, user_api, ids):
        """A paid order answers 201 with status, items and totals, and the cart is empty afterwards"""
        fill_cart(user_api, ids)
        body = json_of(place_order(user_api), 201)
        check_contract(body, ORDER, 'the order')
        for item in body['items']:
            check_contract(item, ORDER_ITEM, f"order item {item.get('name')!r}")
        subtotal, tax, total = expected_totals(PRODUCTS)
        assert [item['name'] for item in body['items']] == PRODUCTS
        assert (body['subtotal'], body['tax'], body['total']) == (subtotal, tax, total)
        assert body['status'] == 'paid'
        assert user_api.cart_names() == [], 'The cart should be empty after the order'

    def test_the_order_can_be_read_back(self, user_api, ids):
        """GET /orders/<id> answers the same order that POST created"""
        fill_cart(user_api, ids)
        created = json_of(place_order(user_api), 201)
        assert json_of(user_api.get(f"orders/{created['id']}"), 200) == created

    def test_the_payment_service_is_charged_the_exact_total(self, user_api, ids, payment_mock):
        """The mock received exactly one charge for this order: right card, right amount in cents"""
        fill_cart(user_api, ids)
        body = json_of(place_order(user_api), 201)
        charges = payment_mock.charges_for(body['reference'])
        assert len(charges) == 1, f'Expected exactly one charge, the mock saw {charges}'
        assert charges[0]['card'] == GOOD_CARD
        assert charges[0]['amount_cents'] == round(body['total'] * 100)
        assert charges[0]['currency'] == 'USD'

    def test_two_orders_in_a_row(self, user_api, ids):
        """A second order works and gets its own id and reference (like OOS-23 on the page)"""
        fill_cart(user_api, ids)
        first = json_of(place_order(user_api), 201)
        fill_cart(user_api, ids, ['Sauce Labs Onesie'])
        second = json_of(place_order(user_api), 201)
        assert first['id'] != second['id'] and first['reference'] != second['reference']
        assert [item['name'] for item in second['items']] == ['Sauce Labs Onesie']


def saved_orders(shop_db):
    """How many orders are in the database right now (other tests of this run add their own)."""
    return shop_db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]


class TestPaymentGoesWrong:
    """The three unhappy answers of the payment service. In every one of them: no new order, cart kept."""

    @pytest.mark.parametrize('card, status, code', [
        pytest.param(DECLINE_CARD, 402, 'payment_declined', id='declined-card'),
        pytest.param(ERROR_CARD, 502, 'payment_unavailable', id='broken-payment-service'),
        pytest.param(SLOW_CARD, 502, 'payment_unavailable', id='payment-service-too-slow'),
    ])
    def test_a_failed_payment_changes_nothing(self, user_api, ids, shop_db, card, status, code):
        """The shop answers with the right error, keeps the cart and saves no order"""
        fill_cart(user_api, ids)
        orders_before = saved_orders(shop_db)
        check_error(place_order(user_api, card=card), status, code)
        assert user_api.cart_names() == PRODUCTS, 'The cart changed although the payment did not work'
        assert saved_orders(shop_db) == orders_before, 'An unpaid order was saved'

    def test_the_declined_message_says_why(self, user_api, ids):
        """The decline error carries the reason the payment service gave"""
        fill_cart(user_api, ids)
        check_error(place_order(user_api, card=DECLINE_CARD), 402, 'payment_declined',
                    'The payment was declined: The card was declined')


class TestOrderValidation:
    def test_an_empty_cart_cannot_be_ordered(self, user_api, shop_db):
        """No items: 409 cart_empty and no order is saved"""
        before = saved_orders(shop_db)
        check_error(place_order(user_api), 409, 'cart_empty')
        assert saved_orders(shop_db) == before

    @pytest.mark.parametrize('missing, code, message', [
        pytest.param('first_name', 'first_name_required', 'Error: First Name is required', id='first-name'),
        pytest.param('last_name', 'last_name_required', 'Error: Last Name is required', id='last-name'),
        pytest.param('postal_code', 'postal_code_required', 'Error: Postal Code is required', id='postal-code'),
        pytest.param('card', 'card_required', 'Error: Card is required', id='card'),
    ])
    def test_every_field_is_required(self, user_api, ids, missing, code, message):
        """Each missing field answers 400 with the same message the checkout page shows"""
        fill_cart(user_api, ids)
        check_error(place_order(user_api, **{missing: ''}), 400, code, message)
        assert user_api.cart_names() == PRODUCTS

    def test_body_must_be_json(self, user_api):
        """A body that is not JSON: 400 invalid_json"""
        check_error(user_api.post('orders', data='card=x'), 400, 'invalid_json')

    @pytest.mark.parametrize('method, path', [
        pytest.param('POST', 'orders', id='create'),
        pytest.param('GET', 'orders/1', id='read'),
    ])
    def test_orders_need_a_token(self, api, method, path):
        check_error(api.request(method, path), 401, 'missing_token')


class TestWhoSeesAnOrder:
    """Security: an order can be read by its user only, from any of that user's logins."""

    def test_an_order_of_another_user_is_not_found(self, api, user_api, token_for, ids):
        """problem_user asks for standard_user's order: 404, exactly as if it did not exist"""
        fill_cart(user_api, ids)
        order = json_of(place_order(user_api), 201)
        other = api.with_token(token_for('problem_user'))
        check_error(other.get(f"orders/{order['id']}"), 404, 'order_not_found')

    def test_the_same_user_sees_it_from_a_new_login(self, api, user_api, token_for, ids):
        """Unlike the cart, the order belongs to the user: a later login of the same user can read it"""
        fill_cart(user_api, ids)
        order = json_of(place_order(user_api), 201)
        later_login = api.with_token(token_for('standard_user'))
        assert json_of(later_login.get(f"orders/{order['id']}"), 200) == order

    def test_an_order_that_does_not_exist(self, user_api):
        check_error(user_api.get('orders/999999'), 404, 'order_not_found')
