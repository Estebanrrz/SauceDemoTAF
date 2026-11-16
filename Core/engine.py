# Browser engine contract.
#
# Page objects and tests only know this class. Selenium and Playwright are two implementations
# of it, so every page is written once. Locators are XPath strings, which both engines support.

import time
from abc import ABC, abstractmethod

from Utilities.readProperties import ReadConfig
from Utilities.steps import step, step_scope

# Console labels for the engine calls that tests make directly. They are applied here, once,
# to every implementation (see __init_subclass__), so both engines print the same steps.
STEP_LABELS = {
    'goto': 'open the page {url}',
    'reload': 'reload the page',
    'open_new_tab': 'open {url} in a new browser tab',
    'evaluate': 'run a check in the page: {expression}',
    'no_alert_is_present': 'check that no pop-up alert appeared',
}


class Engine(ABC):
    name = 'abstract'
    device = None          # Playwright device emulated (--device), None on desktop
    phone_layout = False   # True when the emulated screen is narrow enough for the phone layout

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for method, label in STEP_LABELS.items():
            if method in cls.__dict__:
                setattr(cls, method, step(label)(cls.__dict__[method]))

    # ---- navigation ----
    @abstractmethod
    def goto(self, url):
        """Open a URL in the current tab."""

    @abstractmethod
    def reload(self):
        """Reload the current page."""

    @property
    @abstractmethod
    def current_url(self):
        """URL of the current tab."""

    @abstractmethod
    def open_new_tab(self, url):
        """Open a URL in a new tab of the same session and switch to it."""

    # ---- actions (wait until the element can be used) ----
    @abstractmethod
    def click(self, xpath):
        """Click the first match once it is visible and enabled."""

    @abstractmethod
    def fill(self, xpath, text):
        """Clear the first matching input and type the text."""

    @abstractmethod
    def select_by_label(self, xpath, label):
        """Choose an option of a <select> by its visible text."""

    # ---- reading ----
    @abstractmethod
    def text(self, xpath):
        """Text of the first match (waits for it to exist)."""

    @abstractmethod
    def texts(self, xpath):
        """Texts of all current matches. No wait, may be empty."""

    @abstractmethod
    def value(self, xpath):
        """Value of the first matching input (waits for it to exist)."""

    @abstractmethod
    def attribute(self, xpath, name):
        """Attribute of the first match (waits for it to exist)."""

    @abstractmethod
    def count(self, xpath):
        """How many elements match right now. No wait."""

    @abstractmethod
    def wait_for(self, xpath):
        """Wait until at least one element matches."""

    @abstractmethod
    def is_visible(self, xpath):
        """True if the first match exists and is visible right now. No wait."""

    # ---- page state ----
    @abstractmethod
    def evaluate(self, expression):
        """Run a JavaScript expression in the page and return its value."""

    @abstractmethod
    def no_alert_is_present(self):
        """True if no JavaScript alert or dialog showed up."""

    @abstractmethod
    def quit(self):
        """Close the browser session."""

    # ---- shared ----
    def wait_until(self, predicate, message, timeout=None, label='wait until the page shows the expected result'):
        """Poll until predicate is true or the explicit wait runs out. Prints one step (label);
        steps used inside the predicate stay quiet."""
        timeout = timeout or ReadConfig.getExplicitWait()
        deadline = time.monotonic() + timeout
        with step_scope(label):
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(0.1)
        raise AssertionError(message)
