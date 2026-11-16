# Login scenarios
import pytest

from Utilities.testData import TestData


class TestLogin:
    @pytest.mark.parametrize('username', ['standard_user', 'problem_user'])
    def test_user_logs_in(self, open_login, pages, engine, username):
        """Usuario se Logea"""
        pages.login.Login(username, TestData.password(username))
        engine.wait_until(lambda: 'inventory' in engine.current_url, 'The user is not logged in',
                          label='check the user is logged in (products page)')

    def test_user_logs_out(self, logged_in, pages, engine, base_url):
        """Usuario se deslogea"""
        engine.wait_until(lambda: 'inventory' in engine.current_url, 'The user is not logged in',
                          label='check the user is logged in (products page)')
        pages.menu.Open()
        pages.menu.ClickLogout()
        engine.wait_until(lambda: engine.current_url == base_url,
                          f'The user is not logged out, current URL: {engine.current_url}',
                          label='check the user is back on the login page')

    def test_oos07_script_in_username_is_text_not_code(self, open_login, pages, engine):
        """OOS-07 (security): un script digitado en el usuario se muestra como texto y nunca se ejecuta"""
        payload = '<script>window.__xss=1</script>'
        pages.login.Login(payload, 'secret_sauce')
        assert 'Username and password do not match' in pages.login.GetErrorMessage()
        assert engine.no_alert_is_present(), 'Typed code ran: an alert appeared'
        assert engine.evaluate('window.__xss === undefined'), 'The typed script was executed'
        assert pages.login.GetUserNameValue() == payload

    def test_oos03_spaces_only_password_says_do_not_match(self, open_login, pages, engine, base_url):
        """OOS-03 (product decision pending): password solo de espacios muestra 'do not match'
        y no 'Password is required'. Documents what the site does today."""
        pages.login.Login('standard_user', '   ')
        assert 'Username and password do not match' in pages.login.GetErrorMessage()
        assert engine.current_url == base_url, 'The user left the login page'

    # ---- new scenarios ----
    def test_wrong_password_is_rejected(self, open_login, pages, engine, base_url):
        """Login con contraseña incorrecta"""
        pages.login.Login('standard_user', 'wrong_password')
        message = pages.login.GetErrorMessage()
        assert 'Epic sadface: Username and password do not match any user in this service' in message
        assert engine.current_url == base_url, 'The user left the login page'

    def test_locked_out_user_is_rejected(self, open_login, pages, engine, base_url):
        """Login con usuario bloqueado, aunque la contraseña sea correcta"""
        pages.login.Login('locked_out_user', TestData.password('locked_out_user'))
        assert 'Epic sadface: Sorry, this user has been locked out.' in pages.login.GetErrorMessage()
        assert engine.current_url == base_url, 'The user left the login page'

    def test_empty_password_asks_for_it(self, open_login, pages, engine, base_url):
        """Login con contraseña vacía"""
        pages.login.SetUserName('standard_user')
        pages.login.ClickLoginButton()
        assert 'Epic sadface: Password is required' in pages.login.GetErrorMessage()
        assert engine.current_url == base_url, 'The user left the login page'
