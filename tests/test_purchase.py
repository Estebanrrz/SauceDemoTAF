# Purchase scenarios (end to end)
import pytest

from Utilities.testData import TestData

TAX_RATE = 0.08


def go_to_overview(pages, products):
    """Add the products, go through the cart and the customer form, and land on the overview."""
    for product in products:
        pages.inventory.AddtoCartItem(product)
    pages.inventory.ClickShoppingCartButton()
    pages.cart.ClickButtonCheckout()
    customer = TestData.customer()
    pages.checkout_one.FillInformation(customer['firstName'], customer['lastName'], customer['postalCode'])
    pages.checkout_one.ClickOnContinueButton()


class TestPurchase:
    @pytest.mark.parametrize('products', [
        pytest.param(['Sauce Labs Backpack', 'Sauce Labs Bike Light'], id='several-products'),
        pytest.param(['Sauce Labs Bike Light'], id='one-product'),
    ])
    def test_simple_purchase(self, logged_in, pages, products):
        """Compra simple de uno o varios productos"""
        go_to_overview(pages, products)
        pages.overview.ClickFinishButton()
        assert pages.complete.ThankYouForYourOrderIsDisplayed() is True

    def test_cart_counter_shows_the_number_of_products(self, logged_in, pages):
        """Verificar numero en el carro de compras"""
        pages.inventory.AddtoCartItem('Sauce Labs Backpack')
        pages.inventory.AddtoCartItem('Sauce Labs Bike Light')
        assert pages.inventory.GetCounterShoppincart() == '2', 'The cart counter is not the expected one'

    def test_overview_total(self, logged_in, pages):
        """Verificar el total: Backpack + Bike Light = $43.18"""
        go_to_overview(pages, ['Sauce Labs Backpack', 'Sauce Labs Bike Light'])
        assert pages.overview.GetTotal() == 'Total: $43.18', 'The total is not the expected one'

    # ---- new scenario ----
    def test_complete_order_summary_confirmation_and_empty_cart(self, logged_in, pages):
        """Orden completa: resumen (items, subtotal, impuesto, total), confirmacion y carro vacio al final"""
        products = ['Sauce Labs Backpack', 'Sauce Labs Bike Light']
        go_to_overview(pages, products)
        catalog = TestData.products()
        subtotal = round(sum(catalog[p] for p in products), 2)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)
        assert pages.overview.GetItemNames() == products
        assert pages.overview.GetSubtotal() == f'Item total: ${subtotal:.2f}'
        assert pages.overview.GetTax() == f'Tax: ${tax:.2f}'
        assert pages.overview.GetTotal() == f'Total: ${total:.2f}'
        pages.overview.ClickFinishButton()
        assert pages.complete.ThankYouForYourOrderIsDisplayed() is True
        assert not pages.inventory.IsCartBadgeDisplayed(), 'The cart counter is still visible'
        pages.inventory.ClickShoppingCartButton()
        assert pages.cart.GetItemNames() == [], 'The cart is not empty'
