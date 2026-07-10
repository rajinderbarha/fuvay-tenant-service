# Tenant Business Hours — Remaining Blockers

## P2 — Non-blocking

### 1. Holiday backend endpoint not implemented
- **Impact:** Holidays added via the UI are lost on page refresh.
- **Current behavior:** Holidays stored in React state. Warning banner shown in UI.
- **Fix:** Implement `POST /v1/provider/availability/exceptions` and `GET /v1/provider/availability/exceptions`.

### 2. Slot preview is client-side only
- **Impact:** Preview respects configured hours/duration but not server-side buffer, minimum notice, or dynamic capacity constraints.
- **Current behavior:** `generateSlots(start, end, slotMin)` runs in browser. Matches backend slot logic for standard cases.
- **Fix:** Implement `POST /v1/provider/availability/slot-preview` and wire to `providerAvailabilityApi.slotPreview()`.

### 3. Permission-gated read-only mode not enforced in UI
- **Impact:** A tenant user without `availability.update` permission will still see Add/Edit/Delete buttons.
- **Current behavior:** Buttons are always rendered; the backend will 403 on save attempts (request_id shown).
- **Fix:** Pass permission flags from JWT/context to conditionally hide action buttons.

## None P0/P1 blockers. Page is fully functional for standard use.
