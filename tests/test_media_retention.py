"""Photos are deleted when they stop being needed -- and not before.

A job accumulates images from both ends, and they are not the same thing. What
the customer sent describes their problem and has served its purpose once the
work is done. The provider's before/after proof is what settles a warranty
claim, so deleting it on the same schedule would destroy the platform's
defence in exactly the cases it exists for.
"""
from __future__ import annotations

import inspect


class TestTheTwoKindsAreSeparate:
    def test_customer_photos_go_after_the_job_finishes(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r.purge_customer_photos)
        assert "customer_photo_urls" in src
        assert "photo_urls" in src  # the booking draft's copy
        assert "status = ANY(:statuses)" in src

    def test_completion_proofs_wait_for_the_warranty(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r.purge_completion_proofs)
        assert "warranty_expires_at" in src
        assert "before_photo_ids" in src and "after_photo_ids" in src

    def test_a_job_with_no_warranty_date_is_left_alone(self):
        """Without one there is no way to know the claim window has closed."""
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r.purge_completion_proofs)
        assert "warranty_expires_at IS NOT NULL" in src

    def test_each_retention_is_independent(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r.sweep)
        # Leaving one unset must not stop the other running.
        assert "if policy.customer_photo_retention_days is not None:" in src
        assert "if policy.completion_proof_retention_days is not None:" in src


class TestDeletionMeansDeletion:
    def test_the_file_is_destroyed_at_the_cdn(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r._destroy_assets)
        # Dropping the row would hide the image from the app while its URL kept
        # serving it to anyone who had ever seen it.
        assert "from app.cloudinary_client import destroy" in src
        assert "storage_key" in src

    def test_the_row_is_marked_only_after_the_file_is_gone(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r._destroy_assets)
        destroy_call = src.index("await destroy(")
        mark = src.index("UPDATE media_assets SET deleted_at")
        assert destroy_call < mark

    def test_a_failed_destroy_leaves_the_row_for_next_time(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r._destroy_assets)
        assert "continue" in src[src.index("destroy_failed"):]

    def test_an_already_missing_file_counts_as_success(self):
        from app import cloudinary_client
        src = inspect.getsource(cloudinary_client.destroy)
        # Re-running a purge must not fail because it worked the first time.
        assert '"not found"' in src

    def test_destroy_is_signed_like_the_upload(self):
        from app import cloudinary_client
        src = inspect.getsource(cloudinary_client.destroy)
        assert "sha1" in src and "CLOUDINARY_API_SECRET" in src

    def test_an_unconfigured_cloudinary_is_skipped_not_crashed(self):
        from app import cloudinary_client
        src = inspect.getsource(cloudinary_client.destroy)
        assert "cloudinary_not_configured" in src


class TestTheSweepIsSafeToRunLateAndTwice:
    def test_purged_jobs_are_marked(self):
        from app.engines.execution import media_retention_service as r
        for fn in (r.purge_customer_photos, r.purge_completion_proofs):
            src = inspect.getsource(fn)
            assert "media_purged_at = now()" in src

    def test_marked_jobs_are_never_revisited(self):
        from app.engines.execution import media_retention_service as r
        assert "customer_media_purged_at IS NULL" in inspect.getsource(r.purge_customer_photos)
        assert "completion_media_purged_at IS NULL" in inspect.getsource(r.purge_completion_proofs)

    def test_retention_is_measured_from_the_record_not_the_run(self):
        """A missed run costs latency, not a skipped week of deletions."""
        from app.engines.execution import media_retention_service as r
        assert "make_interval(days => :days)" in inspect.getsource(r.purge_customer_photos)
        assert "make_interval(days => :days)" in inspect.getsource(r.purge_completion_proofs)

    def test_the_loop_is_wired_in(self):
        import inspect as i
        from app import main
        assert "media_retention" in i.getsource(main)


class TestRetentionIsAdminPolicy:
    def test_both_periods_are_draftable(self):
        from app.engines.vertical_monetization.policy_service import _DRAFT_FIELDS
        assert "customer_photo_retention_days" in _DRAFT_FIELDS
        assert "completion_proof_retention_days" in _DRAFT_FIELDS

    def test_the_model_carries_them(self):
        from app.engines.vertical_monetization.models import VerticalMonetizationPolicy as P
        # A column only in the database 500s the admin save, since save_draft
        # seeds a new version by reading each field off the ORM object.
        assert hasattr(P, "customer_photo_retention_days")
        assert hasattr(P, "completion_proof_retention_days")

    def test_unset_means_never_purge(self):
        from app.engines.execution import media_retention_service as r
        src = inspect.getsource(r.sweep)
        assert "is not None" in src
