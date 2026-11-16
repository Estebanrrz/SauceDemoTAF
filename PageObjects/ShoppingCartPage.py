# Shoppingcart Page

from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class ShoppingCartPage(AbstractPage):
    # Locators
    __Button_Checkout_Xpath = '//button[@id="checkout"]'
    __Button_Continue_Shopping_Xpath = '//button[@id="continue-shopping"]'
    __Cart_Title_Xpath = '//span[@class="title"][text()="Your Cart"]'
    __Item_Names_Xpath = '//div[@class="cart_item"]//div[@data-test="inventory-item-name"]'
    __Remove_By_Name_Xpath = '//div[@class="cart_item"][.//div[@data-test="inventory-item-name"]' \
                             '[normalize-space()="{name}"]]//button[contains(text(),"Remove")]'

    @step('click Checkout')
    def ClickButtonCheckout(self):
        self.engine.click(self.__Button_Checkout_Xpath)

    @step('click Continue Shopping')
    def ClickContinueShopping(self):
        self.engine.click(self.__Button_Continue_Shopping_Xpath)

    @step('remove {itemName} from the cart')
    def RemoveItem(self, itemName):
        self.engine.click(self.__Remove_By_Name_Xpath.format(name=itemName))

    @step('read the products in the cart')
    def GetItemNames(self):
        # Wait for the page first, then read the list (it can be empty)
        self.engine.wait_for(self.__Cart_Title_Xpath)
        return self.engine.texts(self.__Item_Names_Xpath)
