#Checkout Complete Page
from PageObjects.AbstractPage import AbstractPage


class CheckoutCompletePage(AbstractPage):
    # locators
    __Title_ThankYou_Xpath = '//*[@id="checkout_complete_container"]/h2'

    def ThankYouForYourOrderIsDisplayed(self):
        return AbstractPage.find_element_by_Xpath(self, self.__Title_ThankYou_Xpath).is_displayed()
