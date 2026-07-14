"""MODULE-L5-02 bugs #34/#35 — the customer complaint surface that never existed."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP  = os.path.join(ROOT, "frontend", "customer-app")
LIST = os.path.join(APP, "app", "customer", "complaints", "page.tsx")
DETAIL = os.path.join(APP, "app", "customer", "complaints", "[complaintId]", "page.tsx")
API  = os.path.join(APP, "lib", "api", "customer-complaints.ts")
BOOKING = os.path.join(APP, "app", "customer", "bookings", "[bookingId]", "page.tsx")


def test_customer_complaint_pages_exist():
    """The customer app had NO complaint surface at all — not one reference to
    'complaint'. The person who actually FILES a complaint could not file one,
    read it, accept/reject a resolution, request a refund, or answer a settlement
    proposal, though every endpoint existed and worked."""
    for p in (LIST, DETAIL, API):
        assert os.path.isfile(p), p


def test_customer_can_reach_the_repaired_flows():
    src = open(DETAIL, encoding="utf-8").read()
    for fn in ("acceptResolution", "rejectResolution", "requestRefund",
               "respondToSettlement", "getComplaintResolutions"):
        assert fn in src, fn
    # bug #30 must be communicated: a settlement needs BOTH parties
    assert "both you and the provider" in src


def test_customer_resolutions_endpoint_exists():
    """Bug #35: the customer had accept/reject endpoints for a resolution but NO
    endpoint to list resolutions — so they could never see what was offered nor
    obtain the resolution_id those endpoints require."""
    router = open(os.path.join(ROOT, "app", "engines", "complaints",
                               "customer_router.py"), encoding="utf-8").read()
    assert '@customer_complaint_router.get("/{complaint_id}/resolutions")' in router
    assert "list_resolutions" in router


def test_booking_page_links_to_raise_a_complaint():
    """A complaint surface nobody can reach is still no surface."""
    src = open(BOOKING, encoding="utf-8").read()
    assert "/customer/complaints?record_type=" in src
