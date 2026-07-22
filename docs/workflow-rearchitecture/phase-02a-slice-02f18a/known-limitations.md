# Known Limitations

1. **Attachment uploader-level authorization not enforced** — only
   tenant-match is checked; see `product-decisions-required.md` item 1.

2. **Attachment message-binding not formally modeled** — see
   `product-decisions-required.md` item 2.

3. **Completed/cancelled Job technician access does not time-box out** —
   see `product-decisions-required.md` item 3.

4. **`list_threads` for technicians reflects participant-row snapshot, not
   live assignment** — a technician assigned to an EXISTING thread's job
   after the thread was created won't see it listed until a participant
   row exists for them, even though direct access
   (`get_thread`/`send_message`) would already permit it via the live
   assignment check. See `product-decisions-required.md` item 4.

5. **`require_staff_or_technician_only` has no access-scope (readonly)
   check** — carried forward from 2F-18's `known-limitations.md` item 2,
   unchanged, still the existing dependency's own design.

6. **No `ForeignKey()` DB constraints on any of the 8 models** —
   carried forward from 2F-18, unchanged, out of scope (would require a
   migration).

7. **`app/engines/media/access.py` was not read or integrated** — this
   slice's attachment check queries `MediaAsset` directly rather than
   reusing that engine's own access-control helpers, to avoid a
   cross-engine coupling not scoped for this slice. If that module's own
   authorization semantics differ from a simple tenant-match, this slice's
   check may be either stricter or looser than the media engine's own
   rules — flagged, not reconciled.

8. **Live-database integration tests could not be run in this environment**
   (no Postgres instance available) — same exclusion as every prior slice
   touching this module (`test_module_l5_20_chat_notify.py`,
   `test_module_l5_19_staff_chat.py`, `test_module_l5_14_chat.py`'s `*Live*`
   classes).
