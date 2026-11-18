# Scenarios of the performance tests, run by Locust against the real JSON API of the local app (/api/v1).
# Do not start it by hand: ./perf/run.sh <profile> starts the app, runs this file and stops the app.
#
# Three kinds of virtual users, in the shares of perf/config.toml ([scenarios]):
#   BrowseUser  catalogue (random sort), then a few products opened
#   CartUser    catalogue, add products, read the cart, remove one, empty the cart
#   BuyUser     catalogue, add products, pay the order through the payment mock, read the order back;
#               every Nth order of the run pays with the declined card (402 is the expected answer)
#
# Every user logs in once, keeps its token (login is slow on purpose, about 40 ms of password hashing),
# logs in again shortly before the token expires and logs out when it stops.
#
# A request counts as an error only when the answer is not the expected one: wrong status code, no JSON,
# wrong data (catalogue different from Data/products.json, wrong sort order, cart with the wrong products,
# wrong order total...), or no answer within [run] request_timeout. The expected 402 of the declined card is a
# success. After an error the flow stops and the user starts the next one with a new login, so it never
# continues from a cart in an unknown state.
#
# Results: every request is recorded (time, endpoint, response time, error) and written at the end, with the
# number of users over time, to the results file that perf/run.py gives in PERF_RESULTS. perf/analysis.py
# builds the console table, the HTML report and the threshold checks from that one file.

import itertools
import json
import os
import random
import sys
import time

import gevent
import locust
from locust import HttpUser, LoadTestShape, between, events, task
from locust.exception import RescheduleTask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root: "perf" package
from perf import settings  # noqa: E402 (needs the path above)

CONFIG = settings.load(os.environ.get('PERF_CONFIG'))
PROFILE_NAME = os.environ.get('PERF_PROFILE', 'smoke')
PROFILE = settings.profile(CONFIG, PROFILE_NAME)
RUN, ACCOUNTS, CHECKOUT, SCENARIOS = CONFIG['run'], CONFIG['accounts'], CONFIG['checkout'], CONFIG['scenarios']

API = '/api/v1'
SORTS = ('az', 'za', 'lohi', 'hilo')
RESULTS_FILE = os.environ.get('PERF_RESULTS')

# The catalogue the app must serve: Data/products.json, the same file the UI and API tests read
with open(os.path.join(settings.ROOT_DIR, 'Data', 'products.json'), encoding='utf-8') as _file:
    EXPECTED_PRICES = {product['name']: round(product['price'] * 100) for product in json.load(_file)}

_usernames = itertools.cycle(ACCOUNTS['usernames'])  # each new virtual user takes the next account
_order_numbers = itertools.count()  # all orders of the run (one Locust process, so no two users get the same)


def cents(price):
    return round(price * 100)


def short(text, limit=200):
    text = ' '.join((text or '').split())
    return text if len(text) <= limit else text[:limit] + '...'


class FlowFailed(Exception):
    """A request of the flow got a wrong answer (already recorded as a failure in the stats)."""


# ---- checks of the answers: each returns None when the answer is right, otherwise what is wrong ----

def check_catalogue(sort):
    def check(body):
        products = body.get('products') if isinstance(body, dict) else None
        if not isinstance(products, list):
            return 'no "products" list in the answer'
        served = {product.get('name'): cents(product.get('price', 0)) for product in products}
        if len(products) != len(EXPECTED_PRICES) or served != EXPECTED_PRICES:
            return f'catalogue differs from Data/products.json: {short(json.dumps(served))}'
        names = [product['name'] for product in products]
        prices = [product['price'] for product in products]
        in_order = {'az': names == sorted(names), 'za': names == sorted(names, reverse=True),
                    'lohi': prices == sorted(prices), 'hilo': prices == sorted(prices, reverse=True)}[sort]
        return None if in_order else f'not sorted by {sort}: {names}'
    return check


def check_product(expected):
    def check(body):
        if not isinstance(body, dict) or (body.get('id'), body.get('name'), body.get('price')) != \
                (expected['id'], expected['name'], expected['price']):
            return f'expected product {expected["id"]} {expected["name"]!r}, got {short(json.dumps(body))}'
        return None
    return check


def check_cart(expected_ids):
    def check(body):
        items = body.get('items') if isinstance(body, dict) else None
        if not isinstance(items, list):
            return 'no "items" list in the answer'
        ids = [item.get('id') for item in items]
        return None if ids == expected_ids else f'cart should hold {expected_ids}, holds {ids}'
    return check


def check_order(expected_ids, expected_total_cents, order_id=None):
    def check(body):
        if not isinstance(body, dict):
            return 'the answer is not an order'
        problems = []
        if order_id is not None and body.get('id') != order_id:
            problems.append(f'id {body.get("id")}, expected {order_id}')
        if body.get('status') != 'paid':
            problems.append(f'status {body.get("status")!r}, expected "paid"')
        ids = [item.get('id') for item in body.get('items') or []]
        if ids != expected_ids:
            problems.append(f'items {ids}, expected {expected_ids}')
        if not isinstance(body.get('total'), (int, float)) or cents(body['total']) != expected_total_cents:
            problems.append(f'total {body.get("total")}, expected {expected_total_cents / 100:.2f}')
        return '; '.join(problems) or None
    return check


