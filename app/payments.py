# Client of the payment service, used by the orders API.
#
# The shop only knows this contract: POST {PAYMENT_URL}payments with the card, the amount in cents and
# a reference; 201 means charged, 402 means the card was declined, anything else means the service has
# a problem. In this repo the service is mocks/payment_mock.py, but the shop cannot tell the difference.

import os

import requests

DEFAULT_URL = 'http://127.0.0.1:5056/'


class PaymentDeclined(Exception):
    """The service answered: this card does not pay."""


class PaymentUnavailable(Exception):
    """The service did not answer, answered too late, or broke."""


def service_url():
    return (os.environ.get('PAYMENT_URL') or DEFAULT_URL).rstrip('/') + '/'


def timeout_seconds():
    return float(os.environ.get('PAYMENT_TIMEOUT') or 3)


def charge(card, amount_cents, reference):
    """Charge the card and return the payment id, or raise PaymentDeclined / PaymentUnavailable."""
    try:
        response = requests.post(service_url() + 'payments',
                                 json={'card': card, 'amount_cents': amount_cents, 'currency': 'USD',
                                       'reference': reference},
                                 timeout=timeout_seconds())
    except requests.RequestException as error:
        raise PaymentUnavailable(f'the payment service did not answer: {error}') from error
    if response.status_code == 201:
        return response.json()['payment_id']
    if response.status_code == 402:
        raise PaymentDeclined(response.json().get('reason', 'the card was declined'))
    raise PaymentUnavailable(f'the payment service answered {response.status_code}')
