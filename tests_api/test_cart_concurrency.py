# Two logins use their carts at the same time and never see each other's products
#
# Each login runs in its own thread and both start together (a barrier). Every cart call answers with the
# whole cart, and after each call the answer must hold exactly what that login put in, in its order.
# Both carts use the Backpack on purpose: the same product in two carts must not mix them up. At the end
# the test checks that the two threads really overlapped in time.
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests_api.clients.api_client import describe
from Utilities.steps import step_prefix, step_scope
from Utilities.testData import TestData

PRODUCTS = {
    'first': ['Sauce Labs Backpack', 'Sauce Labs Bike Light', 'Sauce Labs Onesie'],
    'second': ['Sauce Labs Backpack', 'Sauce Labs Fleece Jacket', 'Sauce Labs Bolt T-Shirt'],
}
ROUNDS = 20
BARRIER_SECONDS = 30


def shop(name, client, products, ids, barrier):
    """One login (runs in its own thread): add and remove its products ROUNDS times, checking the cart
    in every answer. Returns when it started and ended."""
    with step_prefix(name), step_scope(f'add and remove {len(products)} products {ROUNDS} times, '
                                       f'checking the cart after every call'):
        try:
            barrier.wait()
            started = time.monotonic()
            for round_number in range(1, ROUNDS + 1):
                expected = []
                for product in products:
                    response = client.post('cart/items', json={'product_id': ids[product]})
                    expected.append(product)
                    check_cart(response, 201, expected, f'{name}, round {round_number}, after adding {product}')
                for product in products:
                    response = client.delete(f'cart/items/{ids[product]}')
                    expected.remove(product)
                    check_cart(response, 200, expected, f'{name}, round {round_number}, after removing {product}')
            for product in products:  # end with a full cart
                client.post('cart/items', json={'product_id': ids[product]})
            barrier.wait()  # both carts are full now
            check_cart(client.get('cart/items'), 200, products, f'{name}, both carts full')
            return started, time.monotonic()
        except BaseException:
            barrier.abort()  # the other thread stops waiting at once
            raise


def check_cart(response, status, expected, when):
    assert response.status_code == status, f'{when}: {describe(response)}'
    actual = [item['name'] for item in response.json()['items']]
    assert actual == expected, f'{when}: expected {expected}, got {actual}'


class TestCartsAtTheSameTime:
    @pytest.mark.parametrize('first_user, second_user', [
        pytest.param('standard_user', 'problem_user', id='two-users'),
        pytest.param('standard_user', 'standard_user', id='same-user-two-logins'),
    ])
    def test_two_logins_at_the_same_time_never_see_each_other_cart(self, api, ids, first_user, second_user):
        """Two logins change their carts at the same time; every answer shows only that login's own products"""
        clients = {
            'first': api.with_token(api.token_for(first_user, TestData.password(first_user))),
            'second': api.with_token(api.token_for(second_user, TestData.password(second_user))),
        }
        labels = {'first': first_user, 'second': second_user}
        if first_user == second_user:
            labels = {key: f'{user} #{number}' for number, (key, user) in enumerate(labels.items(), 1)}
        barrier = threading.Barrier(len(clients), timeout=BARRIER_SECONDS)
        with ThreadPoolExecutor(max_workers=len(clients)) as pool:
            runs = {key: pool.submit(shop, labels[key], clients[key], PRODUCTS[key], ids, barrier) for key in clients}
            times = {labels[key]: run.result() for key, run in runs.items()}  # re-raises a failed check
        starts, ends = [start for start, _ in times.values()], [end for _, end in times.values()]
        assert max(starts) < min(ends), f'The two logins did not overlap in time: {times}'
