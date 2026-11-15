# Creates the engine chosen with --engine. Adding a new engine only means adding it here.

ENGINES = ('playwright', 'selenium')
DEFAULT_ENGINE = 'playwright'


def create_engine(name, headless=True):
    if name == 'selenium':
        from Core.selenium_engine import SeleniumEngine
        return SeleniumEngine(headless=headless)
    if name == 'playwright':
        from Core.playwright_engine import PlaywrightEngine
        return PlaywrightEngine(headless=headless)
    raise ValueError(f"Unknown engine '{name}'. Use one of: {', '.join(ENGINES)}")
