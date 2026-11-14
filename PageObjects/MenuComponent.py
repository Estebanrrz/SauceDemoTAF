# Burger menu: present on every page after login, so it is a component and not part of one page.
from PageObjects.AbstractPage import AbstractPage


class MenuComponent(AbstractPage):
    # Locators
    __BurguerMenu_Xpath = '//button[@id="react-burger-menu-btn"]'
    __Close_Xpath = '//button[@id="react-burger-cross-btn"]'
    __AllItems_Xpath = '//a[@id="inventory_sidebar_link"]'
    __Logout_Xpath = '//a[@id="logout_sidebar_link"]'
    __MenuWrap_Xpath = '//div[contains(@class,"bm-menu-wrap")]'

    def _click(self, locator):
        # The menu slides in/out with a CSS transition: wait until the item is really clickable.
        self.click_by_Xpath(locator)

    def Open(self):
        self._click(self.__BurguerMenu_Xpath)

    def Close(self):
        self._click(self.__Close_Xpath)

    def ClickAllItems(self):
        self._click(self.__AllItems_Xpath)

    def ClickLogout(self):
        self._click(self.__Logout_Xpath)

    def IsOpen(self):
        return self.find_element_by_Xpath(self.__MenuWrap_Xpath).get_attribute('aria-hidden') == 'false'
