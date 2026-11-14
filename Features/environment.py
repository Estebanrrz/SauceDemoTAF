# Hooks: driver lifecycle, logging, screenshot on failure, retries and the run report
import logging
import os
import re

from behave.contrib.scenario_autoretry import patch_scenario_with_autoretry
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service

from PageObjects.CheckOutStepOnePage import CheckOutStepOnePage
from PageObjects.CheckoutCompletePage import CheckoutCompletePage
from PageObjects.InventoryPage import InventoryPage
from PageObjects.LoginPage import LoginPage
from PageObjects.MenuComponent import MenuComponent
from PageObjects.OverviewPage import OverviewPage
from PageObjects.ShoppingCartPage import ShoppingCartPage
from Utilities.readProperties import ReadConfig
from Utilities.reportGenerator import RunReport

log = logging.getLogger('saucedemo')


BAD = ('failed', 'error')  # behave 1.3: assertion -> failed, any other exception -> error


def _key(scenario):
    return f'{os.path.basename(scenario.filename)}:{scenario.line}'


def _slug(text):
    return re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_')[:60]


def _createDriver(options):
    # Preferred: Selenium Manager resolves a chromedriver that matches the installed Chrome.
    try:
        return webdriver.Chrome(options=options)
    except WebDriverException as e:
        # Fallback: the chromedriver kept in Drivers/ (its version must match the installed Chrome)
        log.warning('Selenium Manager failed (%s); using %s', str(e).splitlines()[0], ReadConfig.getLocalDriverPath())
        return webdriver.Chrome(service=Service(ReadConfig.getLocalDriverPath()), options=options)


def before_all(context):
    context.artifactsDir = ReadConfig.getArtifactsDir()
    os.makedirs(os.path.join(context.artifactsDir, 'screenshots'), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(os.path.join(context.artifactsDir, 'run.log'), mode='w', encoding='utf-8')])
    context.report = RunReport(context.artifactsDir, ReadConfig.getApplicationUrl())
    log.info('Run started against %s (retries=%s)', ReadConfig.getApplicationUrl(), ReadConfig.getRetries())


def before_feature(context, feature):
    # Retries hide flakiness if nobody looks: every retried scenario is flagged "flaky" in the report.
    if ReadConfig.getRetries() > 0:
        for scenario in feature.walk_scenarios():
            patch_scenario_with_autoretry(scenario, max_attempts=ReadConfig.getRetries() + 1)


def before_scenario(context, scenario):
    context.report.startAttempt(_key(scenario))
    log.info('START %s - %s', _key(scenario), scenario.name)
    options = webdriver.ChromeOptions()
    if ReadConfig.isHeadless():
        options.add_argument('--headless=new')
    context.driver = _createDriver(options)
    context.driver.implicitly_wait(3)
    # Never hang forever on a slow page or script: fail the step instead
    context.driver.set_page_load_timeout(ReadConfig.getPageLoadTimeout())
    context.driver.set_script_timeout(15)
    context.driver.maximize_window()
    context.url = ReadConfig.getApplicationUrl()
    context.screenshot = None
    context.loginPage = LoginPage(context.driver)
    context.InventoryPage = InventoryPage(context.driver)
    context.ShoppingCartPage = ShoppingCartPage(context.driver)
    context.CheckOutStepOnePage = CheckOutStepOnePage(context.driver)
    context.OverviewPage = OverviewPage(context.driver)
    context.CheckoutCompletePage = CheckoutCompletePage(context.driver)
    context.Menu = MenuComponent(context.driver)


def after_step(context, step):
    if step.status.name in BAD:
        log.error('STEP FAILED: %s %s | %s', step.keyword, step.name, step.error_message)
        # Screenshot at the moment of failure, before the browser is closed
        path = os.path.join(context.artifactsDir, 'screenshots',
                            f'{_slug(context.scenario.name)}_{context.scenario.line}.png')
        try:
            context.driver.save_screenshot(path)
            context.screenshot = path
        except Exception as e:  # a dead browser must not hide the real failure
            log.warning('Could not take screenshot: %s', e)


def after_scenario(context, scenario):
    status = scenario.compute_status().name
    status = 'failed' if status in BAD else status
    error = next((s.error_message for s in scenario.steps if s.status.name in BAD and s.error_message), None)
    log.info('END %s -> %s', _key(scenario), status)
    context.report.record(_key(scenario), os.path.basename(scenario.filename), scenario.name,
                          scenario.effective_tags, status, scenario.duration, error,
                          context.screenshot if status == 'failed' else None)
    if hasattr(context, 'driver'):
        context.driver.quit()


def after_all(context):
    path = context.report.write()
    summary = context.report.summary()
    log.info('Run finished: %s', summary)
    print(f"\nReport: {path}  ({summary['passed']}/{summary['total']} passed, {summary['flaky']} flaky)")
