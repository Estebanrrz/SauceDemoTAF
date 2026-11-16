# Side menu, logout and session scenarios
import pytest


def check_on_products_page(pages, engine):
    engine.wait_until(lambda: 'inventory.html' in engine.current_url, 'Not on the products page',
                      label='check the products page is shown')
    assert pages.inventory.GetItemNames(), 'The products page lists no products'


class TestMenu:
    @pytest.mark.parametrize('page_name', [
        'inventory', 'cart', 'checkout step one', 'checkout overview', 'checkout complete',
    ])
    def test_oos08_logout_from_any_page(self, go_to_page, pages, engine, base_url, page_name):
        """OOS-08: logout desde cualquier pagina"""
        go_to_page(page_name)
        pages.menu.Open()
        pages.menu.ClickLogout()
        engine.wait_until(lambda: engine.current_url == base_url,
                          f'The user is not logged out, current URL: {engine.current_url}',
                          label='check the user is back on the login page')

    def test_oos09_all_items_from_the_cart(self, go_to_page, pages, engine):
        """OOS-09: All Items lleva a la pagina de productos desde el carro"""
        go_to_page('cart')
        pages.menu.Open()
        pages.menu.ClickAllItems()
        check_on_products_page(pages, engine)

    def test_oos09_close_menu_keeps_the_page(self, logged_in, pages, engine):
        """OOS-09: Close Menu cierra el menu sin cambiar de pagina"""
        pages.menu.Open()
        pages.menu.Close()
        engine.wait_until(lambda: not pages.menu.IsOpen(), 'The menu is still open',
                          label='check the side menu is closed')
        check_on_products_page(pages, engine)

    def test_oos10_second_tab_shares_session_and_cart(self, logged_in, pages, engine, base_url):
        """OOS-10: una segunda pestaña comparte la sesion y el carro"""
        pages.inventory.AddtoCartItem('Sauce Labs Backpack')
        engine.open_new_tab(base_url + 'inventory.html')
        check_on_products_page(pages, engine)
        assert pages.inventory.GetCounterShoppincart() == '1', 'The cart counter is not the expected one'
