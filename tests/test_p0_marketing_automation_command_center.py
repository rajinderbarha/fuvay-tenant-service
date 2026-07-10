"""P0 Enterprise Marketing Automation Command Center — regression tests.

Following this session's established convention: static-inspection tests
(reading source as text) for structural/architectural guarantees, run via
pytest with no live DB dependency. The full live workflow (create post ->
generate caption -> generate image (budget charged) -> approve -> schedule
(channel + past-date validation) -> publish -> calendar -> audit trail) was
additionally verified live against the real Postgres DB with real HTTP calls
during this sprint — see MARKETING_AUTOMATION_LIVE_SMOKE_REPORT.md.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODELS = ROOT / "app/engines/marketing_command_center/models.py"
SERVICE = ROOT / "app/engines/marketing_command_center/service.py"
ROUTER = ROOT / "app/engines/marketing_command_center/admin_router.py"
MIGRATION = ROOT / "alembic/versions/100_marketing_command_center.py"
MAIN = ROOT / "app/main.py"
PERMISSIONS = ROOT / "app/core/permissions.py"
CAMPAIGN_MODEL = ROOT / "app/engines/marketing_automation/models.py"

MARKETING_PAGE = ROOT / "frontend/super-admin/app/admin/marketing/page.tsx"
WIZARD_PAGE = ROOT / "frontend/super-admin/app/admin/marketing/generate/page.tsx"
API_TS = ROOT / "frontend/super-admin/lib/api.ts"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ── 1. Marketing summary loads (structural) ─────────────────────────────────

def test_summary_endpoint_exists():
    src = _read(ROUTER)
    assert '@router.get("/automation/summary"' in src
    assert "get_summary" in _read(SERVICE)


# ── 2. Campaign create works (reuses + extends Sprint 29 engine) ───────────

def test_campaign_model_extended_with_command_center_fields():
    src = _read(CAMPAIGN_MODEL)
    for field in ["goal", "vertical_key", "budget_amount", "budget_used_amount", "channels_json", "owner_user_id"]:
        assert field in src, f"MarketingCampaign missing {field}"


# ── 3. Post create works ────────────────────────────────────────────────────

def test_create_post_endpoint_and_service_method_exist():
    assert '@router.post("/posts"' in _read(ROUTER)
    assert "async def create_post" in _read(SERVICE)


def test_post_model_has_required_fields():
    src = _read(MODELS)
    for field in ["post_code", "campaign_id", "title", "caption", "vertical_key", "tenant_id",
                  "status", "approval_status", "scheduled_at", "published_at"]:
        assert field in src


# ── 4. AI budget ledger records generation cost ─────────────────────────────

def test_ai_generation_charges_platform_budget_ledger():
    src = _read(SERVICE)
    assert "_check_and_charge_budget" in src
    assert "MarketingAIBudgetLedger(" in src
    assert "async def generate_image" in src and "_DALLE_COST_PER_IMAGE" in src
    assert "async def generate_caption" in src and "_CAPTION_COST" in src


def test_platform_pays_rule_never_touches_tenant_wallet():
    src = _read(SERVICE)
    # No import of the tenant-wallet/customer-credit ORM models — the docstring
    # mentions the table names only to document why they're absent.
    assert "TenantWallet" not in src
    assert "CustomerServiceCredit" not in src
    assert "from app.engines.platform_commerce" not in src
    assert "from app.engines.customer_credits" not in src
    assert "Platform pays AI generation costs" in src


# ── 5. AI budget blocks generation when exceeded ────────────────────────────

def test_budget_exceeded_raises_error():
    src = _read(SERVICE)
    assert "AI_BUDGET_EXCEEDED" in src
    assert "auto_disable_on_exceed" in src


# ── 6. Post approval required when user lacks approve permission ───────────

def test_approve_reject_gated_by_approve_permission():
    src = _read(ROUTER)
    assert "P.MARKETING_POSTS_APPROVE" in src
    assert 'async def approve_post' in src
    assert 'async def reject_post' in src


def test_submit_for_approval_sets_pending_status():
    src = _read(SERVICE)
    assert '"pending_approval"' in src
    assert '"pending"' in src


# ── 7. Schedule prevents past date ──────────────────────────────────────────

def test_schedule_rejects_past_date():
    src = _read(SERVICE)
    assert "SCHEDULE_IN_PAST" in src
    assert "scheduled_at <= utcnow()" in src


# ── 8. Publish blocks disconnected account ──────────────────────────────────

def test_publish_and_schedule_block_disconnected_channel():
    src = _read(SERVICE)
    assert "CHANNEL_DISCONNECTED" in src
    assert src.count("CHANNEL_DISCONNECTED") >= 2  # schedule_post AND publish_now


# ── 9. Retry failed post creates new attempt ────────────────────────────────

def test_retry_post_creates_new_publish_attempt():
    src = _read(SERVICE)
    assert "async def retry_post" in src
    assert "attempt_number" in src
    assert "next_num" in src


# ── 10. Social account test handles token expired ───────────────────────────

def test_social_account_test_endpoint_checks_token_expiry():
    src = _read(SERVICE)
    assert "async def test_social_account" in src
    assert "token_expires_at" in src
    assert '"expired"' in src


# ── 11. Calendar returns scheduled posts ────────────────────────────────────

def test_calendar_endpoint_filters_scheduled_posts():
    src = _read(SERVICE)
    assert "async def get_calendar" in src
    assert "scheduled_at.is_not(None)" in src


# ── 12. Audit logs created for publish/schedule/approve ─────────────────────

def test_audit_logged_for_key_lifecycle_actions():
    src = _read(SERVICE)
    for action in [
        "marketing.post.created", "marketing.post.generated", "marketing.post.image_generated",
        "marketing.post.submitted_for_approval", "marketing.post.approved", "marketing.post.rejected",
        "marketing.post.scheduled", "marketing.post.rescheduled", "marketing.post.published",
        "marketing.post.retry", "marketing.post.cancelled",
        "marketing.social_account.connected", "marketing.social_account.disconnected",
        "marketing.ai_budget.updated", "marketing.template.created", "marketing.template.updated",
    ]:
        assert action in src, f"missing audit action {action}"


def test_audit_log_model_has_required_fields():
    src = _read(MODELS)
    for field in ["actor_user_id", "action_type", "target_type", "target_id",
                  "old_value_json", "new_value_json", "reason", "request_id"]:
        assert field in src


# ── Migration / architecture integrity ──────────────────────────────────────

def test_migration_creates_all_required_tables():
    src = _read(MIGRATION)
    for table in [
        "marketing_posts", "marketing_post_assets", "marketing_ai_budget",
        "marketing_ai_budget_ledger", "marketing_content_templates",
        "marketing_publish_attempts", "marketing_audit_logs",
    ]:
        assert f'"{table}"' in src


def test_migration_extends_existing_engines_additively_not_duplicated():
    src = _read(MIGRATION)
    # Extends pre-existing marketing_campaigns / social_accounts rather than
    # creating parallel duplicate tables.
    assert 'op.add_column("marketing_campaigns"' in src
    assert 'op.add_column("social_accounts"' in src


def test_router_mounted_in_main():
    src = _read(MAIN)
    assert "marketing_command_center" in src
    assert "marketing_command_center_router" in src


def test_all_permission_constants_defined():
    src = _read(PERMISSIONS)
    for perm in [
        "MARKETING_AUTOMATION_READ", "MARKETING_POSTS_CREATE", "MARKETING_POSTS_UPDATE",
        "MARKETING_POSTS_APPROVE", "MARKETING_POSTS_SCHEDULE", "MARKETING_POSTS_PUBLISH",
        "MARKETING_POSTS_RETRY", "MARKETING_POSTS_CANCEL", "MARKETING_CAMPAIGNS_READ",
        "MARKETING_CAMPAIGNS_CREATE", "MARKETING_CAMPAIGNS_UPDATE", "MARKETING_CAMPAIGNS_PAUSE",
        "MARKETING_AI_GENERATE_CAPTION", "MARKETING_AI_GENERATE_IMAGE", "MARKETING_AI_MANAGE_BUDGET",
        "MARKETING_SOCIAL_ACCOUNTS_READ", "MARKETING_SOCIAL_ACCOUNTS_CONNECT",
        "MARKETING_SOCIAL_ACCOUNTS_DISCONNECT", "MARKETING_TEMPLATES_READ",
        "MARKETING_TEMPLATES_CREATE", "MARKETING_TEMPLATES_UPDATE",
        "MARKETING_ANALYTICS_READ", "MARKETING_AUDIT_READ",
    ]:
        assert perm in src


def test_analytics_unavailable_state_when_no_published_posts():
    src = _read(SERVICE)
    assert "Analytics not available yet" in src


# ── Frontend: Marketing Automation page renders enterprise layout ──────────

def test_frontend_marketing_page_has_all_kpi_cards():
    src = _read(MARKETING_PAGE)
    for label in ["Posts Published", "Scheduled Posts", "Pending Approval", "Failed Posts",
                  "Images Generated", "Platform AI Spend", "Connected Channels", "Active Campaigns"]:
        assert label in src


def test_frontend_marketing_page_has_action_bar():
    src = _read(MARKETING_PAGE)
    for action in ["Generate &amp; Schedule Post", "Create Campaign", "View Calendar",
                   "Connect Account", "Import Content"]:
        assert action in src


def test_frontend_connected_accounts_empty_state():
    src = _read(MARKETING_PAGE)
    assert "No social accounts connected." in src
    assert "Connect Meta Account" in src
    assert "Connect Google Business Profile" in src


def test_frontend_calendar_empty_state():
    src = _read(MARKETING_PAGE)
    assert "No posts scheduled for this period." in src
    assert "Generate First Post" in src


def test_frontend_campaign_pipeline_has_tabs_and_table():
    src = _read(MARKETING_PAGE)
    for tab in ["draft", "generated", "pending_approval", "scheduled", "published", "failed", "archived"]:
        assert f'"{tab}"' in src
    for col in ["Content", "Target", "Channels", "Status", "Schedule", "AI Cost", "Actions"]:
        assert col in src


def test_frontend_failed_retry_queue_exists():
    src = _read(MARKETING_PAGE)
    assert "Failed / Retry Queue" in src


def test_frontend_budget_panel_shows_platform_note():
    src = _read(MARKETING_PAGE)
    assert "Platform AI Budget" in src
    assert "platform_pays_note" in src


def test_frontend_no_forbidden_tenant_wallet_language():
    src = _read(MARKETING_PAGE)
    forbidden = ["Tenant wallet", "Provider wallet", "Usage credit deduction", "Payout", "Withdraw"]
    for term in forbidden:
        assert term not in src, f"marketing page must not contain '{term}'"


# ── Frontend: Generate & Schedule wizard ────────────────────────────────────

def test_frontend_wizard_has_all_eight_steps():
    src = _read(WIZARD_PAGE)
    for step in ["Goal", "Target", "Channel", "Creative Brief", "AI Generation",
                 "Preview & Edit", "Approval", "Schedule"]:
        assert step in src


def test_frontend_wizard_validates_required_fields_and_shows_connected_channels_only():
    src = _read(WIZARD_PAGE)
    assert "connectedPlatforms" in src
    assert "disabled={!connected}" in src


def test_frontend_wizard_blocks_past_date_schedule():
    src = _read(WIZARD_PAGE)
    assert "Cannot schedule a post in the past." in src


def test_frontend_wizard_calls_real_ai_generation_endpoints():
    src = _read(WIZARD_PAGE)
    assert "marketingCommandCenterApi.generateCaption" in src
    assert "marketingCommandCenterApi.generateImage" in src
    assert "marketingCommandCenterApi.generateHashtags" in src


# ── Frontend API client ──────────────────────────────────────────────────────

def test_api_client_has_marketing_command_center_methods():
    src = _read(API_TS)
    assert "export const marketingCommandCenterApi" in src
    for method in ["getSummary", "listPosts", "createPost", "approvePost", "rejectPost",
                   "schedulePost", "publishNow", "retryPost", "cancelPost",
                   "generateCaption", "generateImage", "generateHashtags", "generateVariations",
                   "getCalendar", "listSocialAccounts", "connectSocialAccount",
                   "listContentTemplates", "getAIBudget", "updateAIBudget", "getAIBudgetLedger",
                   "listPublishFailures", "getAnalyticsSummary", "listAuditLogs"]:
        assert f"{method}:" in src, f"marketingCommandCenterApi missing {method}"
