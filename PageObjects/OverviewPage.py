#Overview Page
from PageObjects.AbstractPage import AbstractPage


class OverviewPage(AbstractPage):
    # Locators
    __Button_Fisnish_Xpath = '//button[@id="finish"]'
    __Total_Xpath = '//div[contains(@class,"summary_total_label")]'

    def ClickFinishButton(self):
        AbstractPage.find_element_by_Xpath(self, self.__Button_Fisnish_Xpath).click()

    def GetTotal(self):
        total = AbstractPage.find_element_by_Xpath(self, self.__Total_Xpath).text
        return total
