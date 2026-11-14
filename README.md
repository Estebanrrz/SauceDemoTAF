# SauceDemoTAF

UI test automation framework for [saucedemo.com](https://www.saucedemo.com/): Python, Selenium and behave (BDD,
Spanish-language Gherkin steps), built on the Page Object pattern.

Covers login/logout, menu, session, sorting, cart and checkout: **31 scenarios** against the real site.

Known limitation: each feature passes when run on its own, but a full run on a heavily loaded machine can fail at
random (clicks that do not register in time). Close other browsers before a full run. Failed scenarios are retried
once and, if they pass, reported as flaky in `artifacts/report.html`.

## Requirements

- Python 3.11 or newer
- Google Chrome. Selenium Manager downloads the matching chromedriver automatically.
- **Fallback driver:** if Selenium Manager cannot download one (no internet, proxy), the framework uses
  `Drivers/chromedriver.exe`. The bundled one is **version 108**, so it only works with Chrome 108: for any other
  Chrome download the matching version from https://googlechromelabs.github.io/chrome-for-testing/ and replace the file.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```powershell
behave                                   # everything
behave features/Cart.feature             # one feature
behave --tags=@OOS-14                    # one scenario by ID
behave --tags=@security                  # by category
$env:HEADLESS = "1"; behave              # headless Chrome (bash: HEADLESS=1 behave)
```

Settings are resolved as: **environment variable > `Configuration/config.ini` > default**.

| Setting | config.ini | Environment variable | Default |
|---|---|---|---|
| Base URL | `baseUrl` | `SAUCEDEMO_URL` | https://www.saucedemo.com/ |
| Headless Chrome | `headless` | `HEADLESS` | false |
| Extra attempts for a failed scenario | `retries` | `RETRIES` | 1 |
| Explicit wait (s) | `explicitWait` | `EXPLICIT_WAIT` | 10 |
| Output folder | `[paths] artifacts` | `ARTIFACTS_DIR` | `artifacts` |

## Output (`artifacts/`, git-ignored)

| File | Content |
|---|---|
| `report.html` | Summary cards (total / passed / failed / skipped / flaky, pass rate) and a table of every scenario with attempts, duration, error and screenshot link |
| `report.json` | Same data, machine-readable (for CI or further analysis) |
| `run.log` | Timestamped log: scenario start/end and each failed step with its error |
| `screenshots/` | One PNG taken at the moment a step fails |

**Retries and flakiness.** A failed scenario is retried (`retries`). If it passes on a later attempt it is reported as
**flaky**, never as a plain pass, so retries do not hide unreliable tests. Set `RETRIES=0` to see raw results.

## Project layout

```
Configuration/config.ini     Settings (URL, timeouts, retries, paths)
Drivers/chromedriver.exe     Fallback chromedriver (v108), used only if Selenium Manager fails
Data/                        Test data: users.json, products.json, customer.json
Features/*.feature           Scenarios (Gherkin)
Features/Steps/              Step definitions
Features/environment.py      Hooks: driver, logging, screenshot on failure, retries, report
PageObjects/                 One class per page, plus MenuComponent (shared by all pages)
Utilities/readProperties.py  Config reader
Utilities/testData.py        Test data reader (credentials come from Data/users.json)
Utilities/reportGenerator.py HTML + JSON report
```

## Scenario tags

Each extended scenario carries an ID from the coverage-gap list (`@OOS-03` ... `@OOS-23`). Other tags:
`@product-decision` (documents current behaviour of a point that still needs a product decision, so the assertion
may need to change), `@security`, `@catalog`.

Scenarios of the gap list that cannot pass against the real site (OOS-01, 02, 05, 06, 11, 18, 19, 22, 24: they
depend on a replica's behaviour or on direct server requests) are intentionally not included. To run the suite
against a replica, set `SAUCEDEMO_URL`.

## Adding tests

1. Put new data (users, products) in `Data/*.json`, not in the steps.
2. Add locators and actions to the matching class in `PageObjects/`; clicks go through `click_by_Xpath`, which waits
   for the element to be clickable.
3. Write the scenario in a `.feature` file and reuse existing steps where possible (`behave --dry-run` lists undefined ones).
