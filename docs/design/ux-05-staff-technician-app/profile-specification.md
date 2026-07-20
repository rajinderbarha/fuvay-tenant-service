# Profile Specification

`ProfileScreen` (extended, not replaced) now shows, in addition to its pre-existing phone/schedule/performance
sections:
- **Canonical role tag** (`Staff`/`Technician`) from the same fail-closed `deriveRole()` used everywhere else —
  descriptive only, never itself a permission check on this screen.
- **Assigned Services** — real, from `StaffUser.specialisations` (already fetched by the pre-existing
  `staffApi.get()` call, no new API call added).
- **Assigned Areas / Certifications / Supported Brands** — honestly labeled `MOCK_DESIGN_ONLY`; no such field
  exists on `StaffUser` today.
- **Availability** — `AvailabilityControl`, see `availability-work-status.md`.
- **Recent Activity** — honestly labeled `MOCK_DESIGN_ONLY`; no per-staff activity-feed endpoint exists.

No tenant-owner settings, permission-admin controls, or HR/health information were added — none exist in this
app's real data model and none were fabricated.
