# Inventory Page
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class InventoryPage(AbstractPage):
    # Locators
    __Item_Button_By_Name_Xpath = '//div[@data-test="inventory-item-name"][normalize-space()="{name}"]' \
                                  '/ancestor::div[@data-test="inventory-item"]' \
                                  '//button[contains(@class,"btn_inventory")]'
    __All_Item_Buttons_Xpath = '//button[contains(@class,"btn_inventory")]'
    __Item_Button_By_Text_Xpath = '(//button[contains(@class,"btn_inventory")][normalize-space()="{text}"])[1]'
    __Item_Names_Xpath = '//div[@data-test="inventory-item-name"]'
    __Item_Prices_Xpath = '//div[@data-test="inventory-item-price"]'
    __Sort_Select_Xpath = '//select[@class="product_sort_container"]'
    __Button_Shopping_Cart_Xpath = '//*[@id="shopping_cart_container"]/a'
    __Count_ShoppingCart_Xpath = '//*[@id="shopping_cart_container"]/a/span'

    @step('add {itemName} to the cart')
    def AddtoCartItem(self, itemName):
        # The same button switches between "Add to cart" and "Remove"
        self.engine.click(self.__Item_Button_By_Name_Xpath.format(name=itemName))

    @step('read the button of {itemName}')
    def GetItemButtonText(self, itemName):
        return self.engine.text(self.__Item_Button_By_Name_Xpath.format(name=itemName))

    @step("click every '{text}' button on the products page")
    def ClickAllButtonsWithText(self, text):
        """Click every product button labelled text ("Add to cart" / "Remove"). Returns how many."""
        self.engine.wait_for(self.__All_Item_Buttons_Xpath)
        clicked = 0
        limit = 3 * self.engine.count(self.__All_Item_Buttons_Xpath)  # never loop forever
        for _ in range(limit):
            if text not in self.GetButtonTexts():
                return clicked
            self.engine.click(self.__Item_Button_By_Text_Xpath.format(text=text))
            clicked += 1
        raise AssertionError(f"Some buttons are still '{text}' after {limit} attempts")

    @step('read the buttons of all products')
    def GetButtonTexts(self):
        self.engine.wait_for(self.__All_Item_Buttons_Xpath)
        return self.engine.texts(self.__All_Item_Buttons_Xpath)

    @step('read the product names')
    def GetItemNames(self):
        self.engine.wait_for(self.__Item_Names_Xpath)
        return self.engine.texts(self.__Item_Names_Xpath)

    @step('read the product prices')
    def GetItemPrices(self):
        self.engine.wait_for(self.__Item_Prices_Xpath)
        return [float(p.replace('$', '')) for p in self.engine.texts(self.__Item_Prices_Xpath)]

    @step('read the product catalog (names and prices)')
    def GetCatalog(self):
        """Products shown on the page as {name: price}."""
        return dict(zip(self.GetItemNames(), self.GetItemPrices()))

    @step("sort the products by '{option}'")
    def SortBy(self, option):
        self.engine.select_by_label(self.__Sort_Select_Xpath, option)

    @step('open the shopping cart')
    def ClickShoppingCartButton(self):
        self.engine.click(self.__Button_Shopping_Cart_Xpath)

    @step('read the cart counter')
    def GetCounterShoppincart(self):
        return self.engine.text(self.__Count_ShoppingCart_Xpath)

    @step('check whether the cart counter is shown')
    def IsCartBadgeDisplayed(self):
        return self.engine.count(self.__Count_ShoppingCart_Xpath) > 0
