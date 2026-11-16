# Playwright implementation of Engine (Chromium).
#
# Uses the browsers Playwright already has (PLAYWRIGHT_BROWSERS_PATH, or /opt/pw-browsers when it exists), so
# nothing is downloaded. Without a Playwright Chromium it uses the installed Chrome (PLAYWRIGHT_CHANNEL=chrome forces it).
# One browser process is shared by all tests; every Engine gets its own clean context.

import atexit
import os

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from Core.engine import Engine
from Utilities.readProperties import ReadConfig

_playwright = None
_browser = None
_headless = None

OFFLINE_BROWSERS = '/opt/pw-browsers'


def _launch(headless):
    channel = ReadConfig.getBrowserChannel()
    try:
        return _playwright.chromium.launch(headless=headless, channel=channel)
    except PlaywrightError as no_chromium:
        if channel:
            raise
        # Playwright has no Chromium here: use the Chrome installed on the machine
        try:
            return _playwright.chromium.launch(headless=headless, channel='chrome')
        except PlaywrightError:
            raise no_chromium


def _get_browser(headless):
    global _playwright, _browser, _headless
    if _browser is not None and _headless != headless:
        _shutdown()
    if _browser is None:
        if not os.environ.get('PLAYWRIGHT_BROWSERS_PATH') and os.path.isdir(OFFLINE_BROWSERS):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = OFFLINE_BROWSERS
        _playwright = sync_playwright().start()
        _browser = _launch(headless)
        _headless = headless
        atexit.register(_shutdown)
    return _browser


def _shutdown():
    global _playwright, _browser
    if _browser is not None:
        _browser.close()
        _browser = None
    if _playwright is not None:
        _playwright.stop()
        _playwright = None


class PlaywrightEngine(Engine):
    name = 'playwright'

    def __init__(self, headless=True):
        self._context = _get_browser(headless).new_context(viewport={'width': 1280, 'height': 900})
        self._context.set_default_timeout(ReadConfig.getExplicitWait() * 1000)
        self._dialog_seen = False
        self.page = self._new_page()

    def _new_page(self):
        page = self._context.new_page()

        def on_dialog(dialog):
            self._dialog_seen = True
            dialog.dismiss()

        page.on('dialog', on_dialog)
        return page

    def _first(self, xpath):
        return self.page.locator(f'xpath={xpath}').first

    # ---- navigation ----
    def goto(self, url):
        self.page.goto(url)

    def reload(self):
        self.page.reload()

    @property
    def current_url(self):
        return self.page.url

    def open_new_tab(self, url):
        self.page = self._new_page()
        self.page.goto(url)

    # ---- actions ----
    def click(self, xpath):
        self._first(xpath).click()

    def fill(self, xpath, text):
        self._first(xpath).fill(text)

    def select_by_label(self, xpath, label):
        self._first(xpath).select_option(label=label)

    # ---- reading ----
    def text(self, xpath):
        locator = self._first(xpath)
        locator.wait_for(state='attached')
        return locator.inner_text()

    def texts(self, xpath):
        return self.page.locator(f'xpath={xpath}').all_inner_texts()

    def value(self, xpath):
        return self._first(xpath).input_value()

    def attribute(self, xpath, name):
        locator = self._first(xpath)
        locator.wait_for(state='attached')
        return locator.get_attribute(name)

    def count(self, xpath):
        return self.page.locator(f'xpath={xpath}').count()

    def wait_for(self, xpath):
        self._first(xpath).wait_for(state='attached')

    # ---- page state ----
    def evaluate(self, expression):
        return self.page.evaluate(expression)

    def no_alert_is_present(self):
        return not self._dialog_seen

    def quit(self):
        self._context.close()
