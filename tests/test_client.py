# tests/test_client.py
import pytest
import base64
import json
from liqpay_api.client import LiqPayAsync
from liqpay_api.utils import make_signature, get_encoded_data

def test_signature_generation():
    # Test signature generation.
    
    private_key = "test_private_key"
    data = "test_data"
    # base64_encode(sha1(private_key + data + private_key))
    
    import hashlib
    expected_to_sign = f"{private_key}{data}{private_key}"
    sha1 = hashlib.sha1(expected_to_sign.encode("utf-8")).digest()
    expected_sig = base64.b64encode(sha1).decode("ascii")
    
    assert make_signature(private_key, data) == expected_sig

def test_encoded_data():
    # Test encoded data.
    
    params = {"author": "oldnum", "dev": True, "status": 0}  
    encoded = get_encoded_data(params)
    decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert decoded == params

@pytest.mark.asyncio
async def test_client_initialization():
    # Test client initialization.
    
    liqpay_async_api = LiqPayAsync("public", "private")
    assert liqpay_async_api.public_key == "public"
    assert liqpay_async_api.private_key == "private"

def test_cnb_form():
    # Test CNB form generation.
    
    liqpay_async_api = LiqPayAsync("public", "private")
    params = {
        "action": "pay",
        "amount": 100,
        "currency": "UAH",
        "description": "Test Payment",
        "order_id": "ORDER-123"
    }
    form = liqpay_async_api.generate_cnb_form(params)
    assert '<input type="hidden" name="data"' in form
    assert '<input type="hidden" name="signature"' in form
    assert 'ORDER-123' not in form # It should be encoded in data

def test_validation_failure():
    # Test validation failure.

    liqpay_async_api = LiqPayAsync("public", "private")
    params = {
        "action": "invalid_action",
        "amount": -10,
        "currency": "INVALID",
    }
    with pytest.raises(ValueError):
        liqpay_async_api.generate_cnb_form(params)

def test_rro_info_encoding():
    # Test RRO info encoding.

    liqpay_async_api = LiqPayAsync("public", "private")
    params = {
        "action": "pay",
        "amount": 404,
        "currency": "UAH",
        "description": "RRO Test",
        "order_id": "RRO-1",
        "rro_info": {
            "items": [
                {
                    "amount": 2,
                    "price": 202,
                    "cost": 404,
                    "id": 123456
                }
            ],
            "delivery_emails": ["email1@email.com"]
        }
    }
    url = liqpay_async_api.generate_checkout_url(params)
    assert "data=" in url
    assert "signature=" in url

def test_generate_direct_checkout_url():
    # Test direct checkout URL generation.

    liqpay_async_api = LiqPayAsync("public", "private")
    params = {
        "action": "pay",
        "amount": 100,
        "currency": "UAH",
        "description": "Test Payment",
        "order_id": "DIRECT-123"
    }
    url = liqpay_async_api.generate_checkout_url(params)
    assert url.startswith("https://www.liqpay.ua/api/3/checkout?")
    assert "data=" in url
    assert "signature=" in url

@pytest.mark.asyncio
async def test_status_check_api(mocker):
    # Mocking fetch_url instead of aiohttp for cleaner test
    liqpay_async_api = LiqPayAsync("public", "private")
    mock_fetch = mocker.patch.object(liqpay_async_api, 'fetch_url', new_callable=mocker.AsyncMock)
    mock_fetch.return_value = {
        "result": "ok",
        "status": "success",
        "order_id": "STATUS-123"
    }

    result = await liqpay_async_api.get_status("STATUS-123")
    
    assert result["status"] == "success"
    assert result["order_id"] == "STATUS-123"
    mock_fetch.assert_called_once()
    
    # Check that data contains action=status
    args, _ = mock_fetch.call_args
    payload = args[1]
    decoded_data = json.loads(base64.b64decode(payload["data"]).decode("utf-8"))
    assert decoded_data["action"] == "status"
    assert decoded_data["order_id"] == "STATUS-123"

@pytest.mark.asyncio
async def test_convenience_methods(mocker):
    # Test high-level convenience methods (pay, hold, subscribe)
    liqpay_async_api = LiqPayAsync("public", "private")
    mock_fetch = mocker.patch.object(liqpay_async_api, 'fetch_url', new_callable=mocker.AsyncMock)
    mock_fetch.return_value = {"result": "ok"}

    params = {
        "amount": 100,
        "currency": "UAH",
        "description": "Test",
        "order_id": "ORDER-1"
    }

    # Test pay
    await liqpay_async_api.pay(params.copy())
    # Test hold
    await liqpay_async_api.hold(params.copy())
    # Test subscribe
    subscribe_params = params.copy()
    subscribe_params["subscribe_date_start"] = "2026-01-01 00:00:00"
    await liqpay_async_api.subscribe(subscribe_params)

    assert mock_fetch.call_count == 3

@pytest.mark.asyncio
async def test_get_payment_url(mocker):
    # Mocking fetch_url to verify it's used correctly
    liqpay_async_api = LiqPayAsync("public", "private")
    mock_fetch = mocker.patch.object(liqpay_async_api, 'fetch_url', new_callable=mocker.AsyncMock)
    mock_fetch.return_value = {
        "result": "ok",
        "_url": "https://www.liqpay.ua/api/3/checkout/session_123"
    }

    params = {
        "action": "pay",
        "amount": 100,
        "currency": "UAH",
        "description": "POST Test",
        "order_id": "POST-123"
    }
    
    url = await liqpay_async_api.get_payment_url(params)
    
    assert url == "https://www.liqpay.ua/api/3/checkout/session_123"
    mock_fetch.assert_called_once()
