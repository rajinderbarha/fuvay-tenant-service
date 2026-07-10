"""Service Setup Templates page — republish action + lucide-icon UI polish.

Static source-inspection tests verifying:
1. Archived templates can be republished (not just draft -> published).
2. All emoji/unicode glyphs were replaced with lucide-react icons.
"""
import os
import re

PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin", "app", "admin",
    "service-setup", "templates", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestRepublishAction:
    def test_archived_status_has_republish_button(self):
        src = _read(PAGE)
        assert 'Republish' in src
        assert 't.status === "archived"' in src

    def test_republish_calls_same_publish_handler(self):
        src = _read(PAGE)
        # Republish reuses onPublish (backend publish_template has no status guard).
        assert src.count("onClick={() => onPublish(t.id)}") >= 4  # 2x draft-publish + 2x archived-republish (grid+table)


class TestLucideIcons:
    def test_imports_lucide_icons(self):
        src = _read(PAGE)
        assert 'from "lucide-react"' in src
        for icon in ["Rocket", "Archive", "ArchiveRestore", "Copy", "Trash2", "FileEdit",
                     "CheckCircle2", "Sparkles", "Plus", "ExternalLink"]:
            assert icon in src

    def test_no_emoji_glyphs_remain(self):
        src = _read(PAGE)
        emoji_pattern = re.compile(
            "[\U0001F300-\U0001FAFF☀-➿]")
        matches = emoji_pattern.findall(src)
        assert not matches, f"Emoji/unicode glyphs still present: {matches}"

    def test_vertical_icon_helper_used_not_emoji_map(self):
        src = _read(PAGE)
        assert "VerticalIcon" in src
        assert "React.isValidElement" in src

    def test_status_badge_has_icon(self):
        src = _read(PAGE)
        assert "STATUS_META" in src
        assert "m.icon" in src


class TestTypeScript:
    def test_file_exists(self):
        assert os.path.exists(PAGE)
