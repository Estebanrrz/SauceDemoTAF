# Inventory Page
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import Select

from PageObjects.AbstractPage import AbstractPage


class InventoryPage(AbstractPage):
    # Locators
    __Inventory_Item_By_Name_Xpath = '//div[@data-test="inventory-item-name"][contains(text(),' \
                                     '"$itemName$")]/ancestor::div[@data-test="inventory-item"] '
    __Button_Add_To_Cart_Xpath = './/button[ contains(@class,"btn_inventory")]'
    __All_Item_Buttons_Xpath = '//button[contains(@class,"btn_inventory")]'
    __Item_Names_Xpath = '//div[@data-test="inventory-item-name"]'
    __Item_Prices_Xpath = '//div[@data-test="inventory-item-price"]'
    __Sort_Select_Xpath = '//select[@class="product_sort_container"]'
    __Button_Shopping_Cart_Xpath = '//*[@id="shopping_cart_container"]/a'
    __Count_ShoppingCart_Xpath = '//*[@id="shopping_cart_container"]/a/span'

    def AddtoCartItem(self, itemName):
        item = AbstractPage.find_element_by_Xpath(self,
                                                  self.__Inventory_Item_By_Name_Xpath.replace("$itemName$", itemName))
        item.find_element("xpath", self.__Button_Add_To_Cart_Xpath).click()

    def ClickAllButtonsWithText(self, text):
        """Click every product button whose label equals text ("Add to cart" / "Remove"). Returns how many."""
        AbstractPage.find_element_by_Xpath(self, self.__All_Item_Buttons_Xpath)
        clicked = 0
        limit = 3 * len(self.find_elements_by_Xpath(self.__All_Item_Buttons_Xpath))  # never loop forever
        for _ in range(limit):
            try:
                pending = [b for b in self.find_elements_by_Xpath(self.__All_Item_Buttons_Xpath) if b.text == text]
                if not pending:
                    return clicked
                pending[0].click()
                clicked += 1
            except StaleElementReferenceException:
                continue  # the page re-rendered; look the buttons up again
        raise AssertionError(f"Some buttons are still '{text}' after {limit} attempts")

    def GetButtonTexts(self):
        AbstractPage.find_element_by_Xpath(self, self.__All_Item_Buttons_Xpath)
        return [b.text for b in self.find_elements_by_Xpath(self.__All_Item_Buttons_Xpath)]

    def GetItemButtonText(self, itemName):
        item = AbstractPage.find_element_by_Xpath(self,
                                                  self.__Inventory_Item_By_Name_Xpath.replace("$itemName$", itemName))
        return item.find_element("xpath", self.__Button_Add_To_Cart_Xpath).text

    def GetItemNames(self):
        AbstractPage.find_element_by_Xpath(self, self.__Item_Names_Xpath)
        return [e.text for e in self.find_elements_by_Xpath(self.__Item_Names_Xpath)]

    def GetItemPrices(self):
        AbstractPage.find_element_by_Xpath(self, self.__Item_Prices_Xpath)
        return [float(e.text.replace('$', '')) for e in self.find_elements_by_Xpath(self.__Item_Prices_Xpath)]

    def GetCatalog(self):
        """Products shown in the inventory as {name: price}."""
        return dict(zip(self.GetItemNames(), self.GetItemPrices()))

    def SortBy(self, visibleText):
        Select(AbstractPage.find_element_by_Xpath(self, self.__Sort_Select_Xpath)).select_by_visible_text(visibleText)

    def ClickShoppingCartButton(self):
        AbstractPage.click_by_Xpath(self, self.__Button_Shopping_Cart_Xpath)

    def GetCounterShoppincart(self):
        return AbstractPage.find_element_by_Xpath(self, self.__Count_ShoppingCart_Xpath).text

    def IsCartBadgeDisplayed(self):
        return len(self.find_elements_by_Xpath(self.__Count_ShoppingCart_Xpath)) > 0
