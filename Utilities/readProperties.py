# Utilities Page to set/get config from a file
#
# Precedence for every setting: environment variable > Configuration/config.ini > default.

import configparser
import os

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
config_path = os.path.join(ROOT_DIR, 'Configuration', 'config.ini')
config = configparser.RawConfigParser()
config.read(config_path)


def _get(section, key, env=None, default=None):
    if env and os.environ.get(env):
        return os.environ[env]
    return config.get(section, key, fallback=default)


class ReadConfig:
    @staticmethod
    def getApplicationUrl():
        """Always ends with '/' (SAUCEDEMO_URL overrides config.ini, e.g. to target a replica)."""
        url = _get('settings', 'baseUrl', 'SAUCEDEMO_URL', 'http://127.0.0.1:5055/')
        return url if url.endswith('/') else url + '/'

    @staticmethod
    def isHeadless():
        return _get('settings', 'headless', 'HEADLESS', 'true').lower() in ('1', 'true', 'yes')

    @staticmethod
    def getDefaultEngine():
        return _get('settings', 'engine', 'ENGINE', 'playwright')

    @staticmethod
    def getBrowserChannel():
        """Installed browser for Playwright (e.g. 'chrome'). Empty means Playwright's own Chromium."""
        return _get('settings', 'browserChannel', 'PLAYWRIGHT_CHANNEL', '') or None

    @staticmethod
    def getExplicitWait():
        return int(_get('settings', 'explicitWait', 'EXPLICIT_WAIT', '10'))

    @staticmethod
    def getPageLoadTimeout():
        return int(_get('settings', 'pageLoadTimeout', None, '30'))

    @staticmethod
    def getDataDir():
        return os.path.join(ROOT_DIR, _get('paths', 'data', None, 'Data'))

    @staticmethod
    def getLocalDriverPath():
        """Fallback chromedriver kept in the repo (see README) for when Selenium Manager cannot download one."""
        return os.path.join(ROOT_DIR, 'Drivers', 'chromedriver.exe')
