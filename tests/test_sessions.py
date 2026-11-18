# Two users logged in at the same time, in two browser sessions, never see each other's cart
#
# Each user runs in its own thread with its own browser session, and both shop AT THE SAME TIME: a
# barrier makes them start together, and the test checks afterwards that their shopping really overlapped.
# Playwright only (skipped on Selenium).
# Both carts hold the Backpack on purpose: the same product in two carts must not mix them up.
# The steps of each user start with its name: "Step: [problem_user] add Sauce Labs Onesie to the cart".
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from Core.factory import create_engine, finish_thread
from PageObjects.InventoryPage import InventoryPage
from PageObjects.LoginPage import LoginPage
from PageObjects.ShoppingCartPage import ShoppingCartPage
from Utilities.readProperties import ReadConfig
from Utilities.steps import step_prefix
from Utilities.testData import TestData

SHOPPERS = {
    'standard_user': ['Sauce Labs Backpack', 'Sauce Labs Bike Light'],
    'problem_user': ['Sauce Labs Backpack', 'Sauce Labs Onesie'],
}
ROUNDS = 3           # add, check, remove, check: this many times per user
BARRIER_SECONDS = 120  # generous: starting a browser can be slow on a busy machine


def shop(username, products, engine_name, device, base_url, barrier):
    """One user in one browser session (runs in its own thread). Returns when its shopping started and ended."""
    with step_prefix(username):
        engine = create_engine(engine_name, headless=ReadConfig.isHeadless(), device=device)
        try:
            pages = SimpleNamespace(login=LoginPage(engine), inventory=InventoryPage(engine),
                                    cart=ShoppingCartPage(engine))
            engine.goto(base_url)
            pages.login.Login(username, TestData.password(username))
            barrier.wait()  # both users are logged in: go
            started = time.monotonic()
            for round_number in range(1, ROUNDS + 1):
                for product in products:
                    pages.inventory.AddtoCartItem(product)
                pages.inventory.ClickShoppingCartButton()
                actual = pages.cart.GetItemNames()
                assert actual == products, f'{username}, round {round_number}: expected {products}, got {actual}'
                for product in products:
                    pages.cart.RemoveItem(product)
                actual = pages.cart.GetItemNames()
                assert actual == [], f'{username}, round {round_number}: the cart should be empty, got {actual}'
                pages.cart.ClickContinueShopping()

            # End: both carts full at the same time, each user sees only its own products
            for product in products:
                pages.inventory.AddtoCartItem(product)
            barrier.wait()
            pages.inventory.ClickShoppingCartButton()
            actual = pages.cart.GetItemNames()
            assert actual == products, f'{username}, both carts full: expected {products}, got {actual}'
            assert pages.inventory.GetCounterShoppincart() == str(len(products))
            return started, time.monotonic()
        except BaseException:
            barrier.abort()  # the other user stops waiting at once instead of after the timeout
            raise
        finally:
            engine.quit()
            finish_thread(engine_name)


class TestSessions:
    def test_two_users_at_the_same_time_never_see_each_other_cart(self, base_url, engine_name, device):
        """Two users in two browser sessions at the same time: neither one ever sees the other one's cart"""
        if engine_name != 'playwright':
            pytest.skip('Two browsers at the same time is checked with Playwright only: with Selenium the clicks of the two sessions get lost')
        barrier = threading.Barrier(len(SHOPPERS), timeout=BARRIER_SECONDS)
        with ThreadPoolExecutor(max_workers=len(SHOPPERS)) as pool:
            runs = {username: pool.submit(shop, username, products, engine_name, device, base_url, barrier)
                    for username, products in SHOPPERS.items()}
            times = {username: run.result() for username, run in runs.items()}  # re-raises a failed check
        starts, ends = [start for start, _ in times.values()], [end for _, end in times.values()]
        assert max(starts) < min(ends), f'The two sessions did not overlap in time: {times}'
