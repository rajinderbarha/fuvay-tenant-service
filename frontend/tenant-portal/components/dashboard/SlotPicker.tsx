"use client";
import React from "react";
import { serviceJobAssignmentApi, type ProviderSlot } from "../../lib/api";

/**
 * Pick a slot the provider can actually take, instead of typing one and hoping.
 *
 * The windows come from the availability engine -- the same one the customer booking flow
 * offers slots from, and the same one that re-checks capacity at confirmation. That is the
 * point of not building a second list here: a hand-typed "10:00-12:00" can fall outside
 * the provider's own working hours, notice period or per-slot capacity, and the booking is
 * then refused AFTER a time has been given to a customer.
 *
 * When no availability is configured the engine returns nothing, and this falls back to
 * the free-text field rather than inventing windows. An empty dropdown would be a dead
 * end; a made-up one would be worse.
 */
export interface SlotPickerProps {
  jobId: string;
  date: string;
  window: string;
  onChange: (next: { date: string; window: string }) => void;
}

/** " (1 left)" when both numbers are present, and nothing at all otherwise -- an invented
 * capacity is worse than no capacity shown. */
function remainingOf(slot: ProviderSlot): string {
  if (typeof slot.capacity !== "number" || typeof slot.already_booked !== "number") return "";
  const left = slot.capacity - slot.already_booked;
  return left > 0 ? ` (${left} left)` : "";
}

export function SlotPicker({ jobId, date, window: chosen, onChange }: SlotPickerProps) {
  const [slots, setSlots] = React.useState<ProviderSlot[] | null>(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let live = true;
    serviceJobAssignmentApi.availableSlots(jobId)
      .then(res => { if (live) setSlots(res.slots ?? []); })
      // A failed lookup must not block scheduling: the free-text field still works.
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [jobId]);

  const dates = React.useMemo(
    () => [...new Set((slots ?? []).map(s => s.date))].sort(),
    [slots],
  );
  const windowsForDate = React.useMemo(
    () => (slots ?? []).filter(s => s.date === date),
    [slots, date],
  );

  if (failed || (slots !== null && slots.length === 0)) {
    return (
      <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
        {failed
          ? "Couldn't load your available slots. Enter the date and window instead."
          : "No availability is configured, so enter the date and window instead."}
      </p>
    );
  }

  if (slots === null) {
    return (
      <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
        Loading your available slots…
      </p>
    );
  }

  const selectStyle: React.CSSProperties = {
    width: "100%", padding: "8px 12px", fontSize: 13,
    borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
    background: "var(--surface)", color: "var(--text-primary)",
  };

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div>
        <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
          Available date
        </label>
        <select
          style={selectStyle}
          value={dates.includes(date) ? date : ""}
          onChange={e => {
            const nextDate = e.target.value;
            // Clear the window with the date: a window from another day is not a slot.
            const first = (slots ?? []).find(s => s.date === nextDate);
            onChange({ date: nextDate, window: first ? first.time_window : "" });
          }}
        >
          <option value="">— Select a date —</option>
          {dates.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      <div>
        <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
          Available time window
        </label>
        <select
          style={selectStyle}
          value={chosen}
          disabled={windowsForDate.length === 0}
          onChange={e => onChange({ date, window: e.target.value })}
        >
          <option value="">
            {windowsForDate.length === 0 ? "— Pick a date first —" : "— Select a window —"}
          </option>
          {windowsForDate.map(slot => (
            <option key={`${slot.date}-${slot.time_window}`} value={slot.time_window}>
              {slot.time_window}
              {/* Remaining capacity, derived from the engine's real numbers rather than a
                  field it does not send: `capacity` minus `already_booked`. Two visits
                  landing in one window is exactly what capacity exists to prevent. */}
              {remainingOf(slot)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
