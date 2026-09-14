"""Catalog Workspace exposes separate Cloudinary artwork only for problems."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend/super-admin/app/admin/catalog-workspace/page.tsx").read_text(encoding="utf-8-sig")
API = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8-sig")
SERVICE = (ROOT / "app/engines/admin_catalog/service_option_service.py").read_text(encoding="utf-8-sig")
SOCIAL = (ROOT / "app/engines/ai_conversation/backend_tools.py").read_text(encoding="utf-8-sig")


def test_mapped_problems_have_a_visible_dual_artwork_editor():
    problems = PAGE.split("function ProblemsSubTab", 1)[1].split("function ChecklistTab", 1)[0]
    assert "Manage images" in problems
    assert 'label="Fuvay app icon"' in problems
    assert 'context="issue_type_image"' in problems
    assert 'label="Instagram card image"' in problems
    assert 'context="instagram_card_image"' in problems
    assert "Save images" in problems
    assert "catalogWorkspaceApi.updateIssueType" in problems
    assert "icon_url: artworkEditor.iconUrl" in problems
    assert "image_url: artworkEditor.instagramImageUrl" in problems


def test_questions_remain_text_only_without_artwork_controls():
    questions = PAGE.split("function QuestionsSubTab", 1)[1].split("function TenantSetupRulesTab", 1)[0]
    assert "IconPicker" not in questions
    assert "Manage images" not in questions
    assert "instagram_card_image" not in questions


def test_problem_artwork_write_is_cloudinary_guarded_and_channel_separated():
    assert "updateIssueType: (issueTypeId" in API
    update = SERVICE.split("async def update_issue_type", 1)[1].split("async def _set_issue_status", 1)[0]
    assert 'for field in ("icon_url", "image_url")' in update
    assert "cloudinary_catalog_url(body[field], field)" in update
    assert 'self.channel == "instagram"' in SOCIAL
    assert 'getattr(r, "image_url", None)' in SOCIAL
    assert 'getattr(r, "icon_url", None)' in SOCIAL
