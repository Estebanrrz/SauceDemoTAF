# Base Page
# Page objects receive an Engine and never touch Selenium or Playwright directly,
# so each page is written once and works on both.
from abc import ABC

from Utilities.steps import step


class AbstractPage(ABC):
    __Error_Message_Xpath = '//*[@data-test="error"]'

    def __init__(self, engine):
        self.engine = engine

    @step('read the error message')
    def GetErrorMessage(self):
        return self.engine.text(self.__Error_Message_Xpath)

    @step('count the error messages on the page')
    def ErrorCount(self):
        self.engine.wait_for(self.__Error_Message_Xpath)
        return self.engine.count(self.__Error_Message_Xpath)
