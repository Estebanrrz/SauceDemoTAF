#Checkout Step Page
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class CheckOutStepOnePage(AbstractPage):
    # Locators
    __FirstName_Field_Xpath = '//*[@id="first-name"]'
    __LastName_Field_Xpath = '//*[@id="last-name"]'
    __ZipCode_Field_Xpath = '//*[@id="postal-code"]'
    __Continue_Button_xpath = '//*[@id="continue"]'

    @step("type the first name '{name}'")
    def SetValueOnFirstName(self, name):
        self.engine.fill(self.__FirstName_Field_Xpath, name)

    @step("type the last name '{lastName}'")
    def SetValueOnLastName(self, lastName):
        self.engine.fill(self.__LastName_Field_Xpath, lastName)

    @step("type the postal code '{zipcode}'")
    def SetValueOnZipCode(self, zipcode):
        self.engine.fill(self.__ZipCode_Field_Xpath, zipcode)

    @step("fill in the customer details: '{firstName}' '{lastName}' '{zipcode}'")
    def FillInformation(self, firstName, lastName, zipcode):
        self.SetValueOnFirstName(firstName)
        self.SetValueOnLastName(lastName)
        self.SetValueOnZipCode(zipcode)

    @step('click Continue')
    def ClickOnContinueButton(self):
        self.engine.click(self.__Continue_Button_xpath)

    @step('read the checkout form fields')
    def GetFieldValues(self):
        return (self.engine.value(self.__FirstName_Field_Xpath),
                self.engine.value(self.__LastName_Field_Xpath),
                self.engine.value(self.__ZipCode_Field_Xpath))
