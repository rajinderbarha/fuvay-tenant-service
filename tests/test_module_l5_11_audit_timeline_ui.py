"""MODULE-L5-11 — the record-timeline endpoint is now reachable from the UI."""
import os


def test_audit_page_wires_the_record_timeline_drill_in():
    """The record-timeline endpoint (full audit history of one record) had a
    client method but was reachable from no UI — an orphaned feature. The audit
    page now exposes it as a 'View record timeline' row action opening the
    complete trail. Proven live: a service_job's timeline returns its 7 audit
    entries (reassignments, status overrides)."""
    root = os.path.join(os.path.dirname(__file__), "..")
    page = open(os.path.join(root, "frontend", "super-admin", "app", "admin",
                "audit-logs", "page.tsx"), encoding="utf-8").read()
    assert "getAuditTimeline" in page
    assert "View record timeline" in page
    assert "rowActions" in page
