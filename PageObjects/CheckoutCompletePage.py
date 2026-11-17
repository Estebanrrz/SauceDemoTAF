#Checkout Complete Page
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class CheckoutCompletePage(AbstractPage):
    # locators
    __Title_ThankYou_Xpath = '//*[@id="checkout_complete_container"]/h2'
    __Order_Number_Xpath = '//*[@data-test="order-number"]'

    @step('read the order confirmation message')
    def GetConfirmationText(self):
        return self.engine.text(self.__Title_ThankYou_Xpath)

    @step('read the order number')
    def GetOrderNumber(self):
        """The 'Order #12' line under the confirmation."""
        return self.engine.text(self.__Order_Number_Xpath)

    @step("check the 'Thank you for your order' message")
    def ThankYouForYourOrderIsDisplayed(self):
        return 'Thank you for your order' in self.GetConfirmationText()
