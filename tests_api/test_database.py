# What the API leaves in the database (read-only checks with the shop_db fixture)
#
# Some rules cannot be seen from the API answers alone, e.g. that logout really deletes the cart rows,
# or that the token is not stored as plain text. These tests look inside the SQLite file.
import hashlib

from Utilities.testData import TestData


def cart_rows(shop_db, token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return shop_db.execute('SELECT COUNT(*) FROM cart_items WHERE token_hash = ?', (token_hash,)).fetchone()[0]


class TestDatabase:
    def test_products_table_matches_the_test_data(self, shop_db):
        """The products table holds Data/products.json, with prices in whole cents"""
        rows = shop_db.execute('SELECT name, price_cents FROM products').fetchall()
        expected = {name: round(price * 100) for name, price in TestData.products().items()}
        assert {row['name']: row['price_cents'] for row in rows} == expected

    def test_tokens_and_passwords_are_not_stored_as_plain_text(self, shop_db, token_for):
        """After a login, neither the token nor the password appears anywhere in the users or api_tokens tables"""
        token = token_for('standard_user')
        password = TestData.password('standard_user')
        stored = [str(value) for table in ('users', 'api_tokens')
                  for row in shop_db.execute(f'SELECT * FROM {table}') for value in tuple(row)]
        assert not [v for v in stored if token in v], 'The token is stored as plain text'
        assert not [v for v in stored if v == password], 'A password is stored as plain text'

    def test_logout_deletes_the_cart_rows(self, shop_db, api, token_for, ids):
        """The cart rows of a login are in the database until logout, and gone right after it"""
        token = token_for()
        user = api.with_token(token)
        user.add_to_cart('Sauce Labs Backpack', ids)
        user.add_to_cart('Sauce Labs Bike Light', ids)
        assert cart_rows(shop_db, token) == 2
        assert user.post('auth/logout').status_code == 204
        assert cart_rows(shop_db, token) == 0, 'The cart rows are still in the database after logout'

    def test_an_order_keeps_its_own_copy_of_the_items(self, shop_db, user_api, ids, payment_mock):
        """order_items stores name and price of what was bought: a later catalog change cannot alter old orders"""
        user_api.add_to_cart('Sauce Labs Backpack', ids)
        order = user_api.post('orders', json={'first_name': 'A', 'last_name': 'B', 'postal_code': 'C',
                                              'card': 'SauceCard #31337'}).json()
        rows = shop_db.execute('SELECT name, price_cents FROM order_items WHERE order_id = ?',
                               (order['id'],)).fetchall()
        assert [(r['name'], r['price_cents']) for r in rows] == [('Sauce Labs Backpack', 2999)]
        totals = shop_db.execute('SELECT subtotal_cents, tax_cents, total_cents FROM orders WHERE id = ?',
                                 (order['id'],)).fetchone()
        assert tuple(totals) == (2999, 240, 3239)  # whole cents: 29.99 + 8% tax
