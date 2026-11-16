#Overview Page
from PageObjects.AbstractPage import AbstractPage
from Utilities.steps import step


class OverviewPage(AbstractPage):
    # Locators
    __Button_Fisnish_Xpath = '//button[@id="finish"]'
    __Subtotal_Xpath = '//div[contains(@class,"summary_subtotal_label")]'
    __Tax_Xpath = '//div[contains(@class,"summary_tax_label")]'
    __Total_Xpath = '//div[contains(@class,"summary_total_label")]'
    __Item_Names_Xpath = '//div[@class="cart_item"]//div[@data-test="inventory-item-name"]'

    @step('click Finish')
    def ClickFinishButton(self):
        self.engine.click(self.__Button_Fisnish_Xpath)

    @step('read the products in the order summary')
    def GetItemNames(self):
        self.engine.wait_for(self.__Total_Xpath)
        return self.engine.texts(self.__Item_Names_Xpath)

    @step('read the item total')
    def GetSubtotal(self):
        return self.engine.text(self.__Subtotal_Xpath)

    @step('read the tax')
    def GetTax(self):
        return self.engine.text(self.__Tax_Xpath)

    @step('read the order total')
    def GetTotal(self):
        return self.engine.text(self.__Total_Xpath)
