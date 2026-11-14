# Shoppingcart Page

from PageObjects.AbstractPage import AbstractPage


class ShoppingCartPage(AbstractPage):
    # Locators
    __Button_Checkout_Xpath = '//button[@id="checkout"]'
    __Button_Continue_Shopping_Xpath = '//button[@id="continue-shopping"]'
    __Cart_Title_Xpath = '//span[@class="title"][text()="Your Cart"]'
    __Item_Names_Xpath = '//div[@class="cart_item"]//div[@data-test="inventory-item-name"]'

    def ClickButtonCheckout(self):
        AbstractPage.click_by_Xpath(self, self.__Button_Checkout_Xpath)

    def ClickContinueShopping(self):
        AbstractPage.click_by_Xpath(self, self.__Button_Continue_Shopping_Xpath)

    def GetItemNames(self):
        # Wait for the page itself, then read the (possibly empty) list
        AbstractPage.find_element_by_Xpath(self, self.__Cart_Title_Xpath)
        return [e.text for e in self.find_elements_by_Xpath(self.__Item_Names_Xpath)]
