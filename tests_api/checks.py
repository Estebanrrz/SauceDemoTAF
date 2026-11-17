# Checks shared by the API tests: status codes, JSON bodies, the error shape and "contracts".
#
# A contract is the list of fields an answer must have and the type of each one. check_contract fails
# when a field is missing, when there is an extra field (it could leak data, e.g. a password) or when
# a field has the wrong type. Every failure message includes the request and the answer.

from tests_api.clients.api_client import describe

NUMBER = (int, float)

# ---- contracts: field -> type ----
LOGIN = {'token': str, 'token_type': str, 'username': str, 'expires_in': NUMBER}
PRODUCT = {'id': int, 'slug': str, 'name': str, 'description': str, 'price': NUMBER}
ERROR = {'code': str, 'message': str}
HEALTH = {'status': str, 'database': str}
CART = {'items': list}
ORDER_ITEM = {'id': int, 'name': str, 'price': NUMBER}
ORDER = {'id': int, 'status': str, 'reference': str, 'payment_id': str, 'items': list,
         'subtotal': NUMBER, 'tax': NUMBER, 'total': NUMBER}


def check_contract(data, contract, what='the answer'):
    assert isinstance(data, dict), f'{what} should be a JSON object, got {data!r}'
    missing = sorted(set(contract) - set(data))
    extra = sorted(set(data) - set(contract))
    assert not missing and not extra, f'{what}: missing fields {missing}, unexpected fields {extra} in {data}'
    wrong = {field: type(data[field]).__name__ for field, kind in contract.items()
             if isinstance(data[field], bool) or not isinstance(data[field], kind)}  # True is an int in Python
    assert not wrong, f'{what}: fields with the wrong type {wrong} in {data}'


def json_of(response, status):
    """Check the status code and that the answer is JSON, then return the body."""
    assert response.status_code == status, f'Expected status {status}, got {describe(response)}'
    content_type = response.headers.get('Content-Type', '')
    assert content_type.startswith('application/json'), f'Expected JSON, got {content_type!r}: {describe(response)}'
    return response.json()


def check_error(response, status, code, message=None):
    """The answer is the standard error {"error": {"code", "message"}} with this status and code."""
    body = json_of(response, status)
    assert set(body) == {'error'}, f'Expected only "error" in the body, got {body}'
    check_contract(body['error'], ERROR, 'the error')
    assert body['error']['code'] == code, f"Expected error code {code!r}, got {describe(response)}"
    if message is not None:
        assert body['error']['message'] == message, f'Expected message {message!r}, got {describe(response)}'
    return body['error']
