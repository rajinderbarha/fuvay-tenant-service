"""
MediaAccessService — permission checks for all media operations.

Rules:
- super_admin can view/manage anything
- tenant_owner/staff can manage media belonging to their tenant
- customer can manage own media only
- Private media always requires access check before serving
- Signed URLs only generated after permission check
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.dependencies.auth import UserContext
from app.exceptions import ServiceOSException

if TYPE_CHECKING:
    from app.engines.media.asset_service import MediaAssetRecord


# Contexts that belong to a customer (customer_id isolation)
CUSTOMER_CONTEXTS = {
    "customer_profile_photo",
    "customer_address_proof",
    "booking_issue_photo",
    "review_photo",
    "complaint_evidence",
    "chat_attachment",
}

# Contexts that require admin-only access to view
ADMIN_ONLY_VIEW_CONTEXTS: set[str] = set()  # extend as needed

# Contexts accessible to participants (job staff + customer + admin)
PARTICIPANT_CONTEXTS = {
    "job_before_photo",
    "job_after_photo",
    "checklist_photo",
    "quote_attachment",
    "chat_attachment",
}


class MediaAccessService:
    """
    Centralized access control for all media operations.
    Always call these before reading/writing/serving media.
    """

    def assert_can_upload(
        self,
        actor: UserContext,
        media_context: str,
        owner_type: str,
        owner_id: str,
    ) -> None:
        """Raise 403 if actor is not allowed to upload in this context."""
        if actor.role == "super_admin":
            return

        if media_context in CUSTOMER_CONTEXTS:
            if actor.role != "customer":
                raise ServiceOSException(
                    "MEDIA_CONTEXT_FORBIDDEN",
                    f"Only customers can upload to context '{media_context}'."
                )
            return

        if actor.role == "customer":
            allowed_customer = {"customer_profile_photo", "customer_address_proof",
                                "booking_issue_photo", "review_photo",
                                "complaint_evidence", "chat_attachment"}
            if media_context not in allowed_customer:
                raise ServiceOSException(
                    "MEDIA_CONTEXT_FORBIDDEN",
                    f"Customers are not allowed to upload to context '{media_context}'."
                )
            return

        # tenant_owner, staff, technician — must belong to same tenant
        if actor.role in ("tenant_owner", "staff", "technician"):
            if owner_type == "tenant" and owner_id != actor.tenant_id:
                raise ServiceOSException(
                    "MEDIA_TENANT_SCOPE_VIOLATION",
                    "Cannot upload media for another tenant."
                )
            return

        raise ServiceOSException("MEDIA_ACCESS_DENIED", "Upload not allowed for your role.")

    def assert_can_view(self, actor: UserContext, asset: "MediaAssetRecord") -> None:
        """Raise 403/404 if actor cannot view this media asset."""
        if actor.role == "super_admin":
            return

        # Public assets: anyone authenticated can view
        if asset.is_public:
            return

        # Customer-scoped: only owner or admin
        if asset.media_context in CUSTOMER_CONTEXTS:
            if actor.role == "customer":
                if str(asset.customer_id) != actor.user_id:
                    raise ServiceOSException(
                        "MEDIA_CUSTOMER_SCOPE_VIOLATION",
                        "You can only view your own media."
                    )
                return
            # tenant roles can view customer media in their own tenant
            if actor.role in ("tenant_owner", "staff", "technician"):
                if asset.tenant_id and str(asset.tenant_id) == actor.tenant_id:
                    return
            raise ServiceOSException("MEDIA_ACCESS_DENIED", "Access denied.")

        # Tenant-scoped: must be same tenant
        if asset.tenant_id:
            if actor.role in ("tenant_owner", "staff", "technician"):
                if str(asset.tenant_id) != actor.tenant_id:
                    raise ServiceOSException(
                        "MEDIA_TENANT_SCOPE_VIOLATION",
                        "You cannot access media from another tenant."
                    )
                return
            raise ServiceOSException("MEDIA_ACCESS_DENIED", "Access denied.")

        # Own media (uploaded_by)
        if str(asset.uploaded_by_user_id) == actor.user_id:
            return

        raise ServiceOSException("MEDIA_ACCESS_DENIED", "Access denied.")

    def assert_can_delete(self, actor: UserContext, asset: "MediaAssetRecord") -> None:
        """Raise 403 if actor cannot delete this media asset."""
        if actor.role == "super_admin":
            return
        self.assert_can_view(actor, asset)  # must be able to view to delete
        # Additional: customers can only delete their own
        if actor.role == "customer":
            if str(asset.uploaded_by_user_id) != actor.user_id:
                raise ServiceOSException("MEDIA_ACCESS_DENIED", "You can only delete your own media.")

    def assert_can_replace(self, actor: UserContext, asset: "MediaAssetRecord") -> None:
        """Raise 403 if actor cannot replace this media asset."""
        self.assert_can_delete(actor, asset)  # same rule as delete
