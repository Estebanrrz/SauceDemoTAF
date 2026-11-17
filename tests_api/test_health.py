# Health check and the error shape of the whole API
import requests

from tests_api.checks import HEALTH, check_contract, check_error, json_of


class TestHealth:
    def test_health_says_ok_without_a_token(self, api):
        """GET /health answers 200 with the app and the database up, and needs no token"""
        body = json_of(api.get('health'), 200)
        check_contract(body, HEALTH)
        assert body == {'status': 'ok', 'database': 'ok'}


class TestErrorShape:
    def test_unknown_endpoint_is_a_json_404(self, api):
        """An URL that does not exist under /api/v1/ answers 404 with the standard JSON error"""
        check_error(api.get('does-not-exist'), 404, 'not_found')

    def test_wrong_method_is_a_json_405(self, user_api):
        """A method the endpoint does not support (DELETE /products) answers 405 with the standard JSON error"""
        check_error(user_api.request('DELETE', 'products'), 405, 'method_not_allowed')

    def test_web_pages_keep_their_html_errors(self, base_url, api):
        """Outside /api/ nothing changed: a missing web page is still an HTML 404, not JSON"""
        response = requests.get(base_url + 'no-such-page.html', timeout=api.timeout)
        assert response.status_code == 404
        assert response.headers['Content-Type'].startswith('text/html')
