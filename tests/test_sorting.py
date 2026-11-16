# Sorting scenarios
import pytest

# How each option must leave the list
ORDER_CHECKS = {
    'Name (A to Z)': lambda names, prices: names == sorted(names),
    'Name (Z to A)': lambda names, prices: names == sorted(names, reverse=True),
    'Price (low to high)': lambda names, prices: prices == sorted(prices),
    'Price (high to low)': lambda names, prices: prices == sorted(prices, reverse=True),
}


class TestSorting:
    def test_oos12_equal_prices_keep_the_name_order(self, logged_in, pages):
        """OOS-12: precios iguales mantienen un orden estable por nombre"""
        pages.inventory.SortBy('Price (low to high)')
        names = pages.inventory.GetItemNames()
        prices = pages.inventory.GetItemPrices()
        assert ORDER_CHECKS['Price (low to high)'](names, prices), \
            f'Unexpected order for Price (low to high): {list(zip(names, prices))}'
        pairs = list(zip(prices, names))
        same_price_in_name_order = all(a[1] <= b[1] for a, b in zip(pairs, pairs[1:]) if a[0] == b[0])
        assert same_price_in_name_order, f'Unstable order between equal prices: {pairs}'

    @pytest.mark.parametrize('option', list(ORDER_CHECKS))
    def test_oos13_sorting_does_not_touch_the_cart(self, logged_in, pages, option):
        """OOS-13: ordenar nunca cambia el contenido del carro"""
        added = ['Sauce Labs Backpack', 'Sauce Labs Bike Light']
        for product in added:
            pages.inventory.AddtoCartItem(product)
        pages.inventory.SortBy(option)
        assert pages.inventory.GetCounterShoppincart() == '2', 'The cart counter is not the expected one'
        pages.inventory.ClickShoppingCartButton()
        actual = pages.cart.GetItemNames()
        assert actual == added, f'Expected {added}, got {actual}'

    # ---- new scenario ----
    @pytest.mark.parametrize('option', list(ORDER_CHECKS))
    def test_each_option_sorts_the_products(self, logged_in, pages, option):
        """Ordenar por cada una de las 4 opciones y comprobar el orden"""
        pages.inventory.SortBy(option)
        names = pages.inventory.GetItemNames()
        prices = pages.inventory.GetItemPrices()
        assert names and prices, 'The products page lists no products'
        assert ORDER_CHECKS[option](names, prices), f'Unexpected order for {option}: {list(zip(names, prices))}'
