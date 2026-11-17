# Client of the payment mock's test hook: what charges did the shop send it?
import os

import requests

from Utilities.readProperties import ReadConfig
from Utilities.steps import step


def mock_url():
    return (os.environ.get('PAYMENT_URL') or 'http://127.0.0.1:5056/').rstrip('/') + '/'


class PaymentMockClient:
    def __init__(self):
        self.timeout = ReadConfig.getExplicitWait()

    @step('check the payment mock is reachable')
    def check_reachable(self):
        """Fail with a clear message instead of letting order tests fail later with a puzzling 502."""
        try:
            requests.get(mock_url() + '__requests', params={'reference': '-'}, timeout=self.timeout)
        except requests.RequestException as error:
            raise AssertionError(
                f'The payment mock at {mock_url()} is not reachable ({type(error).__name__}). If another process '
                f'started it (e.g. a "python app/server.py" that has stopped), start it again or free port 5056 '
                f'so the test run starts its own.') from None

    @step('read the charges the payment service received for {reference}')
    def charges_for(self, reference):
        """The charge requests the shop sent for that order reference, oldest first."""
        response = requests.get(mock_url() + '__requests', params={'reference': reference}, timeout=self.timeout)
        assert response.status_code == 200, f'The payment mock test hook failed: {response.status_code}'
        return response.json()['requests']
