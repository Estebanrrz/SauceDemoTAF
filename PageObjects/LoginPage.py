#Login Page
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class LoginPage(AbstractPage):
    # Locators
    __Textbox_UserName_Xpath = '//input[@id="user-name"]'
    __Textbox_Password_Xpath = '//input[@id="password"]'
    __Button_Login_Xpath = '//input[@id="login-button"]'

    @step("type the username '{username}'")
    def SetUserName(self, username):
        self.engine.fill(self.__Textbox_UserName_Xpath, username)

    @step('type the password {password}')
    def SetPassword(self, password):
        self.engine.fill(self.__Textbox_Password_Xpath, password)

    @step('click the Login button')
    def ClickLoginButton(self):
        self.engine.click(self.__Button_Login_Xpath)

    @step('log in as {username} with password {password}')
    def Login(self, username, password):
        self.SetUserName(username)
        self.SetPassword(password)
        self.ClickLoginButton()

    @step('read the username field')
    def GetUserNameValue(self):
        return self.engine.value(self.__Textbox_UserName_Xpath)

    @step('read the password field')
    def GetPasswordValue(self):
        return self.engine.value(self.__Textbox_Password_Xpath)