def check_error_code(code):
    def check(body):
        got = (body.get('error') or {}).get('code') if isinstance(body, dict) else None
        return None if got == code else f'error code {got!r}, expected {code!r}'
    return check


# ---- the virtual users ----

class ShopUser(HttpUser):
    """Common part: login with token renewal, logout, and one checked call per API request."""
    abstract = True  # Locust runs only the three scenarios below

    def on_start(self):
        self.username = next(_usernames)
        self.token = None
        self.renew_at = 0.0

    def on_stop(self):
        if self.token:
            self.logout()

    def call(self, method, path, name, expect, check=None, body=None, auth=True):
        """Send one request, mark it success or failure, and return the JSON answer. name is the endpoint
        without the method (/products/{id}); "METHOD name" must be one of settings.ENDPOINTS.
        A wrong answer raises FlowFailed (after it is recorded)."""
        headers = {'Authorization': f'Bearer {self.token}'} if auth else {}
        problem, answer = None, None
        with self.client.request(method, API + path, name=name, json=body, headers=headers,
                                 timeout=RUN['request_timeout'], catch_response=True) as response:
            if response.status_code != expect:
                error = getattr(response, 'error', None)
                detail = f'{type(error).__name__}: {short(str(error))}' if error and not response.status_code \
                    else short(response.text)
                problem = f'expected {expect}, got {response.status_code}: {detail}'
            elif expect != 204:
                try:
                    answer = response.json()
                except ValueError:
                    problem = f'{expect} without a JSON body: {short(response.text)}'
                else:
                    problem = check(answer) if check else None
            if problem:
                response.failure(problem)
            else:
                response.success()
        if problem:
            raise FlowFailed(problem)
        return answer

    def login(self):
        started = time.monotonic()
        answer = self.call('POST', '/auth/login', '/auth/login', 200, auth=False,
                           body={'username': self.username, 'password': ACCOUNTS['password']},
                           check=lambda body: None if isinstance(body.get('token'), str) and body['token']
                           and isinstance(body.get('expires_in'), int) else 'no token / expires_in in the answer')
        self.token = answer['token']
        self.renew_at = started + answer['expires_in'] - RUN['token_renew_margin']

    def logout(self):
        try:
            self.call('POST', '/auth/logout', '/auth/logout', 204)
        except FlowFailed:
            pass  # already recorded; the token expires by itself
        finally:
            self.token = None

    def ensure_login(self):
        """Log in the first time, and again shortly before the token expires (then log the old one out)."""
        if self.token and time.monotonic() < self.renew_at:
            return
        old_token = self.token
        self.login()
        if old_token:
            new_token, self.token = self.token, old_token
            self.logout()
            self.token = new_token

    def run_flow(self, flow):
        try:
            self.ensure_login()
            flow()
        except FlowFailed:
            self.token = None  # next flow: new login, so a new empty cart
            raise RescheduleTask()

    # ---- steps shared by the scenarios ----

    def catalogue(self):
        sort = random.choice(SORTS)
        return self.call('GET', f'/products?sort={sort}', '/products', 200, check=check_catalogue(sort))['products']

    def fill_cart(self, products, how_many):
        chosen = random.sample(products, min(random.randint(*how_many), len(products)))
        added = []
        for product in chosen:
            added.append(product['id'])
            self.call('POST', '/cart/items', '/cart/items', 201, body={'product_id': product['id']},
                      check=check_cart(list(added)))
        return chosen


class BrowseUser(ShopUser):
    weight = SCENARIOS['browse']['weight']
    abstract = weight == 0
    wait_time = between(*SCENARIOS['browse']['wait'])

    @task
    def browse(self):
        self.run_flow(self.flow)

    def flow(self):
        products = self.catalogue()
        how_many = random.randint(*SCENARIOS['browse']['products_opened'])
        for product in random.sample(products, min(how_many, len(products))):
            self.call('GET', f'/products/{product["id"]}', '/products/{id}', 200, check=check_product(product))


class CartUser(ShopUser):
    weight = SCENARIOS['cart']['weight']
    abstract = weight == 0
    wait_time = between(*SCENARIOS['cart']['wait'])

    @task
    def use_cart(self):
        self.run_flow(self.flow)

    def flow(self):
        chosen = self.fill_cart(self.catalogue(), SCENARIOS['cart']['items'])
        ids = [product['id'] for product in chosen]
        self.call('GET', '/cart/items', '/cart/items', 200, check=check_cart(ids))
        removed = random.choice(ids)
        ids.remove(removed)
        self.call('DELETE', f'/cart/items/{removed}', '/cart/items/{id}', 200, check=check_cart(ids))
        self.call('DELETE', '/cart/items', '/cart/items', 200, check=check_cart([]))


