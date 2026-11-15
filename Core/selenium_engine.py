# Selenium implementation of Engine (Chrome / Chromium).
#
# Browser: CHROME_BIN, else the Chromium bundled with Playwright (PLAYWRIGHT_BROWSERS_PATH), else
# the Chrome installed on the machine.
# Driver, in this order:
#   1. CHROMEDRIVER environment variable
#   2. chromedriver-py, only when the bundled Chromium is used (that is the version it matches)
#   3. Selenium Manager (needs internet)
#   4. Drivers/chromedriver.exe kept in the repo, if the steps above fail

import glob
import os

from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException, NoAlertPresentException,
                                        StaleElementReferenceException, WebDriverException)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from Core.engine import Engine
from Utilities.readProperties import ReadConfig


def _bundled_chromium():
    """Newest Chromium inside PLAYWRIGHT_BROWSERS_PATH, or None."""
    browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
    candidates = sorted(glob.glob(os.path.join(browsers_path, 'chromium-*', 'chrome-linux*', 'chrome')))
    return candidates[-1] if candidates else None


def _chrome_binary():
    explicit = os.environ.get('CHROME_BIN')
    if explicit and os.path.exists(explicit):
        return explicit
    return _bundled_chromium()


def _chromedriver_path(chrome_binary):
    explicit = os.environ.get('CHROMEDRIVER')
    if explicit and os.path.exists(explicit):
        return explicit
    if chrome_binary and chrome_binary == _bundled_chromium():
        try:
            from chromedriver_py import binary_path
            return binary_path
        except ImportError:
            pass
    return None  # Selenium Manager decides


class SeleniumEngine(Engine):
    name = 'selenium'

    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        binary = _chrome_binary()
        if binary:
            options.binary_location = binary
        if headless:
            options.add_argument('--headless=new')
        for arg in ('--window-size=1280,900', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'):
            options.add_argument(arg)
        driver_path = _chromedriver_path(binary)
        try:
            service = Service(executable_path=driver_path) if driver_path else Service()
            self.driver = webdriver.Chrome(service=service, options=options)
        except WebDriverException:
            local = ReadConfig.getLocalDriverPath()
            if driver_path == local or not os.path.exists(local):
                raise
            self.driver = webdriver.Chrome(service=Service(executable_path=local), options=options)
        self.driver.set_page_load_timeout(ReadConfig.getPageLoadTimeout())

    def _wait(self):
        return WebDriverWait(self.driver, ReadConfig.getExplicitWait())

    def _present(self, xpath):
        return self._wait().until(EC.presence_of_element_located((By.XPATH, xpath)))

    # ---- navigation ----
    def goto(self, url):
        self.driver.get(url)

    def reload(self):
        self.driver.refresh()

    @property
    def current_url(self):
        return self.driver.current_url

    def open_new_tab(self, url):
        self.driver.switch_to.new_window('tab')
        self.driver.get(url)

    # ---- actions ----
    def click(self, xpath):
        # The page can re-render between finding the element and clicking it: try again
        for attempt in range(3):
            try:
                self._wait().until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                return
            except (StaleElementReferenceException, ElementClickInterceptedException):
                if attempt == 2:
                    raise

    def fill(self, xpath, text):
        element = self._present(xpath)
        element.clear()
        element.send_keys(text)

    def select_by_label(self, xpath, label):
        Select(self._present(xpath)).select_by_visible_text(label)

    # ---- reading ----
    def text(self, xpath):
        return self._present(xpath).text

    def texts(self, xpath):
        return [e.text for e in self.driver.find_elements(By.XPATH, xpath)]

    def value(self, xpath):
        return self._present(xpath).get_attribute('value')

    def attribute(self, xpath, name):
        return self._present(xpath).get_attribute(name)

    def count(self, xpath):
        return len(self.driver.find_elements(By.XPATH, xpath))

    def wait_for(self, xpath):
        self._present(xpath)

    # ---- page state ----
    def evaluate(self, expression):
        return self.driver.execute_script(f'return ({expression});')

    def no_alert_is_present(self):
        try:
            self.driver.switch_to.alert.dismiss()
            return False
        except NoAlertPresentException:
            return True

    def quit(self):
        self.driver.quit()
