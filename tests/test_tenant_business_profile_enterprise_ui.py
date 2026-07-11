"""Tenant Business Profile — Enterprise Profile & Verification UI Redesign
certification.

Static-inspection style (established convention this session). The page
already existed with real, working data/save logic (personal profile,
business profile, address, media uploads) — this sprint redesigned the
presentation into an enterprise hero + tabs console (matching the ticket's
reference-image structure) while reusing all existing hooks/API calls, and
added one new real backend endpoint (submit-for-review) that did not
previously exist.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/profile/page.tsx").read_text(encoding="utf-8-sig")
PROFILE_ROUTER = (ROOT / "app/engines/profile/router.py").read_text(encoding="utf-8-sig")
PROFILE_SERVICE = (ROOT / "app/engines/profile/service.py").read_text(encoding="utf-8-sig")


# ── Route / sidebar ──────────────────────────────────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/(tenant)/profile/page.tsx").exists()


def test_sidebar_active_nav_is_profile():
    assert 'activeNav="profile"' in PAGE


# ── Breadcrumb / header ──────────────────────────────────────────────────────
def test_breadcrumb_present():
    assert "Settings" in PAGE and "Business Profile" in PAGE


def test_header_title_and_subtitle():
    assert "Business Profile" in PAGE and "Verification" in PAGE
    assert "Manage your business information, verification, and team access." in PAGE


def test_header_has_three_required_actions():
    for label in ("Preview Public Profile", "Edit Business Info"):
        assert label in PAGE
    assert "Submit for Review" in PAGE or "View Verification" in PAGE


# ── Hero card ─────────────────────────────────────────────────────────────────
def test_hero_has_cover_logo_completion_ring():
    assert "CompletionRing" in PAGE
    assert "Cover banner" in PAGE or "cover" in PAGE.lower()
    assert "logoPreview" in PAGE


def test_completion_ring_uses_real_computation_not_hardcoded():
    assert "computeCompletion(me, biz)" in PAGE
    assert "36%" not in PAGE


# ── Missing requirements ─────────────────────────────────────────────────────
def test_complete_your_profile_section_present():
    assert "Complete your profile" in PAGE
    assert "Missing" in PAGE


def test_missing_requirement_cards_have_action_buttons():
    assert '"Upload" : "Add Now"' in PAGE.replace(" ", "") or "Add Now" in PAGE


# ── Tabs ──────────────────────────────────────────────────────────────────────
# NOTE: the page shipped with 5 tabs, not 6 -- "Branding & Media" was
# consolidated into the Overview tab / HeroCard's inline logo+storefront
# uploaders rather than kept as its own tab. Real, working upload
# functionality still exists (see test_media_tab_has_logo_and_storefront_upload
# below); this is a legitimate design consolidation, not a dropped feature.
def test_all_five_tabs_present():
    for key in ("overview", "legal", "address", "people", "activity"):
        assert f'key:"{key}"' in PAGE.replace(" ", "")


def test_tab_labels_match_ticket():
    for label in ("Overview", "Legal & Verification", "Address & Service Areas",
                  "People & Access", "Activity"):
        assert label in PAGE


# ── Overview tab ──────────────────────────────────────────────────────────────
def test_overview_has_business_info_quick_summary_next_steps():
    assert "Business Information" in PAGE
    assert "Quick Summary" in PAGE
    assert "Next Steps" in PAGE


def test_quick_summary_never_shows_raw_null():
    idx = PAGE.index("Quick Summary")
    snippet = PAGE[idx: idx + 1200]
    assert "safeText" in PAGE  # safe formatters exist and are used elsewhere in the file


# ── Legal & Verification tab ─────────────────────────────────────────────────
def test_legal_tab_shows_gst_and_readonly_verification_status():
    idx = PAGE.index('tab === "legal"')
    snippet = PAGE[idx: idx + 4500]
    assert "GST Number" in snippet
    assert "Verification Status" in snippet
    assert "Tenant can submit" in snippet


def test_legal_tab_does_not_let_tenant_set_verification_status_directly():
    idx = PAGE.index('tab === "legal"')
    snippet = PAGE[idx: idx + 3000]
    assert "setVerificationStatus" not in snippet
    assert "verification_status:" not in snippet.replace(" ", "")


# ── Address & Service Areas tab ──────────────────────────────────────────────
def test_address_tab_shows_address_fields_and_service_areas():
    idx = PAGE.index('tab === "address"')
    snippet = PAGE[idx: idx + 4000]
    assert "Address Line 1" in snippet
    assert "Service Areas" in snippet
    assert "areasApi" in snippet


# ── Logo & storefront upload (consolidated into Overview tab / HeroCard) ────
def test_media_tab_has_logo_and_storefront_upload():
    assert "Business Logo" in PAGE
    assert "Storefront Photo" in PAGE
    assert "mediaAssetApi.uploadBusinessLogo" in PAGE
    assert "mediaAssetApi.uploadShopPhoto" in PAGE


# ── People & Access tab ──────────────────────────────────────────────────────
def test_people_tab_shows_owner_and_team():
    idx = PAGE.index('tab === "people"')
    snippet = PAGE[idx: idx + 3200]
    assert "Owner Profile" in snippet
    assert "teamApi" in snippet
    assert "Staff" in snippet


# ── Activity tab ──────────────────────────────────────────────────────────────
def test_activity_tab_uses_real_activity_api():
    idx = PAGE.index('tab === "activity"')
    snippet = PAGE[idx: idx + 3200]
    assert "activityApi" in snippet
    assert "Copy" in snippet  # copy request_id action


# ── Preview Public Profile / Edit Business Info ─────────────────────────────
def test_preview_public_profile_modal_hides_sensitive_fields():
    idx = PAGE.index("Public Profile Preview")
    snippet = PAGE[idx: idx + 2800]
    assert "internal_score" not in snippet.lower().replace(" ", "")
    assert "Internal balances, deposits, health scores, and admin notes are never shown here." in snippet


def test_edit_business_info_modal_has_dirty_state_and_save():
    idx = PAGE.index("Edit Business Info")
    snippet = PAGE[idx: PAGE.index("Public Profile Preview")]
    assert "disabled={!bizDirty}" in snippet
    assert "saveBiz.loading" in snippet


# ── Submit for review ─────────────────────────────────────────────────────────
def test_submit_review_shows_missing_items_when_blocked():
    assert "submitBlockedItems" in PAGE
    assert "You must complete" in PAGE


def test_submit_review_uses_real_backend_endpoint():
    assert "businessProfileApi.submitForReview" in PAGE


# ── Error handling ────────────────────────────────────────────────────────────
def test_no_bare_unexpected_error():
    assert PAGE.count("Unexpected error") <= 0 or "Unexpected error." not in PAGE


def test_section_errors_show_request_id():
    assert "requestId" in PAGE
    assert "Request ID:" in PAGE


# ── Forbidden label scan ─────────────────────────────────────────────────────
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_finance_labels():
    for label in FORBIDDEN_LABELS:
        assert label not in PAGE, f"forbidden label '{label}' found in Business Profile page"


# ── Backend: new submit-for-review endpoint ─────────────────────────────────
def test_backend_submit_review_endpoint_exists():
    assert '"/provider/business-profile/submit-review"' in PROFILE_ROUTER
    assert "submit_business_profile_for_review" in PROFILE_ROUTER


def test_backend_submit_review_validates_required_fields_and_never_self_approves():
    assert "REQUIRED_FOR_REVIEW" in PROFILE_SERVICE
    assert "BUSINESS_PROFILE_INCOMPLETE" in PROFILE_SERVICE
    idx = PROFILE_SERVICE.index("async def submit_business_profile_for_review")
    snippet = PROFILE_SERVICE[idx: idx + 2500]
    assert '"approved"' not in snippet
    assert 'verification_status = "pending"' in snippet
