"""MODULE-L5-02 bug #36 — the admin complaint detail page that never existed."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
SA   = os.path.join(ROOT, "frontend", "super-admin")
PAGE = os.path.join(SA, "app", "admin", "complaints", "[id]", "page.tsx")
LIST = os.path.join(SA, "app", "admin", "complaints", "page.tsx")
API  = os.path.join(SA, "lib", "api.ts")


def test_admin_complaint_detail_page_exists():
    """The complaints list has always had a row action navigating to
    /admin/complaints/{id} — but the page did not exist. A dead 404. So
    essentially the entire admin complaint API (triage, messaging, resolutions,
    settlement, AI settlement, resolve/close) had no UI at all."""
    assert os.path.isfile(PAGE)
    assert "/admin/complaints/${id}" in open(LIST, encoding="utf-8").read()


def test_admin_api_client_covers_the_detail_surface():
    src = open(API, encoding="utf-8").read()
    for fn in ("listMessages", "addMessage", "listResolutions", "proposeResolution",
               "setPriority", "requestProviderResponse", "adminResolve", "adminClose"):
        assert f"{fn}:" in src, fn


def test_page_drives_the_revived_ai_settlement():
    """Bugs #37/#38 revived the AI settlement engine; this page is the only place
    an admin can actually drive it."""
    src = open(PAGE, encoding="utf-8").read()
    for fn in ("startAISettlement", "getAISession", "finalizeSettlement"):
        assert fn in src, fn
    for field in ("ai_recommendation", "risk_flags", "confidence_score",
                  "customer_answers", "tenant_answers"):
        assert field in src, field
    # bug #30 must be stated: a settlement needs BOTH parties
    assert "BOTH" in src
