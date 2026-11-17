# Accessibility locators (Playwright only): the pages can be driven the way assistive technology sees them
#
# These tests find every control by its role and accessible name (get_by_role, get_by_label) instead of
# XPath, using Playwright's own locators on the raw page (engine.page). That is the point: they prove the
# pages carry proper accessible names, and they show Playwright's accessibility-locator feature. On
# Selenium they are skipped: it has no such locators.
#
# What gives each control its name: aria-label on the inputs and icon buttons, the text of normal
# buttons and links, and role="heading" on the page titles.
import pytest

from playwright.sync_api import expect

from Utilities.steps import step_scope
from Utilities.testData import TestData


@pytest.fixture
def page(engine, engine_name):
    """The raw Playwright page behind the engine."""
    if engine_name != 'playwright':
        pytest.skip('Accessibility locators (get_by_role, get_by_label) are a Playwright feature')
    return engine.page


def login_by_labels(page, username='standard_user'):
    with step_scope(f'log in as {username} using only roles and labels'):
        page.get_by_label('Username').fill(username)
        page.get_by_label('Password').fill(TestData.password(username))
        page.get_by_role('button', name='Login').click()


class TestAccessibilityLocators:
    def test_login_by_role_and_label(self, open_login, page):
        """The login page works driven only by labels and roles, and lands on the Products heading"""
        login_by_labels(page)
        expect(page.get_by_role('heading', name='Products')).to_be_visible()

    def test_full_purchase_by_role_and_label(self, open_login, page):
        """A whole purchase, from login to the thank-you heading, using only roles and labels"""
        product = TestData.productNames()[0]
        customer = TestData.customer()
        login_by_labels(page)
        with step_scope(f'buy {product} using only roles and labels'):
            page.get_by_role('button', name=f'Add {product} to cart').click()
            page.get_by_role('link', name='Shopping cart').click()
            expect(page.get_by_role('heading', name='Your Cart')).to_be_visible()
            page.get_by_role('button', name='Checkout').click()
            page.get_by_label('First Name').fill(customer['firstName'])
            page.get_by_label('Last Name').fill(customer['lastName'])
            page.get_by_label('Postal Code').fill(customer['postalCode'])
            page.get_by_role('button', name='Continue').click()
            expect(page.get_by_role('heading', name='Checkout: Overview')).to_be_visible()
            page.get_by_role('button', name='Finish').click()
        expect(page.get_by_role('heading', name='Thank you for your order!')).to_be_visible()

    def test_removing_by_accessible_name(self, logged_in, page):
        """Every product has its own accessible add / remove name, so the right one can be removed blindly"""
        first, second = TestData.productNames()[:2]
        with step_scope(f'add {first} and {second}, then remove {first}, using only roles'):
            page.get_by_role('button', name=f'Add {first} to cart').click()
            page.get_by_role('button', name=f'Add {second} to cart').click()
            page.get_by_role('button', name=f'Remove {first} from cart').click()
            expect(page.get_by_role('button', name=f'Add {first} to cart')).to_be_visible()
            expect(page.get_by_role('button', name=f'Remove {second} from cart')).to_be_visible()

    def test_menu_by_role(self, logged_in, page):
        """The side menu opens and closes by role; its links only join the accessibility tree while open.
        On a phone layout the phone menu button is found: the hidden desktop one has no role there."""
        with step_scope('open and close the side menu using only roles'):
            logout = page.get_by_role('link', name='Logout')
            expect(logout).not_to_be_visible()
            page.get_by_role('button', name='Open Menu').click()
            expect(logout).to_be_visible()
            page.get_by_role('button', name='Close Menu').click()
            expect(logout).not_to_be_visible()

    def test_sort_by_accessible_name(self, logged_in, page):
        """The sort box is found by its accessible name, and sorting by price puts the cheapest first"""
        cheapest = min(TestData.products(), key=TestData.products().get)
        with step_scope("sort by 'Price (low to high)' using the accessible name of the sort box"):
            page.get_by_role('combobox', name='Sort products').select_option(label='Price (low to high)')
            expect(page.locator('[data-test="inventory-item-name"]').first).to_have_text(cheapest)
