from unittest.mock import AsyncMock, patch
import pytest
from app.integrations import razorpay_client
from app.exceptions import ServiceOSException


@pytest.mark.asyncio
async def test_missing_keys_never_create_placeholder_orders_or_authorize_payments():
    with patch.object(razorpay_client, "_resolve_credentials", AsyncMock(return_value=("", "", ""))), \
         patch.object(razorpay_client.httpx, "AsyncClient") as http:
        with pytest.raises(ServiceOSException) as exc:
            await razorpay_client.create_order(100, "test")
        assert exc.value.error_code == "RAZORPAY_NOT_CONFIGURED"
        http.assert_not_called()
        assert not await razorpay_client.verify_payment_signature("order_local_old", "pay", "signature")
        assert not await razorpay_client.verify_webhook_signature(b"{}", "signature")


@pytest.mark.asyncio
async def test_placeholder_order_is_rejected_even_after_test_keys_are_configured():
    import hashlib
    import hmac
    signature = hmac.new(b"secret", b"order_local_old|pay", hashlib.sha256).hexdigest()
    with patch.object(razorpay_client, "_resolve_credentials", AsyncMock(return_value=("rzp_test_key", "secret", "webhook"))):
        assert not await razorpay_client.verify_payment_signature("order_local_old", "pay", signature)
