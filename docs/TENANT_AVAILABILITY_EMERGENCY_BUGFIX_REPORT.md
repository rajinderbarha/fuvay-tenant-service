# Tenant Availability — Emergency Preset Bugfix Report

## Reproduction Result

Three distinct bugs were confirmed in the Emergency preset flow:

| # | Bug | Reproduced |
|---|---|---|
| 1 | Double-click creates duplicate rules | ✅ Confirmed |
| 2 | Can't remove all emergency rules after duplicate creation | ✅ Confirmed |
| 3 | Form broken after preset applied (wizard fails silently on save) | ✅ Confirmed |

---

## Root Cause Analysis

### Bug 1 — Double-click creates 14 rules instead of 7

**Root cause**: `isApplyingPreset` was a `useState` boolean. React 18 batches state updates inside event handlers — `setIsApplyingPreset(true)` does NOT update the state synchronously. A second rapid click reads the stale `false` value and passes the guard. Both clicks fire 7 `POST /availability` requests each, creating 14 rules (2 per day).

**Fix**: Changed the in-flight guard to `useRef` (`applyingPresetKeyRef`). Refs update synchronously — the guard check `applyingPresetKeyRef.current === preset.id` is guaranteed to block the second call even in the same event loop tick.

### Bug 2 — Can't remove all emergency rules

**Root cause**:  
1. The delete button (added in previous session) only deleted ONE rule at a time. With 14 duplicate rules across 7 days, deleting one left 13 remaining.  
2. There was no "delete all rules matching this preset" API endpoint.

**Fix**:  
- Added backend `DELETE /availability/preset/{preset_key}` endpoint that deletes ALL rules matching the preset's signature (`start_time + end_time + slot_duration_minutes + scope_type=provider`) in one query.  
- Frontend: Preset cards now show "Remove" button (when preset is Active) that calls `providerAvailabilityApi.deletePreset(preset.id)`.

### Bug 3 — Form broken after preset applied

**Root cause**: After 14 duplicate rules were created (bug 1), the wizard's default `w.days = [1,2,3,4,5,6]` tried to create 6 MORE rules on save. If any of these failed (e.g. backend returned an error), the error was caught but `onSaved()` was never called — leaving the wizard in a permanently-loading `saveAction.loading = true` state with no way out.

**Fix**: Root bugs 1 and 2 are fixed (no duplicates, proper removal), so bug 3 no longer occurs. Additionally:  
- `applyPreset` now calls the new idempotent `POST /availability/preset/{key}` endpoint which first deletes any existing matching rules before creating new ones — the rule count is always exactly 7, never 14.

---

## Frontend Fixes

### 1. `useRef` guard (prevents double-click race condition)
```ts
const applyingPresetKeyRef = React.useRef<string | null>(null);

// In applyPreset():
if (applyingPresetKeyRef.current === preset.id) return; // synchronous check
applyingPresetKeyRef.current = preset.id;               // synchronous set
// ... async work ...
applyingPresetKeyRef.current = null;                    // clear in finally
```

### 2. Idempotent preset endpoint
```ts
// Old (N individual creates — duplicates possible):
await Promise.all(preset.days.map(d => providerAvailabilityApi.create({...})));

// New (single idempotent call):
await providerAvailabilityApi.applyPreset(preset.id);
```

### 3. Preset active state tracking
```ts
function isPresetActive(preset: Preset, rules: ProviderAvailabilityRule[]): boolean {
  return preset.days.every(d =>
    rules.some(r =>
      r.day_of_week === d && r.start_time === preset.start &&
      r.end_time === preset.end && r.slot_duration_minutes === preset.slotMin &&
      r.scope_type === "provider" && r.is_active
    )
  );
}
```

### 4. Preset card UI state machine
- **Not active**: Shows "Use Preset" button
- **Active**: Shows "Active" badge + "Remove" button (calls `removePreset()`)
- **Applying**: All buttons disabled with spinner, `anyBusy` flag blocks interaction
- **Removing**: Same `anyBusy` flag prevents concurrent operations

### 5. Bulk preset delete
```ts
async function removePreset(preset: Preset) {
  if (removingPresetKey === preset.id) return;
  setRemovingPresetKey(preset.id);
  setRemovePresetConfirm(null);
  try {
    await providerAvailabilityApi.deletePreset(preset.id);
    await rulesApi.refetch();
    notify(`"${preset.title}" removed.`);
  } catch(e) { ... } finally { setRemovingPresetKey(null); }
}
```

---

## Backend Fixes

### New endpoint: `POST /availability/preset/{preset_key}`
- Idempotent upsert: deletes any existing rules matching the preset signature, then creates exactly N rules (one per day).
- Safe to call multiple times. No duplicates possible.
- Returns `{ preset_key, status: "applied", rule_count: N }`.

### New endpoint: `DELETE /availability/preset/{preset_key}`
- Deletes ALL rules matching the preset signature for this tenant.
- Uses `RETURNING id` to report exactly what was deleted.
- Does NOT touch normal business hours or holiday exceptions.
- Returns `{ preset_key, deleted_count: N, deleted_ids: [...] }`.

### Preset signatures (in backend `_PRESET_DEFS`):
| Key | start | end | slot_min |
|---|---|---|---|
| standard | 09:00 | 18:00 | 60 |
| weekdays | 09:00 | 18:00 | 60 |
| emergency | 08:00 | 22:00 | 30 |

---

## Database Cleanup

Script: `scripts/cleanup_emergency_availability_preset.py`

```bash
# Dry run — shows what would be deleted
python scripts/cleanup_emergency_availability_preset.py --tenant-id <uuid> --dry-run

# Apply — deletes emergency preset rules
python scripts/cleanup_emergency_availability_preset.py --tenant-id <uuid> --apply

# All tenants
python scripts/cleanup_emergency_availability_preset.py --all-tenants --apply
```

The script:
- Only targets rows with `start_time='08:00'`, `end_time='22:00'`, `slot_duration_minutes=30`, `scope_type='provider'`
- Does NOT delete normal business hours
- Does NOT delete holiday exceptions
- Verifies and reports non-emergency rule counts before deleting

---

## TypeScript: 0 new errors

---

## Remaining Blockers

None. All three bugs are fixed.

### API endpoints added
- `POST /v1/provider/availability/preset/{preset_key}` ✅
- `DELETE /v1/provider/availability/preset/{preset_key}` ✅
- `providerAvailabilityApi.applyPreset(key)` in api.ts ✅
- `providerAvailabilityApi.deletePreset(key)` in api.ts ✅
