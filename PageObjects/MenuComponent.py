# Burger menu: it is on every page after login, so it is a component and not part of one page
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class MenuComponent(AbstractPage):
    # Locators
    __BurguerMenu_Xpath = '//button[@id="react-burger-menu-btn"]'
    __Close_Xpath = '//button[@id="react-burger-cross-btn"]'
    __AllItems_Xpath = '//a[@id="inventory_sidebar_link"]'
    __Logout_Xpath = '//a[@id="logout_sidebar_link"]'
    __MenuWrap_Xpath = '//div[contains(@class,"bm-menu-wrap")]'

    @step('open the side menu')
    def Open(self):
        self.engine.click(self.__BurguerMenu_Xpath)

    @step('close the side menu')
    def Close(self):
        self.engine.click(self.__Close_Xpath)

    @step('click All Items in the menu')
    def ClickAllItems(self):
        self.engine.click(self.__AllItems_Xpath)

    @step('click Logout in the menu')
    def ClickLogout(self):
        self.engine.click(self.__Logout_Xpath)

    @step('check whether the side menu is open')
    def IsOpen(self):
        return self.engine.attribute(self.__MenuWrap_Xpath, 'aria-hidden') == 'false'
