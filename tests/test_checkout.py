# Checkout validation scenarios
from Utilities.testData import TestData


class TestCheckout:
    def test_oos04_invalid_postal_code_is_accepted(self, go_to_page, pages, engine):
        """OOS-04 (product decision pending): un codigo postal con formato invalido se acepta.
        Documents what the site does today."""
        go_to_page('checkout step one')
        pages.checkout_one.FillInformation('FirstName', 'LastName', 'not-a-zip!!')
        pages.checkout_one.ClickOnContinueButton()
        engine.wait_until(lambda: 'checkout-step-two.html' in engine.current_url,
                          'Not on the checkout overview page',
                          label='check the checkout overview page is shown')

    def test_oos20_empty_form_shows_only_the_first_error(self, go_to_page, pages):
        """OOS-20: con todos los campos vacios solo se muestra el primer error"""
        go_to_page('checkout step one')
        pages.checkout_one.ClickOnContinueButton()
        actual = pages.checkout_one.GetErrorMessage()
        assert 'First Name is required' in actual, f"Expected 'First Name is required', got '{actual}'"
        assert pages.checkout_one.ErrorCount() == 1, 'More than one error is shown'

    def test_oos21_typed_values_are_kept_after_an_error(self, go_to_page, pages):
        """OOS-21: los valores digitados se conservan despues de un error de validacion"""
        go_to_page('checkout step one')
        pages.checkout_one.SetValueOnFirstName('FirstName')
        pages.checkout_one.SetValueOnLastName('LastName')
        pages.checkout_one.ClickOnContinueButton()
        actual = pages.checkout_one.GetErrorMessage()
        assert 'Postal Code is required' in actual, f"Expected 'Postal Code is required', got '{actual}'"
        first, last, _ = pages.checkout_one.GetFieldValues()
        assert (first, last) == ('FirstName', 'LastName'), f'Values: {first!r}, {last!r}'

    def test_oos23_second_order_works_after_the_first(self, go_to_page, pages):
        """OOS-23: despues de una orden los botones vuelven a Add to cart y una segunda orden funciona"""
        go_to_page('checkout complete')
        pages.menu.Open()
        pages.menu.ClickAllItems()
        texts = pages.inventory.GetButtonTexts()
        assert texts and all(t == 'Add to cart' for t in texts), f'Buttons: {texts}'
        assert not pages.inventory.IsCartBadgeDisplayed(), 'The cart counter is still visible'
        pages.inventory.AddtoCartItem('Sauce Labs Bike Light')
        pages.inventory.ClickShoppingCartButton()
        pages.cart.ClickButtonCheckout()
        customer = TestData.customer()
        pages.checkout_one.FillInformation(customer['firstName'], customer['lastName'], customer['postalCode'])
        pages.checkout_one.ClickOnContinueButton()
        pages.overview.ClickFinishButton()
        assert pages.complete.ThankYouForYourOrderIsDisplayed() is True
