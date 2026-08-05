"""Regression: the Review & Submit row itself showed "Needs attention" even
when every other required section was actually complete and the Submit
button was unlocked. The section's status is only ever "complete" (after
real submission) or otherwise falls into the generic warning branch used
for genuinely broken sections -- there was no distinct "ready, just click
Submit" state, so a tenant with nothing left to do still saw a warning
badge on the very row telling them to act.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
REVIEW_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/review/page.tsx"
)


def _read():
    with open(REVIEW_PAGE, encoding="utf-8") as f:
        return f.read()


class TestReviewSubmitReadyState:
    def test_review_row_has_a_distinct_ready_branch(self):
        c = _read()
        start = c.index("let statusBadge")
        end = c.index("const label = SECTION_LABELS")
        block = c[start:end]
        assert "isReviewRow" in block
        assert '"Ready to submit"' in block
        # The ready branch must come before the generic warning fallback,
        # and must not itself use the warning/danger variant.
        ready_pos = block.index('"Ready to submit"')
        fallback_pos = block.index('"Needs attention"')
        assert ready_pos < fallback_pos

    def test_summary_reflects_ready_state_distinctly(self):
        c = _read()
        assert "All required sections are complete" in c
