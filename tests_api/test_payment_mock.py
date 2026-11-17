# The payment mock itself: the magic cards answer what the orders tests rely on
#
# If someone changes the mock, these tests say so directly, instead of orders tests failing far away.
import requests

from mocks.payment_mock import DECLINE_CARD, ERROR_CARD
from tests_api.clients.payment_mock_client import mock_url


def charge(card, amount_cents=100, reference='mock-check'):
    return requests.post(mock_url() + 'payments',
                         json={'card': card, 'amount_cents': amount_cents, 'reference': reference}, timeout=10)


class TestPaymentMock:
    def test_a_normal_card_is_approved(self, base_url):
        """Any ordinary card: 201 approved with a payment id"""
        response = charge('SauceCard #31337')
        assert response.status_code == 201
        body = response.json()
        assert body['status'] == 'approved' and body['payment_id'].startswith('pay-')

    def test_the_magic_cards(self, base_url):
        """The decline card answers 402 and the error card 500"""
        assert charge(DECLINE_CARD).status_code == 402
        assert charge(ERROR_CARD).status_code == 500

    def test_it_records_what_it_receives(self, base_url):
        """The test hook answers the charges of one reference, so order tests can check what was sent"""
        charge('SauceCard #31337', amount_cents=123, reference='mock-check-recording')
        seen = requests.get(mock_url() + '__requests', params={'reference': 'mock-check-recording'},
                            timeout=10).json()['requests']
        assert seen and seen[-1]['amount_cents'] == 123
