# Base Page
from abc import ABC

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

class AbstractPage(ABC):

    def __init__(self, driver):
        self.driver = driver

    def find_element_by_Xpath(self, locator):
        element = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, locator)))
        return element
