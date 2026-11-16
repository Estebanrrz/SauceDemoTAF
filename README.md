# SauceDemoTAF

UI test automation framework for [saucedemo.com](https://www.saucedemo.com/), written with the Page
Object pattern. The tests run with **pytest** and can use two browser engines, **Playwright** (default)
and **Selenium**, chosen with one option. They run against a local copy of the site, so no internet
is needed.

**40 tests**: the 31 scenarios the project already had plus 6 new ones (9 test cases, because the
sorting scenario runs once per sort option). All pass on both engines.

## Requirements

- Python 3.11 or newer
- Chrome or Chromium (see "Browsers" below)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux / macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
pytest                          # all tests, Playwright, headless
pytest --engine=selenium        # same tests on Selenium
pytest tests/test_login.py      # one file
pytest -k oos14                 # one scenario by its ID (OOS-14)
HEADLESS=0 pytest               # watch the browser
./run_tests.sh                  # local pipeline: both engines, one report each
```

Nothing has to be running before: the tests start the local app by themselves. To open it yourself:

```bash
python app/server.py            # http://127.0.0.1:5055/
```

The reports are written to `reports/` (ignored by git): `reports/report.html` for a normal run, and
`run_tests.sh` also writes `reports/report-selenium.html`.

## The local app

`app/server.py` is a small Flask app that copies what the tests need from saucedemo: same URLs,
ids, `data-test` attributes, error messages, validation order and the 8% tax. Users and products
come from `Data/*.json`, the same files the tests read.

- **Port:** 5055, base URL `http://127.0.0.1:5055/` (change the port with `APP_PORT`)
- **Command:** `python app/server.py`

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
| Explicit wait (s) | `explicitWait` | `EXPLICIT_WAIT` | 10 |
| App port | | `APP_PORT` | 5055 |

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
app/                       Local copy of saucedemo (Flask)
Configuration/config.ini   Settings
Core/                      Engine interface, Selenium and Playwright implementations, factory
Data/                      Test data: users.json, products.json, customer.json
Drivers/                   Optional, git-ignored: your own chromedriver (see "Browsers")
PageObjects/               One class per page, plus MenuComponent (shared by all pages)
Utilities/                 Config reader, test data reader, step logging
tests/                     The tests, one file per area, and the fixtures (tests/conftest.py)
conftest.py                Registers --engine
pytest.ini                 Test path, HTML report and live logging
run_tests.sh               Local pipeline
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

## Adding tests

1. Put new data (users, products, customer) in `Data/*.json`, not in the tests.
2. Add locators and actions to the page class in `PageObjects/`, using only `Engine` methods so the
   page works on both engines.
3. Write the test in `tests/` and reuse the fixtures (`logged_in`, `login_as`, `go_to_page`, `pages`).
