"""MODULE-L5-02 bug #33 — the provider complaint detail page that never existed."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
PAGE = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)",
                    "provider", "complaints", "[complaint_id]", "page.tsx")
LIST = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)",
                    "provider", "complaints", "page.tsx")


def test_provider_complaint_detail_page_exists():
    """The complaints list has always had a 'View & Respond' row action linking
    to /provider/complaints/{id}, but the page did not exist — a dead 404. So the
    entire provider-facing complaint workflow (respond / offer resolution /
    settlement exchange) had no UI, despite every endpoint behind it existing."""
    assert os.path.isfile(PAGE), "provider complaint detail page is missing"


def test_list_row_action_target_now_resolves():
    src = open(LIST, encoding="utf-8").read()
    assert "/provider/complaints/${row.id}" in src
    assert os.path.isfile(PAGE)


def test_detail_page_wires_the_repaired_provider_flows():
    """It must drive the endpoints fixed in bugs #27/#28/#30."""
    src = open(PAGE, encoding="utf-8").read()
    for endpoint in (
        "/v1/provider/complaints/${id}",
        "/messages",
        "/respond",
        "/resolutions",
        "/offer-resolution",
        "/settlement-proposals",
    ):
        assert endpoint in src, endpoint
    # settlement must be presented as requiring BOTH parties (bug #30)
    assert "BOTH" in src
