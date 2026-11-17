# Test data layer: users, products and the default customer live in Data/*.json, not in the code.
import json
import os
from functools import lru_cache

from Utilities.readProperties import ReadConfig


@lru_cache(maxsize=None)
def _load(name):
    with open(os.path.join(ReadConfig.getDataDir(), name), encoding='utf-8') as f:
        return json.load(f)


class TestData:
    __test__ = False  # not a test class, in case a collector ever scans this module

    @staticmethod
    def password(username):
        try:
            return _load('users.json')[username]['password']
        except KeyError:
            raise KeyError(f"User '{username}' is not defined in Data/users.json")

    @staticmethod
    def users():
        return list(_load('users.json'))

    @staticmethod
    def is_locked(username):
        """True for users marked "locked": true in Data/users.json (they cannot log in)."""
        return bool(_load('users.json')[username].get('locked', False))

    @staticmethod
    def active_users():
        """Users that can log in."""
        return [name for name in TestData.users() if not TestData.is_locked(name)]

    @staticmethod
    def locked_users():
        return [name for name in TestData.users() if TestData.is_locked(name)]

    @staticmethod
    def products():
        """Catalog as {name: price}, in the order of Data/products.json."""
        return {p['name']: p['price'] for p in _load('products.json')}

    @staticmethod
    def productNames():
        return list(TestData.products())

    @staticmethod
    def customer():
        return _load('customer.json')
