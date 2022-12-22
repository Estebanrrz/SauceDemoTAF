#Login Page
from PageObjects.AbstractPage import AbstractPage


class LoginPage(AbstractPage):
    # Locators
    __Textbox_UserName_Xpath = '//input[@id="user-name"]'
    __Textbox_Password_Xpath = '//input[@id="password"]'
    __Button_Login_Xpath = '//input[@id="login-button"]'


    def setUserName(self, username):
        AbstractPage.find_element_by_Xpath(self, self.__Textbox_UserName_Xpath).clear()
        AbstractPage.find_element_by_Xpath(self, self.__Textbox_UserName_Xpath).send_keys(username)

    def setPassword(self, password):
        AbstractPage.find_element_by_Xpath(self, self.__Textbox_Password_Xpath).clear()
        AbstractPage.find_element_by_Xpath(self, self.__Textbox_Password_Xpath).send_keys(password)

    def clickLoginButton(self):
        AbstractPage.find_element_by_Xpath(self, self.__Button_Login_Xpath).click()

