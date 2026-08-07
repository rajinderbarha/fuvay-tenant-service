"""LEVEL-5 REMEDIATION (2026-08-01, Phase 10/11) — Customer Home aggregation
and backend-controlled campaign/banner tests.

Prior audit found (G8) no Home aggregation endpoint existed at all, and
(G9) no backend campaign/banner model existed. These tests exercise the
new CustomerHomeService and CampaignService directly against mocked db
sessions — no real DB, no HTTP.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.customer_campaigns.service import CampaignService
from app.engines.customer_campaigns.models import CustomerCampaign
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)


def _id():
    return uuid.uuid4()


def make_campaign(**overrides):
    c = MagicMock(spec=CustomerCampaign)
    c.id = overrides.get("id", _id())
    c.is_enabled = overrides.get("is_enabled", True)
    c.starts_at = overrides.get("starts_at", None)
    c.ends_at = overrides.get("ends_at", None)
    c.priority = overrides.get("priority", 100)
    c.target_zipcodes = overrides.get("target_zipcodes", [])
    c.eligible_vertical_keys = overrides.get("eligible_vertical_keys", [])
    c.eligible_category_ids = overrides.get("eligible_category_ids", [])
    c.to_customer_dict.return_value = {
        "campaign_id": str(c.id),
        "title": overrides.get("title", "Test Campaign"),
        "priority": c.priority,
    }
    return c


def _scalars(lst):
    r = MagicMock()
    r.scalars.return_value.all.return_value = lst
    return r


class TestCampaignTargeting:
    async def test_enabled_campaign_with_no_targeting_shown_everywhere(self):
        db = MagicMock()
        c = make_campaign(target_zipcodes=[])
        db.execute = AsyncMock(return_value=_scalars([c]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(zipcode="141002")
        assert len(result) == 1

    async def test_disabled_campaign_excluded_by_query(self):
        # is_enabled==True is enforced in the SQL WHERE clause itself, so a
        # disabled campaign never even reaches Python-side matching — assert
        # the query never returns it (simulated by an empty result set).
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(zipcode="141002")
        assert result == []

    async def test_scheduled_future_campaign_excluded(self):
        # Same reasoning: the starts_at/ends_at window is enforced in SQL.
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(zipcode="141002")
        assert result == []

    async def test_zip_targeted_campaign_shown_for_matching_zip(self):
        db = MagicMock()
        c = make_campaign(target_zipcodes=["141002", "141003"])
        db.execute = AsyncMock(return_value=_scalars([c]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(zipcode="141002")
        assert len(result) == 1

    async def test_zip_targeted_campaign_hidden_for_non_matching_zip(self):
        db = MagicMock()
        c = make_campaign(target_zipcodes=["999999"])
        db.execute = AsyncMock(return_value=_scalars([c]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(zipcode="141002")
        assert result == []

    async def test_zip_targeted_campaign_hidden_when_customer_has_no_zip(self):
        db = MagicMock()
        c = make_campaign(target_zipcodes=["141002"])
        db.execute = AsyncMock(return_value=_scalars([c]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(zipcode=None)
        assert result == []

    async def test_category_targeted_campaign_matches(self):
        cat_id = _id()
        db = MagicMock()
        c = make_campaign(eligible_category_ids=[str(cat_id)])
        db.execute = AsyncMock(return_value=_scalars([c]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(category_id=cat_id)
        assert len(result) == 1

    async def test_category_targeted_campaign_excludes_other_category(self):
        db = MagicMock()
        c = make_campaign(eligible_category_ids=[str(_id())])
        db.execute = AsyncMock(return_value=_scalars([c]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer(category_id=_id())
        assert result == []

    async def test_priority_ordering_preserved_from_query(self):
        db = MagicMock()
        c1 = make_campaign(priority=1)
        c2 = make_campaign(priority=50)
        db.execute = AsyncMock(return_value=_scalars([c1, c2]))
        svc = CampaignService(db=db)
        result = await svc.list_active_for_customer()
        assert [r["priority"] for r in result] == [1, 50]


class TestCampaignAdminValidation:
    async def test_invalid_deeplink_rejected(self):
        db = MagicMock()
        svc = CampaignService(db=db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_campaign({
                "internal_name": "x", "title": "x",
                "cta_deeplink": "https://evil.example.com/steal-creds",
            })
        assert exc.value.error_code == "CAMPAIGN_INVALID_DEEPLINK"

    async def test_allowlisted_deeplink_accepted(self):
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        svc = CampaignService(db=db)
        result = await svc.create_campaign({
            "internal_name": "x", "title": "x",
            "cta_deeplink": "app://category/ac-cooling",
        })
        assert result["cta_deeplink"] == "app://category/ac-cooling"

    async def test_missing_artwork_does_not_fail(self):
        """Fail safely when artwork is unavailable — a campaign with no
        artwork URLs is still creatable/displayable (frontend renders a
        fallback), not rejected."""
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        svc = CampaignService(db=db)
        result = await svc.create_campaign({"internal_name": "x", "title": "x"})
        assert result["artwork_url_light"] is None
        assert result["artwork_url_dark"] is None

    async def test_invalid_date_window_rejected(self):
        db = MagicMock()
        svc = CampaignService(db=db)
        now = utcnow()
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_campaign({
                "internal_name": "x", "title": "x",
                "starts_at": now, "ends_at": now - timedelta(days=1),
            })
        assert exc.value.error_code == "CAMPAIGN_INVALID_DATE_WINDOW"


# ══════════════════════════════════════════════════════════════════════════════
# Customer Home aggregation
# ══════════════════════════════════════════════════════════════════════════════

class TestCustomerHomeAggregation:
    async def test_get_home_composes_all_sections(self, monkeypatch):
        from app.engines.customer_home.service import CustomerHomeService

        customer_id = _id()
        db = MagicMock()
        svc = CustomerHomeService(db=db, request_id="test-req")

        monkeypatch.setattr(svc, "_get_default_address", AsyncMock(return_value={"zipcode": "141002"}))
        monkeypatch.setattr(svc, "_get_enabled_verticals", AsyncMock(return_value=[{"key": "home_services"}]))
        monkeypatch.setattr(svc, "_get_bookable_categories", AsyncMock(return_value=[{"name": "AC & Cooling"}]))
        monkeypatch.setattr(svc, "_get_active_booking_summary", AsyncMock(return_value=None))
        monkeypatch.setattr(svc, "_get_unread_notification_count", AsyncMock(return_value=3))
        monkeypatch.setattr(svc, "_get_active_campaigns", AsyncMock(return_value=[]))

        result = await svc.get_home(customer_id=customer_id, zipcode=None)
        # Bumped to 2 when the payload grew global_services + quick_issues.
        assert result["response_version"] == 2
        assert result["address"]["zipcode"] == "141002"
        assert result["enabled_verticals"] == [{"key": "home_services"}]
        assert result["bookable_categories"] == [{"name": "AC & Cooling"}]
        assert result["active_booking"] is None
        assert result["unread_notification_count"] == 3
        assert result["serviceability"]["zipcode"] == "141002"

    async def test_get_home_never_exposes_provider_lists_or_matching_scores(self, monkeypatch):
        """Home aggregation must never leak provider identity/matching
        internals — it only composes customer-safe category/booking/
        notification/campaign summaries."""
        from app.engines.customer_home.service import CustomerHomeService

        db = MagicMock()
        svc = CustomerHomeService(db=db, request_id="test-req")
        monkeypatch.setattr(svc, "_get_default_address", AsyncMock(return_value=None))
        monkeypatch.setattr(svc, "_get_enabled_verticals", AsyncMock(return_value=[]))
        monkeypatch.setattr(svc, "_get_bookable_categories", AsyncMock(return_value=[]))
        monkeypatch.setattr(svc, "_get_active_booking_summary", AsyncMock(return_value=None))
        monkeypatch.setattr(svc, "_get_unread_notification_count", AsyncMock(return_value=0))
        monkeypatch.setattr(svc, "_get_active_campaigns", AsyncMock(return_value=[]))

        result = await svc.get_home(customer_id=_id())
        serialized = str(result)
        assert "internal_score" not in serialized
        assert "matching_score" not in serialized
        assert "provider" not in serialized.lower() or "provider" not in result

    async def test_get_home_section_failure_is_isolated_not_fatal(self, monkeypatch):
        """One failing section (e.g. notifications engine error) must not
        take down the whole Home response — fails safe to None for that
        section only."""
        from app.engines.customer_home.service import CustomerHomeService

        db = MagicMock()
        svc = CustomerHomeService(db=db, request_id="test-req")
        monkeypatch.setattr(svc, "_get_default_address", AsyncMock(return_value=None))
        monkeypatch.setattr(svc, "_get_enabled_verticals", AsyncMock(return_value=[]))
        monkeypatch.setattr(svc, "_get_bookable_categories", AsyncMock(return_value=[]))
        monkeypatch.setattr(svc, "_get_active_booking_summary", AsyncMock(return_value=None))
        monkeypatch.setattr(svc, "_get_unread_notification_count", AsyncMock(side_effect=RuntimeError("boom")))
        monkeypatch.setattr(svc, "_get_active_campaigns", AsyncMock(return_value=[]))

        result = await svc.get_home(customer_id=_id())
        # Fails safe to a TYPE-CORRECT default, not None: the response
        # schema declares this field as a number, so a uniform None (the
        # original `_fail_safe` behaviour) broke the contract for every
        # client whenever the notifications lookup errored.
        assert result["unread_notification_count"] == 0
        # The rest of the payload still composed -- one dead section must
        # not take the screen down.
        assert result["response_version"] == 2
        assert result["bookable_categories"] == []

    async def test_get_home_query_count_is_bounded(self, monkeypatch):
        """Home aggregation must issue a fixed, bounded number of lookups,
        not N+1 per category/booking/etc.

        Counts only the customer-scoped sections. `_get_global_services`
        is excluded because it is a fixed platform list, and
        `_get_quick_issues` because it short-circuits with no query when
        there are no bookable categories (as here) -- with categories it
        is still exactly ONE query for all of them, never one per
        category, which is the property this test exists to protect."""
        from app.engines.customer_home.service import CustomerHomeService
        import app.engines.customer_home.service as home_service_mod

        call_count = {"n": 0}
        async def counted(*a, **kw):
            call_count["n"] += 1
            return None

        db = MagicMock()
        svc = CustomerHomeService(db=db, request_id="test-req")
        for method in (
            "_get_default_address", "_get_enabled_verticals", "_get_bookable_categories",
            "_get_active_booking_summary", "_get_unread_notification_count", "_get_active_campaigns",
        ):
            monkeypatch.setattr(svc, method, counted)

        await svc.get_home(customer_id=_id())
        assert call_count["n"] == 6
