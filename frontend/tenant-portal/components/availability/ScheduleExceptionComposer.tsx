"use client";

import React, { useMemo, useState } from "react";
import { CalendarDays, CheckCircle2, PenLine, Plus } from "lucide-react";
import { Btn, Input } from "../shared/ui";
import type {
  AvailabilityException,
  HolidayCalendarResponse,
  HolidayCalendarItem,
} from "../../lib/api";

const CUSTOM_REASONS = [
  "Personal closure",
  "Staff training",
  "Team unavailable",
  "Equipment maintenance",
  "Local event",
  "Emergency closure",
  "Other",
] as const;

function prettyDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric",
  });
}

export function ScheduleExceptionComposer({
  calendar,
  calendarError,
  exceptions,
  minDate,
  saving,
  onAdd,
}: {
  calendar: HolidayCalendarResponse | null;
  calendarError?: string;
  exceptions: AvailabilityException[];
  minDate: string;
  saving: boolean;
  onAdd: (entry: { date: string; reason: string; source: "holiday_calendar" | "custom" }) => Promise<boolean>;
}) {
  const [mode, setMode] = useState<"holiday" | "custom">("holiday");
  const [holidayDate, setHolidayDate] = useState("");
  const [customDate, setCustomDate] = useState("");
  const [customReason, setCustomReason] = useState<(typeof CUSTOM_REASONS)[number]>("Personal closure");
  const [otherReason, setOtherReason] = useState("");
  const closedDates = useMemo(() => new Set(exceptions.map(item => item.date)), [exceptions]);
  const choices = useMemo(
    () => (calendar?.holidays ?? []).filter(item => !item.already_closed && !closedDates.has(item.date)),
    [calendar, closedDates],
  );
  const selected = choices.find(item => item.date === holidayDate) ?? null;
  const customReasonValue = customReason === "Other" ? otherReason.trim() : customReason;

  async function addHoliday(item: HolidayCalendarItem | null) {
    if (!item) return;
    const saved = await onAdd({ date: item.date, reason: item.name, source: "holiday_calendar" });
    if (saved) setHolidayDate("");
  }

  async function addCustom() {
    if (!customDate || !customReasonValue) return;
    const saved = await onAdd({ date: customDate, reason: customReasonValue, source: "custom" });
    if (saved) {
      setCustomDate(""); setCustomReason("Personal closure"); setOtherReason("");
    }
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div role="group" aria-label="Exception type" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" aria-pressed={mode === "holiday"} onClick={() => setMode("holiday")} className="cov-exception-mode">
          <CalendarDays size={14}/> Choose a holiday
        </button>
        <button type="button" aria-pressed={mode === "custom"} onClick={() => setMode("custom")} className="cov-exception-mode">
          <PenLine size={14}/> Custom closure
        </button>
      </div>

      {mode === "holiday" ? (
        <div className="cov-guided-exception" data-tone="holiday">
          <div>
            <strong>Upcoming public holidays</strong>
            <p>Select one holiday. Its official name and date are filled automatically.</p>
          </div>
          {calendarError ? (
            <p role="alert" className="cov-day-error">{calendarError} You can still use Custom closure.</p>
          ) : !calendar ? (
            <p role="status">Syncing the holiday calendar…</p>
          ) : choices.length === 0 ? (
            <p>All holidays in the current calendar range are already closed.</p>
          ) : (
            <>
              <label className="cov-field">
                Holiday
                <select disabled={saving} aria-label="Holiday" value={holidayDate} onChange={event => setHolidayDate(event.target.value)}>
                  <option value="">Select an upcoming holiday</option>
                  {choices.map(item => (
                    <option key={item.date} value={item.date}>
                      {prettyDate(item.date)} — {item.name}
                    </option>
                  ))}
                </select>
              </label>
              {selected && <div className="cov-holiday-selection">
                <CheckCircle2 size={17}/>
                <span><strong>{selected.name}</strong><small>{prettyDate(selected.date)} · {selected.scope === "regional" ? "Regional holiday" : "Public holiday"}</small></span>
              </div>}
              <Btn variant="secondary" loading={saving} disabled={!selected} icon={<Plus size={14}/>} onClick={() => addHoliday(selected)}>
                Add holiday closure
              </Btn>
              <small className="cov-calendar-source">
                Synced for {calendar.states.join(", ") || "India"}; dates are supplied by the platform holiday calendar.
              </small>
            </>
          )}
        </div>
      ) : (
        <div className="cov-guided-exception">
          <div>
            <strong>Custom closure</strong>
            <p>Use this only for your own closure, training, maintenance, or a local event.</p>
          </div>
          <div className="cov-custom-exception-fields">
            <label className="cov-field">
              Closure date
              <input type="date" disabled={saving} min={minDate} value={customDate} onChange={event => setCustomDate(event.target.value)}/>
            </label>
            <label className="cov-field">
              Reason
              <select disabled={saving} value={customReason} onChange={event => setCustomReason(event.target.value as (typeof CUSTOM_REASONS)[number])}>
                {CUSTOM_REASONS.map(reason => <option key={reason}>{reason}</option>)}
              </select>
            </label>
          </div>
          {customReason === "Other" && (
            <Input disabled={saving} label="Short reason" placeholder="Enter a short closure reason" value={otherReason} onChange={value => setOtherReason(value.slice(0, 160))}/>
          )}
          <Btn variant="secondary" loading={saving} disabled={!customDate || !customReasonValue} icon={<Plus size={14}/>} onClick={addCustom}>
            Add custom closure
          </Btn>
        </div>
      )}

      <style>{`
        .cov-exception-mode{display:inline-flex;align-items:center;gap:7px;min-height:38px;padding:0 13px;border:1px solid var(--border);border-radius:10px;background:var(--surface);color:var(--text-secondary);font-size:12.5px;font-weight:700;cursor:pointer}
        .cov-exception-mode[aria-pressed=true]{border-color:var(--accent);background:var(--accent-muted);color:var(--accent)}
        .cov-guided-exception{display:grid;gap:12px;padding:14px;border:1px solid var(--border);border-radius:13px;background:var(--surface-sunken)}
        .cov-guided-exception[data-tone=holiday]{border-color:var(--info-border);background:var(--info-bg)}
        .cov-guided-exception strong{color:var(--text-primary);font-size:13px}.cov-guided-exception p{margin:3px 0 0;color:var(--text-tertiary);font-size:12px;line-height:1.5}
        .cov-guided-exception select,.cov-guided-exception input[type=date]{width:100%;height:40px;padding:0 10px;border:1px solid var(--border);border-radius:10px;background:var(--surface);color:var(--text-primary);font-size:12.5px}
        .cov-custom-exception-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.cov-field{display:grid;gap:6px;color:var(--text-secondary);font-size:11px;font-weight:700}
        .cov-holiday-selection{display:flex;align-items:center;gap:9px;padding:10px;border:1px solid var(--success-border);border-radius:10px;background:var(--success-bg);color:var(--success-text)}.cov-holiday-selection span{display:grid;gap:2px}.cov-holiday-selection small{color:var(--text-secondary);font-size:10.5px}
        .cov-calendar-source{color:var(--text-tertiary);font-size:10.5px}
        @media(max-width:640px){.cov-custom-exception-fields{grid-template-columns:1fr}}
      `}</style>
    </div>
  );
}
