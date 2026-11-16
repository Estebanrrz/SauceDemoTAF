# Root conftest: registers the --engine option.
#
#   pytest                       Playwright (default), headless
#   pytest --engine=selenium     same tests on Selenium

from Core.factory import DEFAULT_ENGINE, ENGINES


def pytest_addoption(parser):
    parser.addoption(
        '--engine',
        action='store',
        default=None,
        choices=list(ENGINES),
        help=f'Browser engine to run the tests with (default: {DEFAULT_ENGINE})',
    )


def pytest_report_header(config):
    from Utilities.readProperties import ReadConfig
    engine = config.getoption('--engine') or ReadConfig.getDefaultEngine()
    return f'engine: {engine}, base url: {ReadConfig.getApplicationUrl()}, headless: {ReadConfig.isHeadless()}'
