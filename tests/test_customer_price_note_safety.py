"""Customer chat must not expose internal tenant-pricing rule identifiers."""

import inspect


def test_tenant_price_note_does_not_expose_internal_source_codes():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    source = inspect.getsource(HomeServiceChatbotBookingService._compute_price_snapshot)

    assert "Price set by the selected service provider." in source
    assert 'tenant_price["source"]' not in source
    assert "tenant_price['source']" not in source


def test_shared_chat_flow_only_renders_customer_facing_price_fields():
    """Instagram and WhatsApp both use this shared matching step."""
    from app.engines.messaging_gateway import flow

    source = inspect.getsource(flow._match_step)

    assert 'price[\'display_price\']' in source
    assert 'price["source"]' not in source
    assert "price['source']" not in source
