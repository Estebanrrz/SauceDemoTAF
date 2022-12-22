# Utilities Page to set/get config from a file

import configparser
import os
from pathlib import Path

path = Path(__file__)
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
config_path = os.path.join(ROOT_DIR, 'Configuration\\config.ini')
config = configparser.RawConfigParser()
config.read(config_path)


class ReadConfig:
    @staticmethod
    def getApplicationUrl():
        url = config.get('settings', 'baseUrl')
        return url
