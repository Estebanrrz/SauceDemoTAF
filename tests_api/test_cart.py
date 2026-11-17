# Cart through the API (/api/v1/cart/items): add, remove, empty, errors, and who can see a cart
#
# One cart per login (per token), quantity always 1, products in the order they were added: the same
# rules as the cart of the web pages.
import pytest

from tests_api.checks import CART, PRODUCT, check_contract, check_error, json_of

BACKPACK, BIKE_LIGHT, ONESIE = 'Sauce Labs Backpack', 'Sauce Labs Bike Light', 'Sauce Labs Onesie'


def names_in(response, status):
    body = json_of(response, status)
    check_contract(body, CART, 'the cart')
    for item in body['items']:
        check_contract(item, PRODUCT, f"cart item {item.get('name')!r}")
    return [item['name'] for item in body['items']]


class TestCart:
    def test_a_new_login_starts_with_an_empty_cart(self, user_api):
        """GET /cart/items right after logging in: 200 and no items"""
        assert names_in(user_api.get('cart/items'), 200) == []

    def test_add_a_product(self, user_api, ids):
        """POST /cart/items answers 201 with the cart, and the product is in the cart afterwards"""
        assert names_in(user_api.post('cart/items', json={'product_id': ids[BACKPACK]}), 201) == [BACKPACK]
        assert names_in(user_api.get('cart/items'), 200) == [BACKPACK]

    def test_cart_keeps_the_order_products_were_added(self, user_api, ids):
        """The cart lists the products in the order they were added, not by name or id (like OOS-16 on the page)"""
        added = [ONESIE, BACKPACK, BIKE_LIGHT]
        for name in added:
            user_api.add_to_cart(name, ids)
        assert user_api.cart_names() == added

    def test_remove_a_product(self, user_api, ids):
        """DELETE /cart/items/<id> removes only that product and answers with the rest of the cart"""
        user_api.add_to_cart(BACKPACK, ids)
        user_api.add_to_cart(BIKE_LIGHT, ids)
        assert names_in(user_api.delete(f'cart/items/{ids[BACKPACK]}'), 200) == [BIKE_LIGHT]

    def test_add_every_product_then_empty_the_cart(self, user_api, ids):
        """All 6 products fit in the cart, and DELETE /cart/items empties it (like OOS-14 on the page)"""
        for name in ids:
            user_api.add_to_cart(name, ids)
        assert sorted(user_api.cart_names()) == sorted(ids)
        assert names_in(user_api.delete('cart/items'), 200) == []
        assert user_api.cart_names() == []

    def test_a_removed_product_can_be_added_again(self, user_api, ids):
        """Add, remove and add again: the product is back, once"""
        user_api.add_to_cart(BACKPACK, ids)
        user_api.delete(f'cart/items/{ids[BACKPACK]}')
        user_api.add_to_cart(BACKPACK, ids)
        assert user_api.cart_names() == [BACKPACK]


class TestCartErrors:
    def test_same_product_twice_is_rejected(self, user_api, ids):
        """Quantity is always 1: adding a product that is already in the cart answers 409 and changes nothing"""
        user_api.add_to_cart(BACKPACK, ids)
        check_error(user_api.post('cart/items', json={'product_id': ids[BACKPACK]}), 409, 'already_in_cart')
        assert user_api.cart_names() == [BACKPACK]

    def test_unknown_product_is_rejected(self, user_api):
        """A product id that does not exist: 404 product_not_found, the cart stays empty"""
        check_error(user_api.post('cart/items', json={'product_id': 9999}), 404, 'product_not_found')
        assert user_api.cart_names() == []

    @pytest.mark.parametrize('body', [
        pytest.param({}, id='no-product-id'),
        pytest.param({'product_id': None}, id='null'),
        pytest.param({'product_id': '1'}, id='text'),
        pytest.param({'product_id': 1.5}, id='decimal'),
        pytest.param({'product_id': True}, id='true'),
        pytest.param({'product_id': [1]}, id='list'),
    ])
    def test_product_id_must_be_a_whole_number(self, user_api, body):
        """product_id missing or not a whole number: 400 invalid_field"""
        check_error(user_api.post('cart/items', json=body), 400, 'invalid_field', 'product_id must be a whole number')

    def test_body_must_be_json(self, user_api):
        """A body that is not JSON: 400 invalid_json"""
        check_error(user_api.post('cart/items', data='product_id=1'), 400, 'invalid_json')

    def test_removing_a_product_that_is_not_in_the_cart(self, user_api, ids):
        """DELETE /cart/items/<id> for a product that is not in the cart: 404 not_in_cart"""
        check_error(user_api.delete(f'cart/items/{ids[BACKPACK]}'), 404, 'not_in_cart')

    @pytest.mark.parametrize('method, path, body', [
        pytest.param('GET', 'cart/items', None, id='read'),
        pytest.param('POST', 'cart/items', {'product_id': 1}, id='add'),
        pytest.param('DELETE', 'cart/items/1', None, id='remove'),
        pytest.param('DELETE', 'cart/items', None, id='empty'),
    ])
    def test_cart_needs_a_token(self, api, method, path, body):
        """Every cart call without a token: 401 missing_token"""
        check_error(api.request(method, path, json=body), 401, 'missing_token')


class TestCartOfAnotherUser:
    """Security: a token only ever reaches the cart of its own login."""

    @pytest.fixture
    def alice(self, api, token_for):
        return api.with_token(token_for('standard_user'))

    @pytest.fixture
    def bob(self, api, token_for):
        return api.with_token(token_for('problem_user'))

    def test_another_user_does_not_see_my_cart(self, alice, bob, ids):
        """standard_user adds products; problem_user's cart is still empty"""
        alice.add_to_cart(BACKPACK, ids)
        alice.add_to_cart(BIKE_LIGHT, ids)
        assert bob.cart_names() == []
        assert alice.cart_names() == [BACKPACK, BIKE_LIGHT]

    def test_another_user_cannot_remove_from_my_cart(self, alice, bob, ids):
        """problem_user tries to remove a product of standard_user's cart: 404 not_in_cart, and it is still there"""
        alice.add_to_cart(BACKPACK, ids)
        check_error(bob.delete(f'cart/items/{ids[BACKPACK]}'), 404, 'not_in_cart')
        assert alice.cart_names() == [BACKPACK]

    def test_another_user_emptying_their_cart_leaves_mine(self, alice, bob, ids):
        """problem_user empties their cart; standard_user's cart does not change"""
        alice.add_to_cart(BACKPACK, ids)
        bob.add_to_cart(ONESIE, ids)
        assert names_in(bob.delete('cart/items'), 200) == []
        assert alice.cart_names() == [BACKPACK]

    def test_two_logins_of_the_same_user_have_two_carts(self, api, token_for, ids):
        """Like two browsers: the same user logged in twice has two separate carts"""
        first, second = api.with_token(token_for()), api.with_token(token_for())
        first.add_to_cart(BACKPACK, ids)
        assert second.cart_names() == []

    def test_logout_deletes_the_cart(self, api, token_for, ids):
        """After logout the old token cannot read the cart, and the next login starts with an empty cart"""
        user = api.with_token(token_for())
        user.add_to_cart(BACKPACK, ids)
        assert user.post('auth/logout').status_code == 204
        check_error(user.get('cart/items'), 401, 'invalid_token')
        assert api.with_token(token_for()).cart_names() == []
