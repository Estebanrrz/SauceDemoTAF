# Readable step output.
#
# Page-object methods carry @step("add {name} to the cart"). Every call logs
# "Step: add Sauce Labs Backpack to the cart" on the 'steps' logger, and pytest.ini turns on
# live logging, so the steps show in the console and in the HTML report with no extra flags.
#
# Only the outermost step is logged: "log in as standard_user" does not also log the typing and
# the click it is made of. Passwords are never logged: an argument named "password" is replaced
# by '********' plus a hint that tells the cases apart (correct, wrong, only spaces, empty).

import functools
import inspect
import logging
from contextlib import contextmanager

from Utilities.testData import TestData

logger = logging.getLogger('steps')
logger.setLevel(logging.INFO)

_depth = 0
MASK = "'********'"


def mask_password(password, username=None):
    """Describe a password without ever showing it."""
    if password == '':
        return "'' (empty)"
    if password.strip() == '':
        return f'{MASK} (only spaces)'
    if username is not None:
        try:
            correct = TestData.password(username)
        except KeyError:
            return MASK
        return f"{MASK} ({'the correct password' if password == correct else 'a wrong password'})"
    return MASK


@contextmanager
def step_scope(label):
    """Log the label when it is a top-level step and keep nested steps quiet."""
    global _depth
    if _depth == 0:
        logger.info('Step: %s', label)
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1


def step(template):
    """Log a label built from the call arguments, e.g. @step("log in as {username}")."""

    def decorator(func):
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            values = dict(bound.arguments)
            if 'password' in values:
                values['password'] = mask_password(values['password'], values.get('username'))
            with step_scope(template.format(**values)):
                return func(*args, **kwargs)

        return wrapper

    return decorator
