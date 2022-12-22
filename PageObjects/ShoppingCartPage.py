# Shoppingcart Page

from PageObjects.AbstractPage import AbstractPage


class ShoppingCartPage(AbstractPage):
    # Locators
    __Button_Checkout_Xpath = '//button[@id="checkout"]'

    def ClickButtonCheckout(self):
        AbstractPage.find_element_by_Xpath(self, self.__Button_Checkout_Xpath).click()
