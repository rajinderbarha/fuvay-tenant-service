# Staff/Technician Communication Policy

## Supported capabilities on this router
- Staff/technician self-service in-app notifications (read/mark-read).
- Staff/technician participation in job/booking/complaint-linked chat
  threads (list/get/messages/send/mark-read) via `staff_chat_router`.

Tenant-owner-to-staff direct messaging, staff-to-staff direct messaging (not
via a shared job thread), and tenant-wide announcements do NOT exist as
capabilities anywhere in this module — no route or service method
implements them. Classified `TECHNICIAN_NOT_SUPPORTED` /
`FALSE_POSITIVE_NON_MUTATION` (not applicable) rather than assumed absent.

## Technician assignment policy — chosen: TENANT_WIDE (unchanged), flagged PRODUCT_DECISION_REQUIRED for future restriction
`ChatThreadService.list_threads`'s provider/staff branch grants any
authorized tenant user (owner, staff, OR technician, since
`require_staff_or_technician_only` admits both) visibility into every
thread for their tenant — not filtered to threads where they are a listed
participant, and NOT filtered to jobs currently assigned to them.

This is a pre-existing, explicitly-commented design choice in
`chat_service.py` ("participant-only scoping made customer threads
invisible to the rest of the provider's team"). Workstream 10/19 asks for
technician access to be assignment/participant-limited "where genuinely
supported" — this module's current design is deliberately NOT
assignment-limited, and restricting it now would be a functional regression
without confirmed product sign-off (a technician reassigned mid-job
currently keeps seeing the existing thread; an assignment-limited version
would need an explicit decision on whether that access should be revoked
immediately on reassignment, kept permanently, or time-boxed).

**Chosen policy for this slice: preserve existing TENANT_WIDE behavior
unchanged, do not silently narrow it.** See `product-decisions-required.md`
for the specific question a future slice needs answered before this can be
tightened to `ASSIGNED_TECHNICIAN_ALLOWED` policy.

## Technicians may
- Start conversations (via `provider_create_thread`'s shared logic — same
  route serves both `provider_chat_router` and is mirrored in
  `staff_chat_router`, minus the `create`/`get_prefs` routes which
  `staff_notif_router` doesn't expose).

  Correction: `staff_chat_router` has NO `POST /threads` (create) route —
  only `provider_chat_router` does. A technician/staff user therefore
  cannot create a NEW thread via `/v1/staff/chat/*`; they can only reply
  within an existing thread (visible to them via the tenant-wide list) or
  via `/v1/provider/*` if their role also passes
  `require_owner_or_office_staff_mutation` (i.e., a `staff` role, but NOT a
  `technician` role, since that guard excludes technician). Net effect: a
  `technician` account can reply to, list, and mark-read existing
  tenant threads, but cannot create new ones from any surface in this
  router — `CONVERSATION_PARTICIPANT_ONLY` policy in practice for
  technicians specifically, `TENANT_WIDE_ANNOUNCEMENT_ALLOWED` is not
  applicable (no announcement capability exists).
- Reply to existing threads (`staff_send_message`).
- Add/remove participants: NOT SUPPORTED anywhere in this module (no route,
  no service method reachable from any router in this module).
