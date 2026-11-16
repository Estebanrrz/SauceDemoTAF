# SauceDemoTAF

UI test automation framework for [saucedemo.com](https://www.saucedemo.com/), written with the Page
Object pattern. The tests run with **pytest** and can use two browser engines, **Playwright** (default)
and **Selenium**, chosen with one option. They run against a local copy of the site, so no internet
is needed. With Playwright they can also run as a phone or tablet (`--device="iPhone 13"`), see
"Mobile".

**40 tests**: the 31 scenarios the project already had plus 6 new ones (9 test cases, because the
sorting scenario runs once per sort option). All pass on both engines. On top of them,
`tests/test_mobile.py` checks the phone and desktop layouts on every supported device (see "Mobile").

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
pytest                          # all tests, Playwright, headless
pytest --engine=selenium        # same tests on Selenium
pytest --device="iPhone 13"     # same tests on Playwright, emulating an iPhone 13
pytest --device="iPhone 13, Pixel 7"   # the whole suite once per device, one report each
pytest --device="iPhone 13, Pixel 7" --parallel   # the same, all devices at the same time
pytest tests/test_login.py      # one file
pytest -k oos14                 # one scenario by its ID (OOS-14)
HEADLESS=0 pytest               # watch the browser
./run_tests.sh                  # local pipeline: setup.sh, both engines, every device, one report each
```

Nothing has to be running before: the tests start the local app by themselves. To open it yourself:

```bash
python app/server.py            # http://127.0.0.1:5055/
```

The reports are written to `reports/` (ignored by git), one file per engine and device, so runs do
not overwrite each other: `report.html` (Playwright, desktop), `report-selenium.html`,
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
    in the other runs, so no test is repeated. One device: 55 tests. Two devices (with or without
    `--parallel`): 55 + 47 = 102 tests.

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
| Devices to emulate (Playwright), comma separated | `device` | `DEVICE` (or `--device`) | (desktop 1280x900) |
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
conftest.py                Registers --engine and --device
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

## Adding tests

1. Put new data (users, products, customer) in `Data/*.json`, not in the tests.
2. Add locators and actions to the page class in `PageObjects/`, using only `Engine` methods so the
   page works on both engines.
3. Write the test in `tests/` and reuse the fixtures (`logged_in`, `login_as`, `go_to_page`, `pages`).
