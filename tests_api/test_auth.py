# Login through the API (POST /api/v1/auth/login) and the Bearer token (security cases)
#
# The login rules are the ones of the login page: same checks, same order, same messages. An unknown
# user and a wrong password get the same answer, so the API does not tell which users exist.
import pytest

from tests_api.checks import LOGIN, check_contract, check_error, json_of
from Utilities.testData import TestData

# Same texts as the login page (tests/test_login.py)
NO_MATCH = 'Epic sadface: Username and password do not match any user in this service'
LOCKED = 'Epic sadface: Sorry, this user has been locked out.'
USERNAME_REQUIRED = 'Epic sadface: Username is required'
PASSWORD_REQUIRED = 'Epic sadface: Password is required'

LOCKED_USER = TestData.locked_users()[0]


class TestLogin:
    @pytest.mark.parametrize('username', TestData.active_users())
    def test_user_gets_a_token(self, api, username):
        """Every user that is not locked gets a Bearer token, and the answer never contains the password"""
        password = TestData.password(username)
        response = api.login(username, password)
        body = json_of(response, 200)
        check_contract(body, LOGIN)
        assert body['token_type'] == 'Bearer'
        assert body['username'] == username
        assert len(body['token']) >= 32, 'The token is too short to be hard to guess'
        assert password not in response.text, 'The password is in the answer'

    def test_every_login_gets_a_new_token_and_both_work(self, api, token_for):
        """Logging in twice gives two different tokens, and both open the products"""
        first, second = token_for('standard_user'), token_for('standard_user')
        assert first != second, 'Two logins got the same token'
        for token in (first, second):
            json_of(api.with_token(token).get('products'), 200)


class TestLoginErrors:
    """Security and validation: a bad login never gets a token."""

    @pytest.mark.parametrize('body, status, code, message', [
        pytest.param({'username': 'standard_user', 'password': 'wrong_password'},
                     401, 'invalid_credentials', NO_MATCH, id='wrong-password'),
        pytest.param({'username': 'no_such_user', 'password': TestData.password('standard_user')},
                     401, 'invalid_credentials', NO_MATCH, id='unknown-user-same-answer-as-wrong-password'),
        pytest.param({'username': LOCKED_USER, 'password': TestData.password(LOCKED_USER)},
                     403, 'user_locked', LOCKED, id='locked-user'),
        pytest.param({'username': LOCKED_USER, 'password': 'wrong_password'},
                     401, 'invalid_credentials', NO_MATCH, id='locked-user-wrong-password-does-not-say-locked'),
        pytest.param({'username': 'standard_user', 'password': '   '},
                     401, 'invalid_credentials', NO_MATCH, id='spaces-only-password'),  # like OOS-03 on the page
        pytest.param({'username': '', 'password': 'secret_sauce'},
                     400, 'username_required', USERNAME_REQUIRED, id='empty-username'),
        pytest.param({'username': 'standard_user', 'password': ''},
                     400, 'password_required', PASSWORD_REQUIRED, id='empty-password'),
        pytest.param({'username': '', 'password': ''},
                     400, 'username_required', USERNAME_REQUIRED, id='both-empty-only-the-first-error'),
        pytest.param({},
                     400, 'username_required', USERNAME_REQUIRED, id='no-fields'),
        pytest.param({'username': 12345, 'password': 'secret_sauce'},
                     400, 'invalid_field', 'username must be a string', id='username-not-text'),
    ])
    def test_login_is_rejected(self, api, body, status, code, message):
        """The login fails with the right status, code and message, and the answer has no token"""
        response = api.post('auth/login', json=body)
        check_error(response, status, code, message)  # only {"error": ...}: no token in the answer

    def test_body_must_be_json(self, api):
        """A form-encoded body instead of JSON answers 400 invalid_json"""
        response = api.post('auth/login', data={'username': 'standard_user', 'password': 'secret_sauce'})
        check_error(response, 400, 'invalid_json')


class TestToken:
    """Security: only a valid token, sent as "Authorization: Bearer <token>", opens a protected endpoint."""

    def test_no_token_is_rejected(self, api):
        """Without the Authorization header: 401 missing_token, and the answer says a Bearer token is expected"""
        response = api.get('products')
        check_error(response, 401, 'missing_token')
        assert response.headers.get('WWW-Authenticate') == 'Bearer'

    @pytest.mark.parametrize('header', [
        pytest.param('Basic {token}', id='wrong-scheme'),
        pytest.param('Bearer', id='scheme-without-token'),
        pytest.param('{token}', id='token-without-scheme'),
    ])
    def test_badly_formed_header_is_rejected(self, api, token_for, header):
        """A header that is not "Bearer <token>" is rejected even if it holds a real token"""
        response = api.get('products', headers={'Authorization': header.format(token=token_for())})
        check_error(response, 401, 'missing_token')

    def test_made_up_token_is_rejected(self, api):
        """A token the server never gave out: 401 invalid_token"""
        check_error(api.with_token('made-up-token-' + 'x' * 30).get('products'), 401, 'invalid_token')

    def test_changed_token_is_rejected(self, api, token_for):
        """A real token with its last character changed no longer works"""
        token = token_for()
        changed = token[:-1] + ('A' if token[-1] != 'A' else 'B')
        check_error(api.with_token(changed).get('products'), 401, 'invalid_token')

    def test_token_in_the_url_is_not_accepted(self, api, token_for):
        """The token only works in the header: in the URL (?token=...) it would end up in logs and history"""
        check_error(api.get('products', params={'token': token_for()}), 401, 'missing_token')


class TestLogout:
    """Security: after logout the token is dead, and only that token."""

    def test_token_stops_working_after_logout(self, api, token_for):
        """POST /auth/logout answers 204, and then the same token gets 401 invalid_token"""
        user = api.with_token(token_for())
        json_of(user.get('products'), 200)
        response = user.post('auth/logout')
        assert response.status_code == 204, f'Expected 204, got {response.status_code}: {response.text}'
        assert response.text == '', 'A 204 answer must have no body'
        check_error(user.get('products'), 401, 'invalid_token')

    def test_logout_twice_is_rejected(self, api, token_for):
        """The second logout with the same token gets 401 invalid_token: the token no longer exists"""
        user = api.with_token(token_for())
        assert user.post('auth/logout').status_code == 204
        check_error(user.post('auth/logout'), 401, 'invalid_token')

    def test_logout_needs_a_token(self, api):
        """POST /auth/logout without a token: 401 missing_token"""
        check_error(api.post('auth/logout'), 401, 'missing_token')

    def test_logout_ends_only_that_token(self, api, token_for):
        """Two logins of the same user: logging out one of them leaves the other one working"""
        first, second = api.with_token(token_for()), api.with_token(token_for())
        assert first.post('auth/logout').status_code == 204
        check_error(first.get('products'), 401, 'invalid_token')
        json_of(second.get('products'), 200)
