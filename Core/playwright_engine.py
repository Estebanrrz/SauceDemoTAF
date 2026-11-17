# Playwright implementation of Engine (Chromium).
#
# Uses the browsers Playwright already has (PLAYWRIGHT_BROWSERS_PATH, or /opt/pw-browsers when it exists), so
# nothing is downloaded. Without a Playwright Chromium it uses the installed Chrome (PLAYWRIGHT_CHANNEL=chrome forces it).
# One browser process is shared by all tests; every Engine gets its own clean context.
# Playwright's sync API only works in the thread that started it, so every thread gets its own Playwright
# and browser. The main thread works as always (closed at exit); a test that drives browsers from other
# threads calls close_this_thread() at the end of each of them (Core/factory.py: finish_thread).
#
# --device="iPhone 13" gives the context that Playwright device profile (screen size, user agent,
# touch, pixel density). It always runs on the local Chromium: many profiles (all iPhones) ask for
# WebKit, which is not installed and needs internet to download, so this is not real Safari.

import atexit
import difflib
import os
import threading

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from Core.engine import Engine
from Utilities.readProperties import ReadConfig

_local = threading.local()  # per thread: playwright, browser, headless

DESKTOP_VIEWPORT = {'width': 1280, 'height': 900}
PHONE_MAX_WIDTH = 600  # same breakpoint as the @media rule in app/templates/base.html
OFFLINE_BROWSERS = '/opt/pw-browsers'


def _get_playwright():
    if getattr(_local, 'playwright', None) is None:
        if not os.environ.get('PLAYWRIGHT_BROWSERS_PATH') and os.path.isdir(OFFLINE_BROWSERS):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = OFFLINE_BROWSERS
        _local.playwright = sync_playwright().start()
        if threading.current_thread() is threading.main_thread():
            atexit.register(close_this_thread)
    return _local.playwright


def _launch(headless):
    channel = ReadConfig.getBrowserChannel()
    try:
        return _get_playwright().chromium.launch(headless=headless, channel=channel)
    except PlaywrightError as no_chromium:
        if channel:
            raise
        # Playwright has no Chromium here: use the Chrome installed on the machine
        try:
            return _get_playwright().chromium.launch(headless=headless, channel='chrome')
        except PlaywrightError:
            raise no_chromium


def _get_browser(headless):
    if getattr(_local, 'browser', None) is not None and _local.headless != headless:
        close_this_thread()
    if getattr(_local, 'browser', None) is None:
        _local.browser = _launch(headless)
        _local.headless = headless
    return _local.browser


def find_device(name):
    """Playwright device name, ignoring case ('iphone 13' -> 'iPhone 13'). ValueError with suggestions."""
    by_lower = {device.lower(): device for device in _get_playwright().devices}
    wanted = name.strip().lower()
    if wanted in by_lower:
        return by_lower[wanted]
    close = [by_lower[n] for n in difflib.get_close_matches(wanted, by_lower, n=5, cutoff=0.6)]
    hint = f" Did you mean: {', '.join(close)}?" if close else ''
    raise ValueError(f"Unknown device '{name}'.{hint} Any Playwright device name works, e.g. 'iPhone 13', 'Pixel 7'.")


def close_this_thread():
    """Close the browser and stop Playwright of the current thread (nothing if it has none)."""
    if getattr(_local, 'browser', None) is not None:
        _local.browser.close()
        _local.browser = None
    if getattr(_local, 'playwright', None) is not None:
        _local.playwright.stop()
        _local.playwright = None


class PlaywrightEngine(Engine):
    name = 'playwright'

    def __init__(self, headless=True, device=None):
        browser = _get_browser(headless)
        options = {'viewport': DESKTOP_VIEWPORT}
        if device:
            options = dict(_get_playwright().devices[find_device(device)])
            options.pop('default_browser_type', None)  # always the local Chromium (see the top of this file)
        self.device = device
        self.phone_layout = bool(device) and options['viewport']['width'] <= PHONE_MAX_WIDTH
        self._context = browser.new_context(**options)
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

    def is_visible(self, xpath):
        return self._first(xpath).is_visible()

    # ---- page state ----
    def evaluate(self, expression):
        return self.page.evaluate(expression)

    def no_alert_is_present(self):
        return not self._dialog_seen

    def quit(self):
        self._context.close()
