# Known Limitations

1. **Technician thread visibility remains tenant-wide, not
   assignment-limited.** Deliberately not changed this slice — see
   `product-decisions-required.md` item 1.

2. **`require_staff_or_technician_only` has no access-scope (readonly)
   check**, unlike `require_owner_or_office_staff_mutation`. This is the
   existing dependency's own design (confirmed by reading
   `app/dependencies/auth.py` — it is a role-only check), reused unchanged
   for consistency with `field_ops.staff_router`'s established convention.
   A staff/technician account with a readonly `access_scope` (if such a
   combination is ever created — currently `access_scope` is documented as
   a tenant-owner/staff concept, not typically applied to `technician`) is
   NOT denied by this specific guard. Not fixed here because inventing a
   new access-scope-aware technician guard was judged out of proportion
   for this slice — flagged for a future audit of `require_staff_or_technician_only`'s
   callers generally (it is used by `field_ops.staff_router` too, not
   introduced by this slice).

3. **Thread/message existence-vs-access error-code distinguishability** —
   see `product-decisions-required.md` item 2. No content leak, only an
   error-code difference.

4. **Media attachment ownership unvalidated** — see
   `product-decisions-required.md` item 3.

5. **No `ForeignKey()` DB constraints on any of the 8 models** — pre-existing,
   confirmed unchanged, out of scope (would require a migration, which is
   forbidden by this slice's constraints).

6. **`tenant_id` nullable on every model that has it** — pre-existing,
   confirmed the relevant access-control branches (`validate_thread_access`)
   fail closed when either side is null, unchanged this slice.

7. **Full manual line-by-line review of every service/model file in this
   module was not performed** — this slice relied on the earlier Explore
   investigation plus direct reads of `provider_router.py`, `models.py`,
   `chat_service.py`, `notification_service.py`, and the relevant slices of
   `constants.py`. `channel_providers.py`, `event_registry.py`, and
   `recipient_resolver.py` were confirmed NOT reachable from
   `provider_router.py` (so out of this slice's blast radius) but were not
   individually line-audited, since Workstream boundaries scope this slice
   to the selected router's actually-reachable code paths.

8. **Live-database integration tests could not be run in this environment**
   (no Postgres instance available) — `test_module_l5_20_chat_notify.py`,
   `test_module_l5_19_staff_chat.py`, `test_module_l5_14_chat.py`'s `*Live*`
   classes remain unexercised this slice, consistent with every prior
   slice in this initiative. All mocked/unit-level equivalents pass.
