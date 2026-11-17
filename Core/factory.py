# Creates the engine chosen with --engine. Adding a new engine only means adding it here.

ENGINES = ('playwright', 'selenium')
DEFAULT_ENGINE = 'playwright'


def resolve_device(name, device):
    """Exact Playwright name of the device to emulate, or None for desktop. ValueError if the engine is
    not Playwright or the device does not exist."""
    if not device:
        return None
    if name != 'playwright':
        raise ValueError(f"--device works with Playwright only (device emulation), not with '{name}'. "
                         f"Use --engine=playwright.")
    from Core.playwright_engine import find_device
    return find_device(device)


def create_engine(name, headless=True, device=None):
    if name == 'selenium':
        from Core.selenium_engine import SeleniumEngine
        return SeleniumEngine(headless=headless)
    if name == 'playwright':
        from Core.playwright_engine import PlaywrightEngine
        return PlaywrightEngine(headless=headless, device=device)
    raise ValueError(f"Unknown engine '{name}'. Use one of: {', '.join(ENGINES)}")


def finish_thread(name):
    """Call at the end of a thread (not the main one) that created engines: frees what that thread started.
    Playwright keeps one browser per thread; Selenium has nothing to free (quit() closes everything)."""
    if name == 'playwright':
        from Core.playwright_engine import close_this_thread
        close_this_thread()
