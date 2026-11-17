# Catalog through the API (GET /api/v1/products): content, sorting, one product, errors
#
# The expected data comes from Data/products.json, the file the app copies into its database.
import pytest

from tests_api.checks import PRODUCT, check_contract, check_error, json_of
from Utilities.testData import TestData

PRICES = TestData.products()  # {name: price}

# Expected order of the names for each sort value (same rules as the sort box of the products page)
EXPECTED_ORDER = {
    'az': sorted(PRICES),
    'za': sorted(PRICES, reverse=True),
    'lohi': sorted(PRICES, key=lambda name: (PRICES[name], name)),   # equal prices: by name
    'hilo': sorted(PRICES, key=lambda name: (-PRICES[name], name)),
}


def products_of(response):
    body = json_of(response, 200)
    assert set(body) == {'products'}, f'Expected only "products" in the body, got {list(body)}'
    return body['products']


class TestCatalog:
    def test_catalog_matches_the_test_data(self, user_api):
        """The API lists exactly the products and prices of Data/products.json"""
        products = products_of(user_api.get('products'))
        actual = {p['name']: p['price'] for p in products}
        assert actual == PRICES, f'Expected {PRICES}, got {actual}'

    def test_every_product_has_the_expected_fields(self, user_api):
        """Every product has id, slug, name, description and price with the right types; ids and slugs are unique"""
        products = products_of(user_api.get('products'))
        for product in products:
            check_contract(product, PRODUCT, f"product {product.get('name')!r}")
            assert product['price'] > 0, f'Price must be positive: {product}'
        assert len({p['id'] for p in products}) == len(products), 'Repeated ids'
        assert len({p['slug'] for p in products}) == len(products), 'Repeated slugs'


class TestSorting:
    @pytest.mark.parametrize('sort', list(EXPECTED_ORDER))
    def test_each_sort_value_orders_the_products(self, user_api, sort):
        """?sort=az|za|lohi|hilo gives the same order as the products page (equal prices by name)"""
        names = [p['name'] for p in products_of(user_api.get('products', params={'sort': sort}))]
        assert names == EXPECTED_ORDER[sort], f'sort={sort}: expected {EXPECTED_ORDER[sort]}, got {names}'

    def test_default_order_is_by_name(self, user_api):
        """Without ?sort the products come A to Z, like the products page"""
        names = [p['name'] for p in products_of(user_api.get('products'))]
        assert names == EXPECTED_ORDER['az']

    @pytest.mark.parametrize('sort', ['price', 'AZ', '', 'az;DROP'])
    def test_unknown_sort_value_is_rejected(self, user_api, sort):
        """A sort value that is not az, za, lohi or hilo answers 400 invalid_sort (values are case sensitive)"""
        check_error(user_api.get('products', params={'sort': sort}), 400, 'invalid_sort',
                    'sort must be one of: az, za, lohi, hilo')


class TestOneProduct:
    def test_each_product_can_be_read_by_id(self, user_api):
        """GET /products/<id> gives the same data as the list, for every product"""
        for product in products_of(user_api.get('products')):
            assert json_of(user_api.get(f"products/{product['id']}"), 200) == product

    @pytest.mark.parametrize('product_id', [0, 9999])
    def test_unknown_id_is_a_404(self, user_api, product_id):
        """An id that does not exist answers 404 product_not_found"""
        check_error(user_api.get(f'products/{product_id}'), 404, 'product_not_found')

    def test_id_that_is_not_a_number_is_a_404(self, user_api):
        """/products/abc is not a product URL: 404 not_found"""
        check_error(user_api.get('products/abc'), 404, 'not_found')


class TestNeedsToken:
    @pytest.mark.parametrize('path', ['products', 'products/1'])
    def test_catalog_needs_a_token(self, api, path):
        """Like the products page needs a logged-in user, the catalog needs a token"""
        check_error(api.get(path), 401, 'missing_token')
