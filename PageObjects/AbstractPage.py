# Base Page
from abc import ABC

from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from Utilities.readProperties import ReadConfig


class AbstractPage(ABC):
    __Error_Message_Xpath = '//*[@data-test="error"]'

    def __init__(self, driver):
        self.driver = driver

    def find_element_by_Xpath(self, locator):
        element = WebDriverWait(self.driver, ReadConfig.getExplicitWait()).until(EC.presence_of_element_located((By.XPATH, locator)))
        return element

    def click_by_Xpath(self, locator):
        # Wait until the element is visible and enabled, not merely present in the DOM
        # Retry when the page re-renders between locating and clicking (React replaces DOM nodes)
        for attempt in range(3):
            try:
                WebDriverWait(self.driver, ReadConfig.getExplicitWait()).until(EC.element_to_be_clickable((By.XPATH, locator))).click()
                return
            except (StaleElementReferenceException, ElementClickInterceptedException):
                if attempt == 2:
                    raise

    def find_elements_by_Xpath(self, locator):
        return self.driver.find_elements(By.XPATH, locator)

    def GetErrorMessage(self):
        return AbstractPage.find_element_by_Xpath(self, self.__Error_Message_Xpath).text
