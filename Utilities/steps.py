# Readable step output.
#
# Page-object methods carry @step("add {name} to the cart"). Every call logs
# "Step: add Sauce Labs Backpack to the cart" on the 'steps' logger, and pytest.ini turns on
# live logging, so the steps show in the console and in the HTML report with no extra flags.
#
# Only the outermost step is logged: "log in as standard_user" does not also log the typing and
# the click it is made of. Passwords are never logged: an argument named "password" is replaced
# by '********' plus a hint that tells the cases apart (correct, wrong, only spaces, empty).
#
# Thread safe: every thread keeps its own nesting, and step_prefix('standard_user') marks the steps of a
# thread ("Step: [standard_user] add ...") so tests that run two users at the same time stay readable.

import functools
import inspect
import logging
import threading
from contextlib import contextmanager

from Utilities.testData import TestData

logger = logging.getLogger('steps')
logger.setLevel(logging.INFO)

_local = threading.local()  # per thread: depth (nesting of steps) and prefix
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
    depth = getattr(_local, 'depth', 0)
    if depth == 0:
        prefix = getattr(_local, 'prefix', None)
        logger.info('Step: %s%s', f'[{prefix}] ' if prefix else '', label)
    _local.depth = depth + 1
    try:
        yield
    finally:
        _local.depth = depth


@contextmanager
def step_prefix(prefix):
    """Start the steps of this thread with [prefix], e.g. the user a thread acts as."""
    previous = getattr(_local, 'prefix', None)
    _local.prefix = prefix
    try:
        yield
    finally:
        _local.prefix = previous


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
