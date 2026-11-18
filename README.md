# SauceDemoTAF

UI and API test automation framework for [saucedemo.com](https://www.saucedemo.com/). The UI tests use
the Page Object pattern. The tests run with **pytest** and can use two browser engines, **Playwright**
(default) and **Selenium**, chosen with one option. They run against a local copy of the site, so no
internet is needed. With Playwright they can also run as a phone or tablet (`--device="iPhone 13"`),
see "Mobile". The local copy also has a **JSON API** backed by an **SQLite** database, tested by the
API tests in `tests_api/` (no browser), see "API".

**46 UI tests**: the 31 scenarios the project already had, 6 new ones (9 test cases, because the
sorting scenario runs once per sort option), `tests/test_sessions.py` (two users in two browser sessions
at the same time, see "API") and `tests/test_accessibility.py` (5 tests that drive the pages only with
Playwright's accessibility locators, see "Accessibility"). On top of them, `tests/test_mobile.py` checks
the phone and desktop layouts on every supported device (see "Mobile"): 61 UI tests in all.

**113 API tests** in `tests_api/`: health, login, logout, token security and expiry, catalog, cart, two
carts at the same time, orders with the payment mock, and database checks (see "API").

## Requirements

- Python 3.11 or newer
- Chrome or Chromium (see "Browsers" below)

## Setup

```bash
source setup.sh                 # creates .venv if it is missing, activates it, installs requirements.txt
```

`./run_tests.sh` runs `setup.sh` by itself, so for the pipeline there is nothing to install by hand.
Without bash (Windows PowerShell / cmd), do the same by hand:

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux / macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
pytest                          # all tests (UI on Playwright, headless, and API)
pytest tests                    # only the UI tests
pytest tests_api                # only the API tests (no browser, a few seconds)
pytest --engine=selenium        # same tests on Selenium
pytest --device="iPhone 13"     # same tests on Playwright, emulating an iPhone 13
pytest --device="iPhone 13, Pixel 7"   # the whole suite once per device, one report each
pytest --device="iPhone 13, Pixel 7" --parallel   # the same, all devices at the same time
pytest tests/test_login.py      # one file
pytest -k oos14                 # one scenario by its ID (OOS-14)
HEADLESS=0 pytest               # watch the browser
./run_tests.sh                  # local pipeline: setup.sh, API, both engines, every device, one report each
./run_tests.sh api              # only the API tests, after setup.sh
```

**One command for everything: `./run_tests.sh`** (Windows: run it in Git Bash). It prepares `.venv`,
runs the API tests, the UI tests on Playwright and on Selenium, and the UI tests on the 4 devices, and
ends with one table (exit code 0 only if everything passed):

```
=============================================================================
SUMMARY (total time 12.3 min)
=============================================================================
Category                  Passed  Failed  Skipped  Errors     Time  Report
-----------------------------------------------------------------------------
API tests                    113       0        0       0    33.2s  reports/report-api.html
UI Playwright, desktop        61       0        0       0    45.1s  reports/report.html
...
TOTAL                        442       0       13       0
(+ 24 not repeated on the later devices: they already ran with the first one)
RESULT: ALL PASSED
```

The same table ends every mode (`./run_tests.sh api`, `selenium`, `mobile`...), and options after the
first word go to pytest (`./run_tests.sh api -k expiry`). Each pytest run saves its counts next to its
HTML report (`reports/summary*.json`); `python -m Utilities.run_summary` prints the table again.

Nothing has to be running before: the tests start the local app by themselves. To open it yourself:

```bash
python app/server.py            # http://127.0.0.1:5055/
```

The reports are written to `reports/` (ignored by git), one file per engine and device, so runs do
not overwrite each other: `report-api.html` (`pytest tests_api`), `report.html` (Playwright, desktop), `report-selenium.html`,
`report-iphone-13.html` (`--device="iPhone 13"`), `report-ipad-mini.html`... `--html=file.html`
still chooses the file yourself.

## Mobile

The local app has a phone layout: under 600px wide the products stack in one column, buttons are
full width and the side menu opens with a phone menu button, `id="mobile-menu-button"` (the desktop
burger, `react-burger-menu-btn`, is hidden there). Same URLs and ids as on desktop.

`--device` runs the suite with a Playwright device profile (screen size, user agent, touch, pixel
density). No real device and no internet are needed:

```bash
pytest --device="iPhone 13"            # or any Playwright device name (case does not matter)
pytest --device="iPhone 13, Pixel 7"   # several devices, separated by commas
pytest --device="iPhone 13, Pixel 7" --parallel   # the same, all devices at the same time
./run_tests.sh mobile                  # every supported device below
./run_tests.sh mobile --parallel       # extra options after the first one go to pytest
./run_tests.sh "iPhone 13, Pixel 7"    # same as the pytest line, after setup.sh
```

With several devices the suite runs once per device, one after the other, each run with its own
report (`reports/report-iphone-13.html`, `reports/report-pixel-7.html`), and a summary at the end
(a failed device shows `TESTS_FAILED` instead of `OK`):

```
=== Devices: 2 runs one after the other, 166.2s in total
  iPhone 13              OK                     96.9s  reports/report-iphone-13.html
  Pixel 7                OK                     68.9s  reports/report-pixel-7.html
```

All the names are checked first: if any device is wrong, nothing runs and the message lists every
wrong name with suggestions. The exit code is 0 only if every device run passed. `--html` cannot be
combined with several devices (each device already has its own report).

**`--parallel`** starts every device run at the same time, one browser each. The local app is
started once for all of them. To keep the console readable, the output of each device is printed
in one block when that device finishes, and the summary shows each device's time and the total.
With 2 devices on a 4-core machine the median went from 158.5s to 76.9s, about 2x faster (4
alternating rounds; the machine was noisy, 1.4x to 3.5x per round). More devices than CPU cores
will not go faster. `--parallel` does nothing with one device, and Ctrl+C stops every run.

Supported devices, and the layout each one must get:

| Device | Width | Layout |
|---|---|---|
| iPhone 13 | 390px | phone |
| Pixel 7 | 412px | phone |
| iPhone 13 landscape | 750px | desktop |
| iPad Mini | 768px | desktop |

- **Chromium only.** Profiles always run on the local Chromium. The iPhone profiles ask for WebKit,
  which is not installed and needs internet to download, so an "iPhone 13" run is Chromium with the
  iPhone screen and user agent, not real Safari.
- **Playwright only.** `--device` with `--engine=selenium` stops with an error. An unknown name also
  stops the run, with suggestions.
- **Phone layout = 600px or narrower.** Portrait phones get it (iPhone SE 320 to iPhone 13 Pro Max
  428, Pixel 7 412). Landscape phones and tablets (iPhone 13 landscape 750, iPad Mini 768) get the
  desktop layout. The tests use the same limit (`PHONE_MAX_WIDTH` in `Core/playwright_engine.py`) to
  choose the menu button, so a broken phone layout fails instead of silently using the desktop one.
- **Tests** (`tests/test_mobile.py`, marker `mobile`). They need the local app: the real saucedemo
  has no `mobile-menu-button`.
  - `TestThisRun`: on the device of the run (desktop or `--device`), only the right menu button is
    shown and no page scrolls sideways. With `--device` the rest of the suite runs on it too.
  - `TestEachDevice`: one test per supported device in every Playwright run, no `--device` needed:
    it gets the layout in the table, its menu button opens and closes the menu, and no page of a
    full purchase scrolls sideways. To support another device, add it to `DEVICE_LAYOUTS` there
    and to `DEVICES` in `run_tests.sh`. Skipped on Selenium (no device emulation). They have the
    marker `all_devices`: with several devices they run only with the first one and are deselected
    in the other runs, so no test is repeated. One device: 61 UI tests. Two devices (with or without
    `--parallel`): 61 + 53 = 114 UI tests. The API tests (when included) also run only with the first device.

## The local app

`app/server.py` is a small Flask app that copies what the tests need from saucedemo: same URLs,
ids, `data-test` attributes, error messages, validation order and the 8% tax. Users and products
come from `Data/*.json`, the same files the tests read.

- **Port:** 5055, base URL `http://127.0.0.1:5055/` (change the port with `APP_PORT`)
- **Command:** `python app/server.py`
- **API:** `http://127.0.0.1:5055/api/v1/` (see "API")
- **Database:** SQLite, `app/shop.db` when you start the app yourself (git-ignored, `SHOP_DB` chooses
  another file). When the test suite starts the app, it gets a new temporary database for that run,
  deleted at the end, so every run starts from the same data.

To run the tests against another site, set `SAUCEDEMO_URL`, for example the real one.
Some tests depend on the way the local app works, so a different site may make a few fail.

## Browsers

- **Playwright** uses its own Chromium. If your machine has none, run `playwright install chromium`
  once (needs internet), or use the Chrome you already have: `PLAYWRIGHT_CHANNEL=chrome pytest`
  (PowerShell: `$env:PLAYWRIGHT_CHANNEL = "chrome"`). Browsers already downloaded for Playwright
  are found through `PLAYWRIGHT_BROWSERS_PATH` (for example `/opt/pw-browsers`), so nothing is
  downloaded.
- **Selenium** looks for the browser in `CHROME_BIN`, then in the Chromium bundled with Playwright,
  then the Chrome installed on the machine. The driver is chosen in this order:
  1. `CHROMEDRIVER` (path to a chromedriver binary)
  2. `chromedriver-py`, only with the Playwright Chromium (that is the version it matches)
  3. Selenium Manager (needs internet)
  4. `Drivers/chromedriver.exe`, if you put one there. The repo does not include any binary: if
     there is no internet, download the driver that matches your Chrome from
     <https://googlechromelabs.github.io/chrome-for-testing/> and either save it in `Drivers/`
     (ignored by git) or point `CHROMEDRIVER` to it.

## Settings

Resolved as: **environment variable > `Configuration/config.ini` > default**.

| Setting | config.ini | Environment variable | Default |
|---|---|---|---|
| Base URL | `baseUrl` | `SAUCEDEMO_URL` | http://127.0.0.1:5055/ |
| Headless | `headless` | `HEADLESS` | true |
| Engine | `engine` | `ENGINE` | playwright |
| Playwright browser channel | `browserChannel` | `PLAYWRIGHT_CHANNEL` | (own Chromium) |
| Devices to emulate (Playwright), comma separated | `device` | `DEVICE` (or `--device`) | (desktop 1280x900) |
| Explicit wait (s) | `explicitWait` | `EXPLICIT_WAIT` | 10 |
| App port | | `APP_PORT` | 5055 |
| App database file | | `SHOP_DB` | `app/shop.db`; a temporary file when the tests start the app |
| API token lifetime (s) | | `TOKEN_TTL_SECONDS` | 300 (5 minutes) |
| Payment service | | `PAYMENT_URL` | http://127.0.0.1:5056/ (the mock; it only auto-starts for a local URL) |
| Payment wait (s) | | `PAYMENT_TIMEOUT` | 3 |
| Payment mock port | | `PAYMENT_PORT` | 5056 |

## API

The local app has a JSON API under `/api/v1/`. The data lives in an SQLite database (`app/db.py`,
plain SQL, no ORM) that is created and filled from `Data/users.json` and `Data/products.json` every
time the app starts. Prices are stored as whole cents; passwords and tokens only as hashes. Open the
file with any SQLite viewer (for example DB Browser for SQLite) to look inside.

**The web pages use the API too, over HTTP** (`app/shop_api.py`), like any other client: the login page
calls `auth/login` and keeps the token in the session cookie, the products page reads `products`, the
cart button, cart page and checkout use `cart/items`, and logout calls `auth/logout`. The pages keep no
shop data of their own, so a bug in the API shows up in the UI tests too.

| Endpoint | Token | What it does |
|---|---|---|
| `GET /api/v1/health` | no | `{"status": "ok", "database": "ok"}` |
| `POST /api/v1/auth/login` | no | `{"username", "password"}` -> `{"token", "token_type": "Bearer", "username"}` |
| `POST /api/v1/auth/logout` | yes | The token stops working (204), and its cart is deleted |
| `GET /api/v1/products?sort=az` | yes | The catalog. `sort`: `az` (default), `za`, `lohi`, `hilo` |
| `GET /api/v1/products/{id}` | yes | One product |
| `GET /api/v1/cart/items` | yes | `{"items": [product, ...]}` in the order they were added |
| `POST /api/v1/cart/items` | yes | `{"product_id": 1}` adds it (201); already there: 409 (quantity is always 1) |
| `DELETE /api/v1/cart/items/{id}` | yes | Removes that product; not in the cart: 404 |
| `DELETE /api/v1/cart/items` | yes | Empties the cart |
| `POST /api/v1/orders` | yes | Pays the whole cart: `{"first_name", "last_name", "postal_code", "card"}` |
| `GET /api/v1/orders/{id}` | yes | One order of the logged-in user (someone else's order: 404) |

- **Token:** send it as `Authorization: Bearer <token>`. Every login gives a new token.
- **Tokens expire** `TOKEN_TTL_SECONDS` after the login (default 300 = 5 minutes; the login answer says
  it in `expires_in`). Then every call with it gets `401 token_expired`, "The token has expired, please
  log in again" (a token that never existed or was logged out gets `invalid_token` instead). The web
  pages then go back to the login page. A wrong value (`abc`, `0`) stops the app at start with a clear
  message. Database files from before expiry existed are upgraded at start; their old tokens count as
  expired.
- **One cart per login** (per token), like one cart per browser session: two users, or the same user
  logged in twice, never share a cart. Every cart call answers with the whole cart.
- **Orders belong to the user** (unlike carts): a later login of the same user still reads them. The
  order copies name and price of every item, so catalog changes never alter old orders. The cart is
  emptied only when the payment worked.
- **Errors** always have the same shape: `{"error": {"code": "invalid_token", "message": "..."}}`, with
  400 (bad input), 401 (no or bad token, wrong password), 402 (payment declined), 403 (locked user),
  404, 405, 409, 502 (payment service down).
- **Login rules** are the login page's: same checks, same order, same "Epic sadface" messages. An
  unknown user gets the same answer as a wrong password.

Try it by hand (or import the same calls into Postman):

```bash
python app/server.py
curl -s -X POST http://127.0.0.1:5055/api/v1/auth/login -H 'Content-Type: application/json' \
     -d '{"username": "standard_user", "password": "secret_sauce"}'
curl -s http://127.0.0.1:5055/api/v1/products?sort=lohi -H 'Authorization: Bearer <token>'
```

### The payment mock (`mocks/payment_mock.py`)

The shop never talks to a real card company. `POST /api/v1/orders` charges the card at `PAYMENT_URL`
(default `http://127.0.0.1:5056/`), and in this repo that is a small mock which answers by "magic
cards", like the test cards of real payment providers, so it needs no set-up calls and parallel runs
cannot disturb each other:

| Card | The mock answers | The shop answers |
|---|---|---|
| any other card (e.g. `SauceCard #31337`, the one the checkout page uses) | 201 approved | 201, order saved, cart emptied |
| `SauceCard #DECLINED` | 402 declined | 402 `payment_declined`, nothing changes |
| `SauceCard #ERROR` | 500 | 502 `payment_unavailable`, nothing changes |
| `SauceCard #SLOW` | waits longer than the shop does (`PAYMENT_TIMEOUT`, 3 s) | 502 `payment_unavailable`, nothing changes |

It starts by itself with the app (also with `python app/server.py`), or alone with
`python mocks/payment_mock.py`. For the tests it records every charge it receives:
`GET /__requests?reference=order-abc` answers what the shop sent (card, amount in cents, reference),
so a test can check the exact amount that was charged. The checkout page always pays with the fixed
approved card; decline and error are reached through the API (`tests_api/test_orders.py`).

### API tests (`tests_api/`)

They use **requests** over real HTTP, no browser, and print one step per call like the UI tests
(`Step: POST /api/v1/auth/login`, passwords never shown). They get the marker `api`
(`pytest -m api`, `-m "not api"`) and run in a few seconds.

```
tests_api/
  clients/api_client.py   ApiClient: base URL, Bearer token, step output, timeout; returns the raw response
  checks.py               json_of, check_error, check_contract and the contracts (fields and types of each answer)
  conftest.py             Fixtures: api, token_for(username), user_api, ids, shop_db
  test_health.py          Health and the error shape
  test_auth.py            Login, login errors, token security, logout
  test_token_expiry.py    Token lifetime: expires_in, expired token on every endpoint, wrong settings
  separate_app.py         Starts a separate copy of the app with its own settings (e.g. TOKEN_TTL_SECONDS=2)
  test_products.py        Catalog, sorting, one product, errors
  test_cart.py            Cart: add, remove, empty, errors, the cart of another user
  test_cart_concurrency.py  Two logins change their carts at the same time (threads)
  test_orders.py          Orders: totals, what the payment service was charged, declined card,
                          broken and hanging payment service, validation, who sees an order
  test_payment_mock.py    The magic cards of the mock answer what the orders tests rely on
  test_database.py        What the API leaves in the SQLite file (read-only)
```

Fixtures: `api` (no token), `token_for('problem_user')` (a new token), `user_api` (logged in as
standard_user), `ids` (`{product name: id}` from the API), `shop_db` (read-only connection to the app's
database; skipped when the app was started outside the test run, unless `SHOP_DB` points both to the
same file).

**Two users at the same time.** `tests_api/test_cart_concurrency.py` (API, about 160 cart calls at the
same time) and `tests/test_sessions.py` (UI, two browser sessions) run each user in its own thread:
a barrier makes them start together, every check is done while the other user is changing its cart,
and the test fails if the two did not really overlap in time. The UI test runs with Playwright only
(skipped on Selenium: with two browsers at the same time some clicks get lost). Each user's steps start with its name:
`Step: [problem_user] add Sauce Labs Onesie to the cart`. To drive browsers from your own threads,
create the engine inside the thread and call `finish_thread(engine_name)` (`Core/factory.py`) at its end.

Adding an API test:

1. Use the fixtures: `api` to call without a token, `user_api` for a logged-in user, `token_for('problem_user')`
   for another user.
2. Check the answer with `json_of(response, 200)` (status + JSON) or `check_error(response, 401, 'invalid_token')`,
   and the fields with `check_contract(body, PRODUCT)`.
3. Take the expected data from `Data/*.json` (`TestData`), not from the app code: the tests treat the app as a
   black box.

## Accessibility

Every control has an accessible name: `aria-label` on the inputs and icon buttons (username, password,
the checkout fields, the cart link, `Add <product> to cart` / `Remove <product> from cart`), the text of
normal buttons and links, and `role="heading"` on the page titles. `tests/test_accessibility.py` drives
a full purchase, the menu and the sort box using only Playwright's accessibility locators
(`get_by_role`, `get_by_label`) on the raw page (`engine.page`), which also proves those names exist.
Playwright only: on Selenium these 5 tests are skipped.

## Step output

Every test prints what it does, in plain English, with no flags:

```
Step: log in as standard_user with password '********' (the correct password)
Step: add Sauce Labs Backpack to the cart
Step: open the shopping cart
```

Page object methods carry a `@step("...")` label (`Utilities/steps.py`) and `pytest.ini` turns on
live logging. Passwords are never printed: they show as `'********'` plus a hint (the correct
password, a wrong password, only spaces, empty).

## Project layout

```
app/                       Local copy of saucedemo (Flask): server.py (pages), shop_api.py (the pages' API
                           client), api.py (JSON API), db.py (SQLite), messages.py (texts shared by both)
Configuration/config.ini   Settings
Core/                      Engine interface, Selenium and Playwright implementations, factory
Data/                      Test data: users.json, products.json, customer.json
Drivers/                   Optional, git-ignored: your own chromedriver (see "Browsers")
PageObjects/               One class per page, plus MenuComponent (shared by all pages)
Utilities/                 Config reader, test data reader, step logging
mocks/                     Mock of the external payment service (see "The payment mock")
tests/                     The UI tests, one file per area, and the fixtures (tests/conftest.py)
tests_api/                 The API tests (see "API")
conftest.py                Registers --engine and --device; base_url fixture shared by tests/ and tests_api/
pytest.ini                 Test path, HTML report options and live logging
run_tests.sh               Local pipeline (runs setup.sh first)
setup.sh                   Creates .venv if missing, activates it, installs requirements.txt
```

The tests and page objects are written once. They only use the `Engine` interface in
`Core/engine.py`, and `--engine` decides if Selenium or Playwright implements it.

## Tests

Scenario IDs from the coverage-gap list are in the test names (`test_oos14_...`), so `-k oos14` runs
one of them. Tests that document a rule the site has today but that still needs a product decision
say so in their docstring (OOS-03, OOS-04).

The 6 new scenarios:

1. Login with a wrong password
2. Login with a locked out user
3. Login with an empty password
4. Sorting by each of the four options and checking the order
5. Removing a product from the cart page
6. Complete order: summary (items, subtotal, tax, total), confirmation, and an empty cart afterwards

## Adding UI tests

1. Put new data (users, products, customer) in `Data/*.json`, not in the tests.
2. Add locators and actions to the page class in `PageObjects/`, using only `Engine` methods so the
   page works on both engines.
3. Write the test in `tests/` and reuse the fixtures (`logged_in`, `login_as`, `go_to_page`, `pages`).
