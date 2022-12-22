# Inventory Page
from PageObjects.AbstractPage import AbstractPage


class InventoryPage(AbstractPage):
    # Locators
    __BurguerMenu_Xpath = '//button[@id="react-burger-menu-btn"]'
    __Logout_Xpath = '//a[@id="logout_sidebar_link"]'
    __Inventory_Item_By_Name_Xpath = '//div[@class="inventory_item_name"][contains(text(),' \
                                     '"$itemName$")]/ancestor::div[@class="inventory_item"] '
    __Button_Add_To_Cart_Xpath = './/button[ contains(@class,"btn_inventory")]'
    __Button_Shopping_Cart_Xpath = '//*[@id="shopping_cart_container"]/a'
    __Count_ShoppingCart_Xpath = '//*[@id="shopping_cart_container"]/a/span'

    def AddtoCartItem(self, itemName):
        item = AbstractPage.find_element_by_Xpath(self,
                                                  self.__Inventory_Item_By_Name_Xpath.replace("$itemName$", itemName))
        item.find_element("xpath", self.__Button_Add_To_Cart_Xpath).click()

    def OpenBurguerMenu(self):
        AbstractPage.find_element_by_Xpath(self, self.__BurguerMenu_Xpath).click()

    def ClickLogout(self):
        AbstractPage.find_element_by_Xpath(self, self.__Logout_Xpath).click()

    def ClickShoppingCartButton(self):
        AbstractPage.find_element_by_Xpath(self, self.__Button_Shopping_Cart_Xpath).click()

    def GetCounterShoppincart(self):
        return AbstractPage.find_element_by_Xpath(self, self.__Count_ShoppingCart_Xpath).text