class BuyUser(ShopUser):
    weight = SCENARIOS['buy']['weight']
    abstract = weight == 0
    wait_time = between(*SCENARIOS['buy']['wait'])

    @task
    def buy(self):
        self.run_flow(self.flow)

    def flow(self):
        chosen = self.fill_cart(self.catalogue(), SCENARIOS['buy']['items'])
        ids = [product['id'] for product in chosen]
        subtotal = sum(cents(product['price']) for product in chosen)
        total = subtotal + round(subtotal * CHECKOUT['tax_rate'])
        every = CHECKOUT['declined_card_every']
        declined = bool(every) and next(_order_numbers) % every == 0
        order = {name: CHECKOUT[name] for name in ('first_name', 'last_name', 'postal_code')}
        if declined:
            # Expected: 402 payment_declined, and the cart stays as it was (then the user empties it)
            self.call('POST', '/orders', '/orders (declined card)', 402, check=check_error_code('payment_declined'),
                      body={**order, 'card': CHECKOUT['declined_card']})
            self.call('GET', '/cart/items', '/cart/items', 200, check=check_cart(ids))
            self.call('DELETE', '/cart/items', '/cart/items', 200, check=check_cart([]))
            return
        placed = self.call('POST', '/orders', '/orders', 201, check=check_order(ids, total),
                           body={**order, 'card': CHECKOUT['card']})
        self.call('GET', f'/orders/{placed["id"]}', '/orders/{id}', 200, check=check_order(ids, total, placed['id']))


# ---- the load: the stages of the profile ----

class ProfileShape(LoadTestShape):
    """Users and spawn rate of the current stage of the profile; the run stops after the last stage."""
    stages = PROFILE['stages']

    def tick(self):
        elapsed, end = self.get_run_time(), 0
        for stage in self.stages:
            end += stage['duration']
            if elapsed < end:
                return stage['users'], stage['spawn_rate']
        return None


# ---- recording: every request, the users over time, and the results file ----

class Recorder:
    """Everything the analysis needs, kept in memory during the run and written once at the end."""

    def __init__(self):
        self.samples = []        # [seconds since start, "METHOD name", response time ms, error message or None]
        self.users = []          # [seconds since start, active users], once per second
        self.script_errors = []  # exceptions of the scenario code itself (a bug in the test, not in the app)
        self.started_at = self.stopped_at = None

    def elapsed(self, when=None):
        return (when if when is not None else time.time()) - self.started_at


recorder = Recorder()


@events.request.add_listener
def record_request(request_type, name, response_time, exception, start_time=None, **_kwargs):
    if recorder.started_at is None:
        return
    recorder.samples.append([round(recorder.elapsed(start_time), 3), f'{request_type} {name}',
                             round(response_time, 2), None if exception is None else str(exception)])


@events.user_error.add_listener
def record_script_error(user_instance, exception, tb, **_kwargs):
    recorder.script_errors.append(f'{type(user_instance).__name__}: {type(exception).__name__}: {exception}')


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    """Start the clock, then once per second note the users, and every [run] progress_every seconds print a
    progress line so a long run shows it is alive."""
    recorder.started_at = time.time()
    every, total = RUN['progress_every'], settings.total_duration(PROFILE)
    if environment.runner is None:
        return

    def loop():
        last_printed, printed_count = 0, 0
        while True:
            now = recorder.elapsed()
            recorder.users.append([round(now, 1), environment.runner.user_count])
            if every and now - last_printed >= every:
                last_printed = now
                count = len(recorder.samples)
                errors = sum(1 for sample in recorder.samples if sample[3] is not None)
                print(f'  [{now:5.0f}s / {total:.0f}s] users {environment.runner.user_count:3d}'
                      f' | requests {count:6d} (+{count - printed_count}) | errors {errors}', flush=True)
                printed_count = count
            gevent.sleep(1)

    environment.runner.greenlet.spawn(loop)


@events.test_stop.add_listener
def on_test_stop(**_kwargs):
    recorder.stopped_at = time.time()  # after the users stopped (and logged out)


@events.quit.add_listener
def write_results(exit_code, **_kwargs):
    """Write the results file once, when Locust quits (also after Ctrl+C: then it holds the part that ran)."""
    if not RESULTS_FILE or recorder.started_at is None:
        return
    stopped_at = recorder.stopped_at or time.time()
    results = {
        'format': 1,
        'profile': PROFILE_NAME,
        'description': PROFILE.get('description', ''),
        'stages': PROFILE['stages'],
        'config': CONFIG['path'],
        'locust_version': locust.__version__,
        'started_at': recorder.started_at,
        'duration_s': round(stopped_at - recorder.started_at, 3),
        'users': recorder.users,
        'script_errors': recorder.script_errors,
        'sample_fields': ['t_s', 'endpoint', 'response_ms', 'error'],
        'samples': recorder.samples,
    }
    temporary = RESULTS_FILE + '.part'
    with open(temporary, 'w', encoding='utf-8') as file:
        json.dump(results, file, separators=(',', ':'))
    os.replace(temporary, RESULTS_FILE)  # never a half-written results file
