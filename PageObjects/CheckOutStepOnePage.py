#Checkout Step Page
from PageObjects.AbstractPage import AbstractPage


class CheckOutStepOnePage(AbstractPage):
    # Locators
    __FirstName_Field_Xpath = '//*[@id="first-name"]'
    __LastName_Field_Xpath = '//*[@id="last-name"]'
    __ZipCode_Field_Xpath = '//*[@id="postal-code"]'
    __Continue_Button_xpath = '//*[@id="continue"]'


    def SetValueOnFirstName(self, name):
        AbstractPage.find_element_by_Xpath(self, self.__FirstName_Field_Xpath).send_keys(name)

    def SetValueOnLastName(self, lastName):
        AbstractPage.find_element_by_Xpath(self, self.__LastName_Field_Xpath).send_keys(lastName)

    def SetValueOnZipCode(self, zipcode):
        AbstractPage.find_element_by_Xpath(self, self.__ZipCode_Field_Xpath).send_keys(zipcode)

    def ClickOnContinueButton(self):
        AbstractPage.find_element_by_Xpath(self, self.__Continue_Button_xpath).click()
