"""NOTIFICATION-CENTER-REBUILD: Logs & Failures tab backend.

Static source-inspection style (consistent with this repo's other Phase 3/4
notification tests). Covers:
  - cancel only allowed on pending records (not delivered/failed/skipped)
  - retry is idempotent -- never creates a duplicate outbox row, only
    flips the existing one back to pending
  - list/export support vertical_key and event_key filters
  - export route is registered before the {outbox_id} path param route
    (otherwise "export" would be parsed as a UUID and 422)
"""
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
NOTIF_SERVICE = os.path.join(ROOT, "app", "engines", "platform_notifications", "notification_service.py")
ADMIN_ROUTER = os.path.join(ROOT, "app", "engines", "platform_notifications", "admin_router.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestCancelOnlyAllowedWhenPending:
    def test_cancel_source_checks_delivery_status_is_pending(self):
        src = _read(NOTIF_SERVICE)
        idx = src.index("async def cancel_outbox")
        block = src[idx: idx + 400]
        assert "DELIVERY_PENDING" in block
        assert "ERR_NOTIF_RETRY_NOT_ALLOWED" in block

    def test_cancel_marks_skipped_not_a_new_status_enum(self):
        # Cancelled reuses DELIVERY_SKIPPED (with a distinguishing failure_code)
        # rather than inventing a new enum value requiring a migration.
        src = _read(NOTIF_SERVICE)
        idx = src.index("async def cancel_outbox")
        block = src[idx: idx + 400]
        assert "DELIVERY_SKIPPED" in block
        assert "CANCELLED_BY_ADMIN" in block


class TestRetryIsIdempotent:
    def test_retry_outbox_mutates_existing_row_never_inserts(self):
        src = _read(NOTIF_SERVICE)
        idx = src.index("async def retry_outbox")
        block = src[idx: idx + 500]
        assert "db.add(" not in block
        assert "outbox.retry_count += 1" in block
        assert "outbox.delivery_status = DELIVERY_PENDING" in block

    def test_retry_respects_max_retries(self):
        src = _read(NOTIF_SERVICE)
        idx = src.index("async def retry_outbox")
        block = src[idx: idx + 500]
        assert "outbox.retry_count >= outbox.max_retries" in block


class TestLogsFiltersAndExportRouting:
    def test_list_outbox_supports_vertical_and_event_key_filters(self):
        src = _read(NOTIF_SERVICE)
        idx = src.index("async def list_outbox")
        block = src[idx: idx + 1500]
        assert "vertical_key" in block
        assert "event_key" in block

    def test_export_route_registered_before_outbox_id_path_param(self):
        src = _read(ADMIN_ROUTER)
        export_idx = src.index('@admin_outbox_router.get("/export"')
        detail_idx = src.index('@admin_outbox_router.get("/{outbox_id}"')
        assert export_idx < detail_idx, (
            "GET /export must be registered before GET /{outbox_id} -- otherwise "
            "FastAPI parses 'export' as outbox_id and 422s on UUID validation"
        )

    def test_cancel_route_exists(self):
        src = _read(ADMIN_ROUTER)
        assert '"/{outbox_id}/cancel"' in src
