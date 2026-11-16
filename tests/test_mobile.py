# Mobile layout scenarios. Local app only: the real saucedemo has no #mobile-menu-button.
#
# TestThisRun    the device of this run (desktop, or --device="..."): the right menu button is shown
#                and no page scrolls sideways. With --device the rest of the suite runs on it too.
# TestEachDevice every supported device, in every Playwright run (no --device needed): it gets the
#                layout written below, its menu button works and every page fits its screen.
import pytest

from Utilities.testData import TestData

pytestmark = pytest.mark.mobile

# Supported devices and the layout each one must get: phone layout up to 600px wide, desktop above
DEVICE_LAYOUTS = {
    'iPhone 13': 'phone',              # 390px
    'Pixel 7': 'phone',                # 412px
    'iPhone 13 landscape': 'desktop',  # 750px
    'iPad Mini': 'desktop',            # 768px
}
PAGES = ['inventory', 'cart', 'checkout step one', 'checkout overview', 'checkout complete']


def check_menu_button(pages, phone):
    """Exactly one menu button is shown: the phone one on the phone layout, the desktop one otherwise."""
    visible = {'phone': pages.menu.IsMobileButtonVisible(), 'desktop': pages.menu.IsDesktopButtonVisible()}
    expected = {'phone': phone, 'desktop': not phone}
    assert visible == expected, f'Menu buttons shown: {visible}, expected: {expected}'


class TestThisRun:
    def test_the_right_menu_button_is_shown(self, logged_in, pages, engine):
        """Se ve el boton de menu del diseño actual (movil o escritorio) y no el otro"""
        check_menu_button(pages, engine.phone_layout)

    def test_login_page_fits_the_screen(self, open_login, pages):
        """La pagina de login cabe en el ancho de la pantalla"""
        assert pages.login.FitsScreenWidth(), 'The login page scrolls sideways'

    @pytest.mark.parametrize('page_name', PAGES)
    def test_page_fits_the_screen(self, go_to_page, pages, page_name):
        """Cada pagina cabe en el ancho de la pantalla"""
        go_to_page(page_name)
        assert pages.inventory.FitsScreenWidth(), f'The {page_name} page scrolls sideways'


@pytest.mark.all_devices  # with several --device they run with the first device only (root conftest.py)
@pytest.mark.parametrize('device', list(DEVICE_LAYOUTS))  # overrides --device for these tests only
class TestEachDevice:
    def test_device_gets_its_layout(self, device, logged_in, pages, engine):
        """Cada dispositivo recibe su diseño, con su boton de menu, y el menu abre y cierra"""
        phone = DEVICE_LAYOUTS[device] == 'phone'
        assert engine.phone_layout == phone, f'The framework expects the wrong layout for {device}'
        check_menu_button(pages, phone)
        pages.menu.Open()
        engine.wait_until(pages.menu.IsOpen, 'The menu did not open', label='check the side menu is open')
        pages.menu.Close()
        engine.wait_until(lambda: not pages.menu.IsOpen(), 'The menu is still open',
                          label='check the side menu is closed')

    def test_every_page_fits_the_device_screen(self, device, open_login, pages):
        """Una compra completa en el dispositivo: ninguna pagina se desplaza hacia los lados"""
        too_wide = []

        def check(page_name):
            if not pages.login.FitsScreenWidth():
                too_wide.append(page_name)

        check('login')
        pages.login.Login('standard_user', TestData.password('standard_user'))
        assert pages.inventory.GetItemNames(), 'The products page lists no products'
        check('inventory')
        pages.inventory.AddtoCartItem('Sauce Labs Backpack')
        pages.inventory.ClickShoppingCartButton()
        assert pages.cart.GetItemNames() == ['Sauce Labs Backpack']
        check('cart')
        pages.cart.ClickButtonCheckout()
        customer = TestData.customer()
        pages.checkout_one.FillInformation(customer['firstName'], customer['lastName'], customer['postalCode'])
        check('checkout step one')
        pages.checkout_one.ClickOnContinueButton()
        assert pages.overview.GetTotal().startswith('Total: $')
        check('checkout overview')
        pages.overview.ClickFinishButton()
        assert pages.complete.ThankYouForYourOrderIsDisplayed() is True
        check('checkout complete')
        assert not too_wide, f'These pages scroll sideways on {device}: {too_wide}'
