# Burger menu: it is on every page after login, so it is a component and not part of one page.
# On the phone layout the burger is hidden and the menu opens with #mobile-menu-button instead.
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class MenuComponent(AbstractPage):
    # Locators
    __BurguerMenu_Xpath = '//button[@id="react-burger-menu-btn"]'
    __MobileMenu_Xpath = '//button[@id="mobile-menu-button"]'
    __Header_Xpath = '//header[@data-test="primary-header"]'
    __Close_Xpath = '//button[@id="react-burger-cross-btn"]'
    __AllItems_Xpath = '//a[@id="inventory_sidebar_link"]'
    __Logout_Xpath = '//a[@id="logout_sidebar_link"]'
    __MenuWrap_Xpath = '//div[contains(@class,"bm-menu-wrap")]'

    @step('open the side menu')
    def Open(self):
        # Chosen from the device, not from what is visible: a broken phone layout must fail, not fall back
        self.engine.click(self.__MobileMenu_Xpath if self.engine.phone_layout else self.__BurguerMenu_Xpath)

    @step('close the side menu')
    def Close(self):
        self.engine.click(self.__Close_Xpath)

    @step('click All Items in the menu')
    def ClickAllItems(self):
        self.engine.click(self.__AllItems_Xpath)

    @step('click Logout in the menu')
    def ClickLogout(self):
        self.engine.click(self.__Logout_Xpath)

    @step('check whether the phone menu button is visible')
    def IsMobileButtonVisible(self):
        self.engine.wait_for(self.__Header_Xpath)
        return self.engine.is_visible(self.__MobileMenu_Xpath)

    @step('check whether the desktop menu button is visible')
    def IsDesktopButtonVisible(self):
        self.engine.wait_for(self.__Header_Xpath)
        return self.engine.is_visible(self.__BurguerMenu_Xpath)

    @step('check whether the side menu is open')
    def IsOpen(self):
        return self.engine.attribute(self.__MenuWrap_Xpath, 'aria-hidden') == 'false'
