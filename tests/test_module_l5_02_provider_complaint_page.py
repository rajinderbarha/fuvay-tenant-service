"""MODULE-L5-02 bug #33, superseded: the provider complaint pages now redirect.

Bug #33 was a dead 404 at /provider/complaints/{id}. That page was later built,
but it drifted from the Complaints & Resolution Center in the sidebar: no
resolution deadlines, a "reassign provider" remedy the engine never modelled,
and money-based settlements that paid the customer nothing. Every provider
notification linked to it, so providers worked the stale copy. Both old routes
now redirect into /home-services/complaints, keeping existing links alive.
"""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
PAGE = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)",
                    "provider", "complaints", "[complaint_id]", "page.tsx")
LIST = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)",
                    "provider", "complaints", "page.tsx")


def test_old_detail_link_still_resolves_to_the_case():
    """Old bookmarks and notifications must still open the right case."""
    src = open(PAGE, encoding="utf-8").read()
    assert "router.replace" in src
    assert "/home-services/complaints/${id}" in src


def test_old_list_redirects_to_the_resolution_center():
    src = open(LIST, encoding="utf-8").read()
    assert 'router.replace("/home-services/complaints")' in src


def test_old_pages_no_longer_offer_settlements_or_unmodelled_remedies():
    for path in (PAGE, LIST):
        src = open(path, encoding="utf-8").read()
        assert "/settlement-proposals" not in src
        assert "provider_reassignment" not in src
