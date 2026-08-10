"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { Modal as DsModal, Button as DsButton, Skeleton as DsSkeleton } from "@serviceos/design-system";
import {
  providerAvailabilityApi,
  providerStatusApi,
  providerTeamMembersApi,
  providerServiceAreasApi,
  tenantSetupApi,
  ServiceOSError,
  type ProviderAvailabilityRule,
  type ProviderAvailabilityPayload,
  type AvailabilityScopeType,
} from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import {
  Clock, ChevronRight, RefreshCw, Plus, AlertTriangle, CheckCircle2,
  XCircle, Copy, Activity, Calendar, Edit2, Trash2, AlertCircle,
  Shield, Eye, ChevronLeft, Sun, Info, X,
} from "lucide-react";

// ── Constants ─────────────────────────────────────────────────────────────────
const DAY_NAMES = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
const DAY_SHORT = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

// 0=Sun, 1=Mon, ..., 6=Sat  — backend uses this numbering
const ORDERED_DAYS = [1,2,3,4,5,6,0]; // Mon-first display

const SCOPE_LABEL: Record<string, string> = {
  provider:     "All Services",
  offering:     "Specific Service",
  staff_member: "Staff Member",
  service_area: "Service Area",
};

const SLOT_PRESETS = [30, 45, 60, 90, 120];

// ── Safe helpers ──────────────────────────────────────────────────────────────
const safeText = (v: unknown, fb = "—"): string =>
  typeof v === "string" && v.trim() ? v.trim() : fb;
const safeNum = (v: unknown): number =>
  typeof v === "number" && isFinite(v) ? v : 0;
const safeDate = (v: unknown): string => {
  if (!v) return "—";
  try { return new Date(String(v)).toLocaleDateString("en-IN", { dateStyle: "medium" }); } catch { return "—"; }
};
function copyText(t: string) {
  if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {});
}

// ── Slot generation (client-side) ─────────────────────────────────────────────
function generateSlots(start: string, end: string, durationMin: number): string[] {
  if (!start || !end || durationMin <= 0) return [];
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  if (isNaN(sh) || isNaN(sm) || isNaN(eh) || isNaN(em)) return [];
  let cur = sh * 60 + sm;
  const endMin = eh * 60 + em;
  const slots: string[] = [];
  while (cur + durationMin <= endMin && slots.length < 48) {
    const h = Math.floor(cur / 60);
    const m = cur % 60;
    slots.push(`${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`);
    cur += durationMin;
  }
  return slots;
}

// ── Validation ────────────────────────────────────────────────────────────────
interface ValidationIssue {
  severity: "danger" | "warning";
  code: string;
  title: string;
  reason: string;
  cta: string;
}

/** `technicianCount` is how many people can actually take an assignment; 0 means "not
 * known yet", and the team check is skipped rather than guessed at. */
function detectIssues(rules: ProviderAvailabilityRule[], technicianCount = 0): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const active = rules.filter(r => r.is_active);
  if (active.length === 0) {
    issues.push({ severity: "danger", code: "no_active_rules",
      title: "No Active Rules",
      reason: "Customers cannot book your services until you add working hours.",
      cta: "Add Working Hours" });
  }
  rules.forEach(r => {
    if (r.start_time >= r.end_time) {
      issues.push({ severity: "danger", code: "invalid_time_range",
        title: "Invalid Time Range",
        reason: `${DAY_NAMES[r.day_of_week]} rule: end time must be after start time.`,
        cta: "Edit Rule" });
    }
    if (r.slot_duration_minutes !== null && r.slot_duration_minutes < 15) {
      issues.push({ severity: "warning", code: "slot_duration_too_small",
        title: "Slot Duration Too Short",
        reason: `${DAY_NAMES[r.day_of_week]} rule: slot duration should be at least 15 minutes.`,
        cta: "Edit Rule" });
    }
    if (r.slot_duration_minutes !== null && r.slot_duration_minutes > 480) {
      issues.push({ severity: "warning", code: "slot_duration_too_large",
        title: "Slot Duration Too Long",
        reason: `${DAY_NAMES[r.day_of_week]} rule: slot duration exceeds 480 minutes.`,
        cta: "Edit Rule" });
    }
    if (r.max_bookings_per_slot !== null && r.max_bookings_per_slot < 1) {
      issues.push({ severity: "danger", code: "max_bookings_missing",
        title: "Invalid Max Bookings",
        reason: `${DAY_NAMES[r.day_of_week]} rule: max bookings per slot must be at least 1.`,
        cta: "Edit Rule" });
    }
    // A rule promising more simultaneous visits than there are people to send. Reported
    // for rules SAVED BEFORE this limit existed -- the booking engine already caps them
    // in practice, so the number on screen is not the number in force until it is fixed.
    if (technicianCount > 0 && r.max_bookings_per_slot !== null
        && r.max_bookings_per_slot > technicianCount) {
      issues.push({ severity: "warning", code: "max_bookings_exceeds_team",
        title: "More Bookings Than Technicians",
        reason: `${DAY_NAMES[r.day_of_week]} rule allows ${r.max_bookings_per_slot} bookings per slot, `
          + `but only ${technicianCount} technician(s) can take assignments. `
          + `Bookings are limited to ${technicianCount}.`,
        cta: "Edit Rule" });
    }
    if ((r.scope_type === "offering" || r.scope_type === "staff_member" || r.scope_type === "service_area") && !r.scope_id) {
      issues.push({ severity: "warning", code: "scope_id_missing",
        title: "Scope ID Missing",
        reason: `A ${SCOPE_LABEL[r.scope_type]} rule on ${DAY_NAMES[r.day_of_week]} has no target selected.`,
        cta: "Edit Rule" });
    }
  });
  return issues;
}

// ── Sub-components ────────────────────────────────────────────────────────────
function SectionError({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry: () => void;
}) {
  return (
    <div style={{ padding:"16px 20px", background:"var(--danger-bg)", border:"1px solid var(--danger-border)", borderRadius:"var(--radius-lg)" }}>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:12 }}>
        <div>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--danger-text)", margin:"0 0 4px", display:"flex", alignItems:"center", gap:6 }}>
            <XCircle size={14}/> {title}
          </p>
          <p style={{ fontSize:12, color:"var(--danger-text)", margin:0, opacity:0.85 }}>{error}</p>
          {requestId && (
            <button onClick={() => copyText(requestId)}
              style={{ fontSize:11, color:"var(--danger-text)", background:"none", border:"none",
                cursor:"pointer", padding:"4px 0 0", display:"flex", alignItems:"center",
                gap:4, fontFamily:"inherit", opacity:0.75 }}>
              <Copy size={10}/> Request ID: {requestId}
            </button>
          )}
        </div>
        <button onClick={onRetry}
          style={{ padding:"6px 12px", fontSize:12, borderRadius:"var(--radius-md)",
            border:"1px solid var(--danger-border)", background:"transparent",
            color:"var(--danger-text)", cursor:"pointer", fontFamily:"inherit",
            display:"flex", alignItems:"center", gap:5, flexShrink:0 }}>
          <RefreshCw size={11}/> Retry
        </button>
      </div>
    </div>
  );
}

function StatusBadge({ active, label }: { active: boolean; label?: string }) {
  return (
    <span style={{ fontSize:11, fontWeight:700, padding:"2px 9px", borderRadius:999,
      background: active ? "var(--success-bg)" : "var(--surface-sunken)",
      color: active ? "var(--success-text)" : "var(--text-secondary)",
      border: `1px solid ${active ? "var(--success-border)" : "var(--border)"}`,
      whiteSpace:"nowrap" }}>
      {label ?? (active ? "Configured" : "Not Configured")}
    </span>
  );
}

// ── Preset Cards ──────────────────────────────────────────────────────────────
interface Preset {
  id: string;
  title: string;
  description: string;
  preview: string;
  icon: string;
  days: number[];
  start: string;
  end: string;
  slotMin: number;
  maxBookings: number;
}

const PRESETS: Preset[] = [
  { id:"standard", title:"Standard Hours", description:"Great for most home service businesses.",
    icon:"🕘", preview:"Mon–Sat, 09:00–19:00", days:[1,2,3,4,5,6], start:"09:00", end:"19:00", slotMin:60, maxBookings:5 },
  { id:"weekdays", title:"Weekdays Only", description:"No weekend availability.",
    icon:"📅", preview:"Mon–Fri, 09:00–18:00", days:[1,2,3,4,5], start:"09:00", end:"18:00", slotMin:60, maxBookings:5 },
  { id:"emergency", title:"Emergency Service", description:"Extended hours including weekends.",
    icon:"🚨", preview:"All days, 08:00–22:00", days:[0,1,2,3,4,5,6], start:"08:00", end:"22:00", slotMin:30, maxBookings:3 },
  { id:"custom", title:"Custom Schedule", description:"Choose your own days and hours.",
    icon:"✏️", preview:"Your own days and time", days:[], start:"09:00", end:"18:00", slotMin:60, maxBookings:5 },
];

function isPresetActive(preset: Preset, rules: ProviderAvailabilityRule[]): boolean {
  if (preset.id === "custom") return false;
  return preset.days.every(d =>
    rules.some(r =>
      r.day_of_week === d &&
      r.start_time === preset.start &&
      r.end_time === preset.end &&
      r.slot_duration_minutes === preset.slotMin &&
      r.scope_type === "provider" &&
      r.is_active
    )
  );
}

// ── Preset Confirmation Modal ──────────────────────────────────────────────────
function PresetConfirmModal({ preset, onConfirm, onCancel, loading }: {
  preset: Preset; onConfirm: () => void; onCancel: () => void; loading: boolean;
}) {
  return (
    <DsModal open onClose={onCancel} title={`Apply ${preset.title}?`}
      footer={<>
        <DsButton variant="secondary" size="sm" onClick={onCancel}>Cancel</DsButton>
        <DsButton variant="primary" size="sm" disabled={loading} loading={loading} onClick={onConfirm}>
          Apply Preset
        </DsButton>
      </>}>
      <div style={{ fontSize:32, marginBottom:12, textAlign:"center" }}>{preset.icon}</div>
      <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 6px", textAlign:"center" }}>
        This will update your weekly schedule.
      </p>
      <div style={{ padding:"10px 14px", background:"var(--surface-sunken)", border:"1px solid var(--border)",
        borderRadius:9, fontSize:12, color:"var(--text-secondary)", textAlign:"center", fontFamily:"monospace" }}>
        {preset.preview}
      </div>
    </DsModal>
  );
}

// ── Weekly Schedule View ──────────────────────────────────────────────────────
const DAY_FULL_NAMES = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const DAY_BG = [
  "rgba(124,58,237,0.08)","rgba(37,99,235,0.08)","rgba(37,99,235,0.08)",
  "rgba(37,99,235,0.08)","rgba(37,99,235,0.08)","rgba(37,99,235,0.08)","rgba(124,58,237,0.08)",
];
const DAY_FG = [
  "var(--accent)","var(--brand)","var(--brand)","var(--brand)","var(--brand)","var(--brand)","var(--accent)",
];

function WeeklyScheduleView({ rules, onEdit, onAdd, onDelete }: {
  rules: ProviderAvailabilityRule[];
  onEdit: (r: ProviderAvailabilityRule) => void;
  onAdd: (dayIdx: number) => void;
  onDelete: (r: ProviderAvailabilityRule) => void;
}) {
  return (
    <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow:"hidden" }}>
      {/* Card header */}
      <div style={{ padding:"18px 24px", borderBottom:"1px solid var(--border)" }}>
        <h2 style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 3px" }}>
          Weekly Schedule
        </h2>
        <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
          Your working hours for each day of the week.
        </p>
      </div>

      {/* Table */}
      <table style={{ width:"100%", borderCollapse:"collapse" }}>
        <thead>
          <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
            {["Day","Status","Working Hours","Action"].map(h => (
              <th key={h} style={{ padding:"10px 20px", textAlign:"left", fontSize:11, fontWeight:600,
                color:"var(--text-tertiary)", whiteSpace:"nowrap" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ORDERED_DAYS.map((dayIdx, rowIdx) => {
            const dayRules = rules.filter(r => r.day_of_week === dayIdx);
            const activeRules = dayRules.filter(r => r.is_active);
            const isOpen = activeRules.length > 0;
            return (
              <tr key={dayIdx} style={{ borderBottom: rowIdx < 6 ? "1px solid var(--border)" : "none" }}>
                {/* Day */}
                <td style={{ padding:"14px 20px" }}>
                  <span style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                    {DAY_NAMES[dayIdx]}
                  </span>
                </td>
                {/* Status */}
                <td style={{ padding:"14px 20px" }}>
                  <span style={{ fontSize:11, fontWeight:600, padding:"3px 10px", borderRadius:5,
                    background: isOpen ? "var(--success-bg)" : "var(--surface-sunken)",
                    color: isOpen ? "var(--success-text)" : "var(--text-secondary)",
                    border: `1px solid ${isOpen ? "var(--success-border)" : "var(--border)"}` }}>
                    {isOpen ? "Open" : "Closed"}
                  </span>
                </td>
                {/* Working Hours */}
                <td style={{ padding:"14px 20px" }}>
                  {activeRules.length === 0 ? (
                    <span style={{ fontSize:13, color:"var(--text-tertiary)" }}>—</span>
                  ) : (
                    <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                      {activeRules.map((r, i) => (
                        <div key={i} style={{ display:"flex", alignItems:"center", gap:6 }}>
                          <span style={{ fontSize:13, color:"var(--text-primary)" }}>
                            {r.start_time} – {r.end_time}
                          </span>
                          <button onClick={() => onEdit(r)} title="Edit"
                            style={{ background:"none", border:"none", cursor:"pointer",
                              color:"var(--text-tertiary)", padding:0, display:"flex", alignItems:"center" }}>
                            <Edit2 size={12}/>
                          </button>
                          <button onClick={() => onDelete(r)} title="Remove"
                            style={{ background:"none", border:"none", cursor:"pointer",
                              color:"var(--danger-text)", padding:0, display:"flex", alignItems:"center" }}>
                            <Trash2 size={12}/>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </td>
                {/* Action */}
                <td style={{ padding:"14px 20px", textAlign:"right" }}>
                  <div style={{ display:"flex", gap:8, justifyContent:"flex-end", alignItems:"center" }}>
                    <button onClick={() => onAdd(dayIdx)}
                      style={{ background:"none", border:"none", cursor:"pointer", fontFamily:"inherit",
                        fontSize:13, fontWeight:500, color:"var(--brand)",
                        display:"flex", alignItems:"center", gap:4, padding:0 }}>
                      <Plus size={13}/> Add Hours
                    </button>
                    {isOpen && (
                      <button onClick={() => activeRules.forEach(r => onDelete(r))}
                        style={{ background:"none", border:"none", cursor:"pointer", fontFamily:"inherit",
                          fontSize:12, color:"var(--danger-text)", padding:0 }}>
                        Close Day
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Slot Preview Panel ────────────────────────────────────────────────────────
function SlotPreviewPanel({ rules }: { rules: ProviderAvailabilityRule[] }) {
  const [selectedDay, setSelectedDay] = useState<number>(1);

  const dayRules = rules.filter(r => r.day_of_week === selectedDay && r.is_active);
  const allSlots: string[] = [];
  dayRules.forEach(r => {
    const dur = r.slot_duration_minutes ?? 60;
    generateSlots(r.start_time, r.end_time, dur).forEach(s => {
      if (!allSlots.includes(s)) allSlots.push(s);
    });
  });
  allSlots.sort();

  function fmt12(t: string): string {
    const [h, m] = t.split(":").map(Number);
    if (isNaN(h) || isNaN(m)) return t;
    const ampm = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 || 12;
    return `${String(h12).padStart(2,"0")}:${String(m).padStart(2,"0")} ${ampm}`;
  }

  return (
    <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-xl, 1rem)", overflow:"hidden" }}>
      <div style={{ padding:"18px 24px 0", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <div>
          <h2 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 2px",
            display:"flex", alignItems:"center", gap:8 }}>
            <span style={{ display:"inline-flex", width:22, height:22, borderRadius:6,
              background:"rgba(37,99,235,0.1)", alignItems:"center", justifyContent:"center" }}>
              <Eye size={13} style={{ color:"var(--brand)" }}/>
            </span>
            Booking Slot Preview
          </h2>
          <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
            These are the slots customers will see when booking on the selected day.
          </p>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:4, fontSize:10, color:"var(--text-tertiary)",
          padding:"4px 8px", borderRadius:6, background:"var(--surface-sunken)", border:"1px solid var(--border)" }}>
          <Info size={10}/> Client-side preview
        </div>
      </div>

      {/* Day tabs — pill style */}
      <div style={{ padding:"14px 24px 0", display:"flex", gap:4, flexWrap:"wrap" }}>
        {ORDERED_DAYS.map(d => {
          const hasRules = rules.some(r => r.day_of_week === d && r.is_active);
          const isSelected = selectedDay === d;
          return (
            <button key={d} onClick={() => setSelectedDay(d)}
              style={{ padding:"6px 14px", fontSize:12, fontWeight:600, borderRadius:20,
                border:"1px solid", cursor:"pointer", fontFamily:"inherit", transition:"all 0.12s",
                borderColor: isSelected ? "var(--brand)" : "var(--border)",
                background: isSelected ? "var(--brand)" : "transparent",
                color: isSelected ? "white" : hasRules ? "var(--text-primary)" : "var(--text-tertiary)" }}>
              {DAY_SHORT[d]}
              {hasRules && !isSelected && (
                <span style={{ display:"inline-block", width:5, height:5, borderRadius:"50%",
                  background:"var(--success-text)", marginLeft:5, verticalAlign:"middle" }}/>
              )}
            </button>
          );
        })}
      </div>

      <div style={{ padding:"16px 24px 20px" }}>

      {rules.length === 0 ? (
        <div style={{ textAlign:"center", padding:"28px", color:"var(--text-tertiary)" }}>
          <Clock size={30} style={{ opacity:0.25, marginBottom:10 }}/>
          <p style={{ fontSize:14, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 4px" }}>
            No working hours to preview.
          </p>
          <p style={{ fontSize:12, margin:0 }}>Add working hours to preview customer slots.</p>
        </div>
      ) : allSlots.length === 0 ? (
        <div style={{ padding:"16px", background:"var(--surface-sunken)", border:"1px solid var(--border)",
          borderRadius:9, textAlign:"center" }}>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 4px" }}>
            {DAY_NAMES[selectedDay]} — Closed
          </p>
          <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
            No customer bookings available on this day.
          </p>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom:10, padding:"8px 12px", borderRadius:"var(--radius-md)",
            background:"var(--success-bg)", border:"1px solid var(--success-border)",
            fontSize:12, color:"var(--success-text)", display:"flex", gap:6 }}>
            <CheckCircle2 size={13} style={{ flexShrink:0, marginTop:1 }}/>
            {allSlots.length} booking slots available on {DAY_NAMES[selectedDay]}
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(96px, 1fr))", gap:6 }}>
            {allSlots.map(slot => (
              <div key={slot} style={{ padding:"8px 0", textAlign:"center",
                background:"var(--surface-sunken)", border:"1px solid var(--border)",
                borderRadius:"var(--radius-md)", fontSize:12, fontFamily:"monospace", fontWeight:600,
                color:"var(--text-primary)" }}>
                {fmt12(slot)}
              </div>
            ))}
          </div>
        </div>
      )}
      </div>
    </div>
  );
}

// ── Wizard ────────────────────────────────────────────────────────────────────
interface WizardState {
  scope: AvailabilityScopeType;
  scopeId: string;
  scopeName: string;
  days: number[];
  start: string;
  end: string;
  slotMin: number;
  maxBookings: number;
  isActive: boolean;
}

const BLANK_WIZARD: WizardState = {
  scope: "provider", scopeId: "", scopeName: "",
  days: [1,2,3,4,5,6], start: "09:00", end: "18:00",
  slotMin: 60, maxBookings: 5, isActive: true,
};

interface WizardProps {
  initialDayIdx?: number | null;
  existingRule?: ProviderAvailabilityRule | null;
  onClose: () => void;
  onSaved: () => void;
  staffOptions: { id: string; name: string }[];
  areaOptions: { id: string; name: string }[];
}

function AvailabilityWizard({ initialDayIdx, existingRule, onClose, onSaved, staffOptions, areaOptions }: WizardProps) {
  const isEdit = !!existingRule;
  const [step, setStep] = useState(1);
  const totalSteps = 5;

  const [w, setW] = useState<WizardState>(() => {
    if (existingRule) {
      return {
        scope: existingRule.scope_type as AvailabilityScopeType,
        scopeId: existingRule.scope_id ?? "",
        scopeName: existingRule.scope_name ?? "",
        days: [existingRule.day_of_week],
        start: existingRule.start_time,
        end: existingRule.end_time,
        slotMin: existingRule.slot_duration_minutes ?? 60,
        maxBookings: existingRule.max_bookings_per_slot ?? 5,
        isActive: existingRule.is_active,
      };
    }
    return { ...BLANK_WIZARD, days: initialDayIdx !== null && initialDayIdx !== undefined ? [initialDayIdx] : [1,2,3,4,5,6] };
  });

  const [fieldErr, setFieldErr] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [saveErrId, setSaveErrId] = useState<string | null>(null);

  function f<K extends keyof WizardState>(k: K, v: WizardState[K]) {
    setW(prev => ({ ...prev, [k]: v }));
    setFieldErr(null);
  }

  function toggleDay(d: number) {
    setW(prev => ({
      ...prev,
      days: prev.days.includes(d) ? prev.days.filter(x => x !== d) : [...prev.days, d],
    }));
  }

  function validateStep(s: number): string | null {
    if (s === 1 && w.scope !== "provider" && !w.scopeId.trim()) return "Please select a target.";
    if (s === 2 && w.days.length === 0) return "Please select at least one day.";
    if (s === 3) {
      if (!w.start || !w.end) return "Start and end time are required.";
      if (w.start >= w.end) return "End time must be after start time.";
    }
    if (s === 4) {
      if (w.slotMin < 15 || w.slotMin > 480) return "Slot duration must be between 15 and 480 minutes.";
      if (w.maxBookings < 1) return "Max bookings must be at least 1.";
    }
    return null;
  }

  function nextStep() {
    const err = validateStep(step);
    if (err) { setFieldErr(err); return; }
    setFieldErr(null);
    setStep(s => Math.min(s + 1, totalSteps));
  }

  const previewSlots = generateSlots(w.start, w.end, w.slotMin);

  const saveAction = useAction(async () => {
    const err = validateStep(step);
    if (err) { setFieldErr(err); return; }
    setSaveErr(null); setSaveErrId(null);
    try {
      if (isEdit && existingRule) {
        const payload: Partial<ProviderAvailabilityPayload> = {
          scope_type: w.scope,
          scope_id: w.scopeId || null,
          day_of_week: w.days[0] ?? existingRule.day_of_week,
          start_time: w.start,
          end_time: w.end,
          slot_duration_minutes: w.slotMin,
          max_bookings_per_slot: w.maxBookings,
          is_active: w.isActive,
        };
        await providerAvailabilityApi.update(existingRule.id, payload);
      } else {
        await Promise.all(w.days.map(d =>
          providerAvailabilityApi.create({
            scope_type: w.scope,
            scope_id: w.scopeId || null,
            day_of_week: d,
            start_time: w.start,
            end_time: w.end,
            slot_duration_minutes: w.slotMin,
            max_bookings_per_slot: w.maxBookings,
            is_active: w.isActive,
          })
        ));
      }
      onSaved();
    } catch(e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setSaveErr(e instanceof Error ? e.message : "Save failed.");
      setSaveErrId(rid);
    }
  });

  const inputStyle: React.CSSProperties = {
    width:"100%", padding:"9px 12px", fontSize:13, boxSizing:"border-box",
    border:"1px solid var(--border)", borderRadius:"var(--radius-md)",
    background:"var(--surface)", color:"var(--text-primary)", outline:"none", fontFamily:"inherit",
  };

  const SCOPE_OPTIONS: { value: AvailabilityScopeType; title: string; desc: string }[] = [
    { value:"provider",     title:"All Services",        desc:"Use this schedule for your whole business." },
    { value:"offering",     title:"Specific Service",    desc:"Use this schedule only for selected services." },
    { value:"staff_member", title:"Staff Member",        desc:"Use this schedule only for one staff member." },
    { value:"service_area", title:"Service Area",        desc:"Use this schedule only for one service area." },
  ];

  const DAY_PRESETS = [
    { label:"Mon–Sat", days:[1,2,3,4,5,6] },
    { label:"Mon–Fri", days:[1,2,3,4,5] },
    { label:"All Days", days:[0,1,2,3,4,5,6] },
  ];

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.5)", zIndex:1000,
      display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
      <div style={{ background:"var(--surface)", borderRadius:14, maxWidth:600, width:"100%",
        maxHeight:"94vh", display:"flex", flexDirection:"column",
        boxShadow:"0 20px 60px rgba(0,0,0,0.2)", border:"1px solid var(--border)" }}>

        {/* Header */}
        <div style={{ padding:"18px 24px", borderBottom:"1px solid var(--border)",
          display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
          <div>
            <h2 style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
              {isEdit ? "Edit Working Hours" : "Add Working Hours"}
            </h2>
            <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"2px 0 0" }}>
              Step {step} of {totalSteps}
            </p>
          </div>
          <button onClick={onClose}
            style={{ width:30, height:30, borderRadius:"var(--radius-md)", border:"1px solid var(--border)",
              background:"var(--surface-sunken)", cursor:"pointer",
              display:"flex", alignItems:"center", justifyContent:"center", color:"var(--text-secondary)" }}>
            <X size={14}/>
          </button>
        </div>

        {/* Step indicator */}
        <div style={{ padding:"12px 24px", borderBottom:"1px solid var(--border)", flexShrink:0 }}>
          <div style={{ display:"flex", gap:6, alignItems:"center" }}>
            {["Who", "Days", "Hours", "Slots", "Review"].map((label, i) => (
              <React.Fragment key={label}>
                <div style={{ display:"flex", alignItems:"center", gap:5 }}>
                  <div style={{ width:22, height:22, borderRadius:"50%",
                    background: i + 1 < step ? "var(--success-text)" : i + 1 === step ? "var(--brand)" : "var(--surface-sunken)",
                    border: i + 1 <= step ? "none" : "1px solid var(--border)",
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontSize:10, fontWeight:700,
                    color: i + 1 <= step ? "white" : "var(--text-tertiary)" }}>
                    {i + 1 < step ? <CheckCircle2 size={12}/> : i + 1}
                  </div>
                  <span style={{ fontSize:11, fontWeight:600,
                    color: i + 1 === step ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                    {label}
                  </span>
                </div>
                {i < 4 && <div style={{ flex:1, height:1, background:"var(--border)" }}/>}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Body */}
        <div style={{ flex:1, overflowY:"auto", padding:"22px 24px" }}>
          {fieldErr && (
            <div style={{ padding:"10px 14px", background:"var(--danger-bg)", border:"1px solid var(--danger-border)",
              borderRadius:9, fontSize:12, color:"var(--danger-text)", marginBottom:14,
              display:"flex", gap:6 }}>
              <XCircle size={13} style={{ flexShrink:0, marginTop:1 }}/> {fieldErr}
            </div>
          )}

          {/* Step 1: Who */}
          {step === 1 && (
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                Who does this schedule apply to?
              </p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 6px" }}>
                One schedule for your whole business, or separate schedules for specific services, staff, or areas.
              </p>
              {SCOPE_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => f("scope", opt.value)}
                  style={{ padding:"14px 16px", borderRadius:10, border:"1px solid", cursor:"pointer",
                    textAlign:"left", fontFamily:"inherit",
                    borderColor: w.scope === opt.value ? "var(--brand)" : "var(--border)",
                    background: w.scope === opt.value ? "rgba(37,99,235,0.06)" : "var(--surface-sunken)" }}>
                  <p style={{ fontSize:13, fontWeight:700, margin:"0 0 3px",
                    color: w.scope === opt.value ? "var(--brand)" : "var(--text-primary)" }}>
                    {opt.title}
                  </p>
                  <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>{opt.desc}</p>
                </button>
              ))}

              {w.scope !== "provider" && (
                <div style={{ marginTop:6 }}>
                  <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                    Select {SCOPE_OPTIONS.find(s => s.value === w.scope)?.title}
                  </label>
                  {w.scope === "staff_member" && staffOptions.length > 0 ? (
                    <select value={w.scopeId} onChange={e => {
                      const opt = staffOptions.find(s => s.id === e.target.value);
                      f("scopeId", e.target.value);
                      f("scopeName", opt?.name ?? "");
                    }} style={{ ...inputStyle }}>
                      <option value="">— Select staff member —</option>
                      {staffOptions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  ) : w.scope === "service_area" && areaOptions.length > 0 ? (
                    <select value={w.scopeId} onChange={e => {
                      const opt = areaOptions.find(a => a.id === e.target.value);
                      f("scopeId", e.target.value);
                      f("scopeName", opt?.name ?? "");
                    }} style={{ ...inputStyle }}>
                      <option value="">— Select service area —</option>
                      {areaOptions.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                    </select>
                  ) : (
                    <input value={w.scopeId} onChange={e => f("scopeId", e.target.value)}
                      placeholder="Name or ID" style={inputStyle}/>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 2: Days */}
          {step === 2 && (
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                Which days are you open?
              </p>
              <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                {DAY_PRESETS.map(p => (
                  <button key={p.label} onClick={() => f("days", p.days)}
                    style={{ padding:"6px 14px", fontSize:12, fontWeight:600, borderRadius:"var(--radius-md)",
                      border:"1px solid var(--border)", background:"var(--surface-sunken)",
                      color:"var(--text-secondary)", cursor:"pointer", fontFamily:"inherit" }}>
                    {p.label}
                  </button>
                ))}
                <button onClick={() => f("days", [])}
                  style={{ padding:"6px 14px", fontSize:12, fontWeight:600, borderRadius:"var(--radius-md)",
                    border:"1px solid var(--border)", background:"var(--surface-sunken)",
                    color:"var(--text-secondary)", cursor:"pointer", fontFamily:"inherit" }}>
                  Clear
                </button>
              </div>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                {ORDERED_DAYS.map(d => (
                  <button key={d} onClick={() => { if (!isEdit) toggleDay(d); }}
                    style={{ padding:"10px 14px", borderRadius:10, border:"1px solid", cursor: isEdit ? "default" : "pointer",
                      fontFamily:"inherit", minWidth:60, textAlign:"center",
                      borderColor: w.days.includes(d) ? "var(--brand)" : "var(--border)",
                      background: w.days.includes(d) ? "rgba(37,99,235,0.08)" : "var(--surface-sunken)" }}>
                    <p style={{ fontSize:12, fontWeight:700, margin:"0 0 2px",
                      color: w.days.includes(d) ? "var(--brand)" : "var(--text-tertiary)" }}>
                      {DAY_SHORT[d]}
                    </p>
                    <p style={{ fontSize:10, margin:0,
                      color: w.days.includes(d) ? "var(--brand)" : "var(--text-tertiary)" }}>
                      {w.days.includes(d) ? "Open" : "Closed"}
                    </p>
                  </button>
                ))}
              </div>
              <div style={{ padding:"10px 14px", background:"var(--surface-sunken)", border:"1px solid var(--border)",
                borderRadius:9, fontSize:12, color:"var(--text-secondary)" }}>
                Selected: {w.days.length === 0 ? "No days selected" :
                  w.days.sort((a,b)=>a-b).map(d => DAY_SHORT[d]).join(", ")}
              </div>
            </div>
          )}

          {/* Step 3: Hours */}
          {step === 3 && (
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                Set your working hours
              </p>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                <div>
                  <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                    Opening Time
                  </label>
                  <input type="time" value={w.start} onChange={e => f("start", e.target.value)}
                    style={{ ...inputStyle, fontFamily:"monospace",
                      borderColor: w.start >= w.end && w.end ? "var(--danger-text)" : "var(--border)" }}/>
                </div>
                <div>
                  <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                    Closing Time
                  </label>
                  <input type="time" value={w.end} onChange={e => f("end", e.target.value)}
                    style={{ ...inputStyle, fontFamily:"monospace",
                      borderColor: w.start >= w.end && w.end ? "var(--danger-text)" : "var(--border)" }}/>
                </div>
              </div>
              {w.start && w.end && w.start < w.end && (
                <div style={{ padding:"10px 14px", background:"var(--success-bg)", border:"1px solid var(--success-border)",
                  borderRadius:9, fontSize:12, color:"var(--success-text)", display:"flex", gap:6 }}>
                  <CheckCircle2 size={13} style={{ flexShrink:0, marginTop:1 }}/>
                  Open from {w.start} to {w.end}
                </div>
              )}
              {w.start && w.end && w.start >= w.end && (
                <div style={{ padding:"10px 14px", background:"var(--danger-bg)", border:"1px solid var(--danger-border)",
                  borderRadius:9, fontSize:12, color:"var(--danger-text)", display:"flex", gap:6 }}>
                  <XCircle size={13} style={{ flexShrink:0, marginTop:1 }}/>
                  End time must be after start time.
                </div>
              )}
              <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer",
                padding:"10px 14px", background:"var(--surface-sunken)", border:"1px solid var(--border)",
                borderRadius:9, userSelect:"none" }}>
                <input type="checkbox" checked={w.isActive} onChange={e => f("isActive", e.target.checked)}
                  style={{ width:15, height:15, cursor:"pointer" }}/>
                <span style={{ fontSize:13, fontWeight:500, color:"var(--text-primary)" }}>
                  Activate this schedule immediately
                </span>
              </label>
            </div>
          )}

          {/* Step 4: Booking slots */}
          {step === 4 && (
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                Configure booking slots
              </p>
              <div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                  Slot Duration
                </label>
                <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:8 }}>
                  {SLOT_PRESETS.map(p => (
                    <button key={p} onClick={() => f("slotMin", p)}
                      style={{ padding:"8px 16px", fontSize:13, fontWeight:600, borderRadius:9,
                        border:"1px solid", cursor:"pointer", fontFamily:"inherit",
                        borderColor: w.slotMin === p ? "var(--brand)" : "var(--border)",
                        background: w.slotMin === p ? "rgba(37,99,235,0.08)" : "var(--surface-sunken)",
                        color: w.slotMin === p ? "var(--brand)" : "var(--text-primary)" }}>
                      {p} min
                    </button>
                  ))}
                </div>
                <input type="number" min={15} max={480} value={w.slotMin}
                  onChange={e => f("slotMin", Math.max(15, parseInt(e.target.value) || 60))}
                  style={{ ...inputStyle, width:160, fontFamily:"monospace" }}/>
              </div>
              <div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                  Max Customers Per Slot
                </label>
                <div style={{ display:"flex", gap:6, marginBottom:8 }}>
                  {[1,2,3,5,10].map(n => (
                    <button key={n} onClick={() => f("maxBookings", n)}
                      style={{ padding:"8px 14px", fontSize:13, fontWeight:600, borderRadius:9,
                        border:"1px solid", cursor:"pointer", fontFamily:"inherit",
                        borderColor: w.maxBookings === n ? "var(--brand)" : "var(--border)",
                        background: w.maxBookings === n ? "rgba(37,99,235,0.08)" : "var(--surface-sunken)",
                        color: w.maxBookings === n ? "var(--brand)" : "var(--text-primary)" }}>
                      {n}
                    </button>
                  ))}
                </div>
                <input type="number" min={1} max={100} value={w.maxBookings}
                  onChange={e => f("maxBookings", Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ ...inputStyle, width:120, fontFamily:"monospace" }}/>
              </div>
              {w.start < w.end && (
                <div style={{ padding:"12px 14px", background:"var(--surface-sunken)", border:"1px solid var(--border)",
                  borderRadius:9 }}>
                  <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)", margin:"0 0 6px",
                    textTransform:"uppercase", letterSpacing:"0.07em" }}>Preview</p>
                  <p style={{ fontSize:13, color:"var(--text-primary)", margin:0 }}>
                    {generateSlots(w.start, w.end, w.slotMin).length} slots between {w.start}–{w.end}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 5: Review */}
          {step === 5 && (
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                Review & Save
              </p>
              <div style={{ background:"var(--surface-sunken)", border:"1px solid var(--border)", borderRadius:10, padding:"16px 18px" }}>
                {[
                  ["Applies To",       SCOPE_LABEL[w.scope] + (w.scopeName ? ` — ${w.scopeName}` : "")],
                  ["Open Days",        w.days.length === 0 ? "None selected" : w.days.sort((a,b)=>a-b).map(d=>DAY_SHORT[d]).join(", ")],
                  ["Working Hours",    w.start && w.end ? `${w.start} – ${w.end}` : "—"],
                  ["Slot Duration",    `${w.slotMin} minutes`],
                  ["Max Bookings",     `${w.maxBookings} per slot`],
                  ["Available Slots",  w.start < w.end ? `${generateSlots(w.start, w.end, w.slotMin).length} slots per day` : "—"],
                  ["Status",           w.isActive ? "Active immediately" : "Saved as inactive"],
                ].map(([k,v]) => (
                  <div key={k} style={{ display:"flex", gap:12, padding:"8px 0",
                    borderBottom:"1px solid var(--border)" }}>
                    <span style={{ fontSize:12, color:"var(--text-secondary)", width:130, flexShrink:0 }}>{k}</span>
                    <span style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)" }}>{v}</span>
                  </div>
                ))}
              </div>

              {previewSlots.length > 0 && (
                <div>
                  <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)", textTransform:"uppercase",
                    letterSpacing:"0.07em", margin:"0 0 8px" }}>
                    Customers will see these slots:
                  </p>
                  <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
                    {previewSlots.slice(0, 12).map(s => (
                      <span key={s} style={{ padding:"4px 10px", borderRadius:6,
                        background:"rgba(37,99,235,0.06)", border:"1px solid rgba(37,99,235,0.15)",
                        fontSize:12, fontFamily:"monospace", color:"var(--text-primary)" }}>
                        {s}
                      </span>
                    ))}
                    {previewSlots.length > 12 && (
                      <span style={{ padding:"4px 10px", borderRadius:6,
                        background:"var(--surface-sunken)", border:"1px solid var(--border)",
                        fontSize:12, color:"var(--text-tertiary)" }}>
                        +{previewSlots.length - 12} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {saveErr && (
                <div style={{ padding:"10px 14px", background:"var(--danger-bg)", border:"1px solid var(--danger-border)",
                  borderRadius:9, fontSize:12, color:"var(--danger-text)" }}>
                  <p style={{ margin:"0 0 4px", fontWeight:600 }}>Availability could not be saved</p>
                  <p style={{ margin:"0 0 4px" }}>{saveErr}</p>
                  {saveErrId && (
                    <button onClick={() => copyText(saveErrId)}
                      style={{ fontSize:11, background:"none", border:"none", cursor:"pointer",
                        color:"var(--danger-text)", fontFamily:"inherit", display:"flex",
                        alignItems:"center", gap:4, padding:0, opacity:0.75 }}>
                      <Copy size={10}/> Request ID: {saveErrId}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding:"14px 24px", borderTop:"1px solid var(--border)", flexShrink:0,
          display:"flex", gap:8, justifyContent:"space-between" }}>
          <button onClick={() => step > 1 ? setStep(s => s - 1) : onClose()}
            style={{ padding:"9px 16px", fontSize:13, borderRadius:9, border:"1px solid var(--border)",
              background:"var(--surface-sunken)", color:"var(--text-primary)", cursor:"pointer",
              fontFamily:"inherit", display:"flex", alignItems:"center", gap:6 }}>
            <ChevronLeft size={13}/> {step > 1 ? "Back" : "Cancel"}
          </button>
          {step < totalSteps ? (
            <button onClick={nextStep}
              style={{ padding:"9px 20px", fontSize:13, fontWeight:600, borderRadius:9,
                border:"none", background:"var(--brand)", color:"white",
                cursor:"pointer", fontFamily:"inherit", display:"flex", alignItems:"center", gap:6 }}>
              Next <ChevronRight size={13}/>
            </button>
          ) : (
            <button onClick={saveAction.execute} disabled={saveAction.loading}
              style={{ padding:"9px 20px", fontSize:13, fontWeight:600, borderRadius:9,
                border:"none", background:"var(--brand)", color:"white", fontFamily:"inherit",
                cursor:saveAction.loading ? "not-allowed" : "pointer",
                opacity:saveAction.loading ? 0.7 : 1,
                display:"flex", alignItems:"center", gap:6 }}>
              {saveAction.loading
                ? <><RefreshCw size={12} style={{ animation:"spin 1s linear infinite" }}/> Saving…</>
                : <><CheckCircle2 size={13}/> Save Schedule</>}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Delete Confirm ────────────────────────────────────────────────────────────
function DeleteConfirm({ rule, onConfirm, onCancel, loading }: {
  rule: ProviderAvailabilityRule; onConfirm: () => void; onCancel: () => void; loading: boolean;
}) {
  return (
    <DsModal open onClose={onCancel} title="Remove Working Hours"
      footer={<>
        <DsButton variant="secondary" size="sm" onClick={onCancel}>Cancel</DsButton>
        <DsButton variant="destructive" size="sm" disabled={loading} loading={loading} onClick={onConfirm}>
          Remove Rule
        </DsButton>
      </>}>
      <div style={{ display:"flex", gap:12 }}>
        <AlertTriangle size={20} style={{ color:"var(--warning-text)", flexShrink:0 }}/>
        <div>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 10px" }}>
            {DAY_NAMES[rule.day_of_week]} {rule.start_time}–{rule.end_time}
          </p>
          <div style={{ padding:"10px 14px", background:"var(--warning-bg)", border:"1px solid var(--warning-border)",
            borderRadius:9, fontSize:12, color:"var(--warning-text)" }}>
            Removing this rule may make your business unavailable for bookings.
          </div>
        </div>
      </div>
    </DsModal>
  );
}

// ── Holidays Panel ────────────────────────────────────────────────────────────
interface HolidayEntry {
  id: string;
  date: string;
  type: string;
  reason: string;
  scope: string;
}

function HolidaysPanel({ holidays, onAdd, onDelete }: {
  holidays: HolidayEntry[];
  onAdd: () => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", padding:"20px 24px" }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:4 }}>
        <div>
          <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 2px",
            display:"flex", alignItems:"center", gap:8 }}>
            <Sun size={15}/> Holidays & Exceptions
          </p>
          <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
            {holidays.length} holiday{holidays.length !== 1 ? "s" : ""} or exception{holidays.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button onClick={onAdd}
          style={{ padding:"6px 14px", fontSize:12, fontWeight:600, borderRadius:"var(--radius-md)",
            border:"1px solid var(--border)", background:"var(--surface-sunken)",
            color:"var(--text-secondary)", cursor:"pointer", fontFamily:"inherit",
            display:"flex", alignItems:"center", gap:5 }}>
          <Plus size={11}/> Add Holiday
        </button>
      </div>

      <div style={{ marginTop:12, padding:"8px 12px", borderRadius:"var(--radius-md)",
        background:"var(--warning-bg)", border:"1px solid var(--warning-border)",
        fontSize:11, color:"var(--warning-text)", marginBottom:12 }}>
        Holiday persistence is local only — backend endpoint for holiday exceptions is not yet implemented.
      </div>

      {holidays.length === 0 ? (
        <div style={{ textAlign:"center", padding:"24px", color:"var(--text-tertiary)" }}>
          <Sun size={24} style={{ opacity:0.25, marginBottom:8 }}/>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 4px" }}>
            No holidays or exceptions yet.
          </p>
          <p style={{ fontSize:12, margin:0 }}>Add holidays to prevent bookings on specific dates.</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {holidays.map(h => (
            <div key={h.id} style={{ display:"flex", alignItems:"center", gap:12,
              padding:"11px 14px", background:"var(--surface-sunken)",
              border:"1px solid var(--border)", borderRadius:9 }}>
              <div style={{ flex:1 }}>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>
                  {safeText(h.reason, "Holiday")}
                </p>
                <div style={{ display:"flex", gap:10, fontSize:11, color:"var(--text-tertiary)" }}>
                  <span>{safeDate(h.date)}</span>
                  <span>{h.type === "closed" ? "Closed" : h.type}</span>
                </div>
              </div>
              <button onClick={() => onDelete(h.id)}
                style={{ padding:"5px 10px", fontSize:11, borderRadius:7,
                  border:"1px solid var(--danger-border)", background:"var(--danger-bg)",
                  color:"var(--danger-text)", cursor:"pointer", fontFamily:"inherit" }}>
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Add Holiday Modal ─────────────────────────────────────────────────────────
function AddHolidayModal({ onClose, onSave }: {
  onClose: () => void;
  onSave: (h: Omit<HolidayEntry, "id">) => void;
}) {
  const [date, setDate] = useState("");
  const [type, setType] = useState("closed");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);

  function save() {
    if (!date) { setErr("Please select a date."); return; }
    if (!reason.trim()) { setErr("Please enter a reason."); return; }
    onSave({ date, type, reason, scope: "all" });
    onClose();
  }

  const inputStyle: React.CSSProperties = {
    width:"100%", padding:"9px 12px", fontSize:13, boxSizing:"border-box",
    border:"1px solid var(--border)", borderRadius:"var(--radius-md)",
    background:"var(--surface)", color:"var(--text-primary)", outline:"none", fontFamily:"inherit",
  };

  return (
    <DsModal open onClose={onClose} title="Add Holiday / Exception"
      footer={<>
        <DsButton variant="secondary" size="sm" onClick={onClose}>Cancel</DsButton>
        <DsButton variant="primary" size="sm" onClick={save}>Add Holiday</DsButton>
      </>}>
      {err && (
        <div style={{ padding:"8px 12px", background:"var(--danger-bg)", border:"1px solid var(--danger-border)",
          borderRadius:"var(--radius-md)", fontSize:12, color:"var(--danger-text)", marginBottom:12 }}>
          {err}
        </div>
      )}

      <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
        <div>
          <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.06em" }}>Date</label>
          <input type="date" value={date} onChange={e => { setDate(e.target.value); setErr(null); }} style={inputStyle}/>
        </div>
        <div>
          <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.06em" }}>Reason</label>
          <input value={reason} onChange={e => { setReason(e.target.value); setErr(null); }}
            placeholder="e.g. Diwali Holiday" style={inputStyle}/>
        </div>
        <div>
          <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.06em" }}>Type</label>
          <select value={type} onChange={e => setType(e.target.value)} style={inputStyle}>
            <option value="closed">Full Day Closed</option>
            <option value="custom">Custom Hours</option>
            <option value="emergency_open">Emergency Open</option>
          </select>
        </div>
      </div>
    </DsModal>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function BusinessHoursPage() {
  const rulesApi    = useApi(useCallback(() => providerAvailabilityApi.list(), []), []);
  const statusApi   = useApi(useCallback(() => providerStatusApi.get(), []), []);
  const staffApi    = useApi(useCallback(() => providerTeamMembersApi.list(), []), []);
  const areasApi    = useApi(useCallback(() => providerServiceAreasApi.list(), []), []);
  const activityApi = useApi(useCallback(() => tenantSetupApi.getActivity(1), []), []);

  const [wizardOpen,    setWizardOpen]    = useState(false);
  const [wizardDayIdx,  setWizardDayIdx]  = useState<number | null>(null);
  const [editRule,      setEditRule]      = useState<ProviderAvailabilityRule | null>(null);
  const [deleteTarget,  setDeleteTarget]  = useState<ProviderAvailabilityRule | null>(null);
  const [presetConfirm, setPresetConfirm] = useState<Preset | null>(null);
  const [removePresetConfirm, setRemovePresetConfirm] = useState<Preset | null>(null);
  const [holidayOpen,   setHolidayOpen]   = useState(false);
  const [holidays,      setHolidays]      = useState<HolidayEntry[]>([]);
  const [toast, setToast] = useState<{ msg: string; type: "success"|"error" } | null>(null);
  const [filterScope,   setFilterScope]   = useState<string>("all");

  const applyingPresetKeyRef  = React.useRef<string | null>(null);
  const removingPresetKeyRef  = React.useRef<string | null>(null);
  const [applyingPresetKey,  setApplyingPresetKey]  = useState<string | null>(null);
  const [removingPresetKey,  setRemovingPresetKey]  = useState<string | null>(null);

  function notify(msg: string, type: "success"|"error" = "success") {
    setToast({ msg, type }); setTimeout(() => setToast(null), 3800);
  }

  const list: ProviderAvailabilityRule[] = rulesApi.data?.rules ?? [];
  const activeRules = list.filter(r => r.is_active);
  const openDays = [...new Set(activeRules.map(r => r.day_of_week))];
  const closedDays = [0,1,2,3,4,5,6].filter(d => !openDays.includes(d));
  /**
   * How many technicians can actually take an assignment.
   *
   * Reuses the `staffApi` this page already loads for its scope picker rather than
   * adding a second fetch of the same team -- one source, so the limit shown here cannot
   * disagree with the limit the booking engine applies.
   */
  const technicianCount = (staffApi.data?.members ?? []).filter(
    (m: { status?: string; can_receive_assignment?: boolean }) =>
      (m.status ?? "active") === "active" && m.can_receive_assignment !== false,
  ).length;

  const issues = detectIssues(list, technicianCount);
  const configuredStatus = activeRules.length > 0 && issues.filter(i=>i.severity==="danger").length === 0;

  const staffOptions = (staffApi.data?.members ?? []).map(m => ({
    id: String(m.member_id),
    name: safeText(m.full_name, "Staff Member"),
  }));
  const areaOptions = (areasApi.data?.areas ?? []).map(a => ({
    id: String(a.id),
    name: safeText(a.city ?? a.zone_name, "Area"),
  }));

  const activities = (() => {
    const d = activityApi.data as unknown as Record<string,unknown> | null;
    if (!d) return [];
    const items = d.events ?? d.activities ?? d.items ?? [];
    return Array.isArray(items) ? (items as unknown[]).slice(0, 6) : [];
  })();

  const deleteAction = useAction(useCallback(async (id: string) => {
    await providerAvailabilityApi.delete(id);
    rulesApi.refetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []));

  function handleSaved() {
    rulesApi.refetch();
    setWizardOpen(false);
    setEditRule(null);
    setWizardDayIdx(null);
    notify(editRule ? "Working hours updated." : "Working hours saved.");
  }

  function openWizardForDay(dayIdx: number) {
    setWizardDayIdx(dayIdx);
    setEditRule(null);
    setWizardOpen(true);
  }

  function openEdit(rule: ProviderAvailabilityRule) {
    setEditRule(rule);
    setWizardDayIdx(null);
    setWizardOpen(true);
  }

  async function applyPreset(preset: Preset) {
    if (preset.id === "custom") {
      setWizardDayIdx(null); setEditRule(null); setWizardOpen(true);
      return;
    }
    if (applyingPresetKeyRef.current) return;
    applyingPresetKeyRef.current = preset.id;
    setApplyingPresetKey(preset.id);
    try {
      let applied = false;
      try {
        await providerAvailabilityApi.applyPreset(preset.id);
        applied = true;
      } catch {
        const matching = list.filter(r =>
          r.start_time === preset.start && r.end_time === preset.end &&
          r.slot_duration_minutes === preset.slotMin && r.scope_type === "provider"
        );
        await Promise.all(matching.map(r => providerAvailabilityApi.delete(r.id)));
        await Promise.all(preset.days.map(d =>
          providerAvailabilityApi.create({
            scope_type: "provider", day_of_week: d,
            start_time: preset.start, end_time: preset.end,
            slot_duration_minutes: preset.slotMin,
            max_bookings_per_slot: preset.maxBookings, is_active: true,
          })
        ));
        applied = true;
      }
      if (applied) {
        await rulesApi.refetch();
        notify(`"${preset.title}" applied — ${preset.days.length} days configured.`);
      }
    } catch(e) {
      notify(e instanceof Error ? e.message : "Preset could not be applied.", "error");
    } finally {
      applyingPresetKeyRef.current = null;
      setApplyingPresetKey(null);
    }
  }

  async function removePreset(preset: Preset) {
    if (removingPresetKeyRef.current) return;
    removingPresetKeyRef.current = preset.id;
    setRemovingPresetKey(preset.id);
    setRemovePresetConfirm(null);
    try {
      try {
        await providerAvailabilityApi.deletePreset(preset.id);
      } catch {
        const matching = list.filter(r =>
          r.start_time === preset.start && r.end_time === preset.end &&
          r.slot_duration_minutes === preset.slotMin && r.scope_type === "provider"
        );
        await Promise.all(matching.map(r => providerAvailabilityApi.delete(r.id)));
      }
      await rulesApi.refetch();
      notify(`"${preset.title}" removed.`);
    } catch(e) {
      notify(e instanceof Error ? e.message : "Could not remove preset.", "error");
    } finally {
      removingPresetKeyRef.current = null;
      setRemovingPresetKey(null);
    }
  }

  const filteredList = filterScope === "all" ? list : list.filter(r => r.scope_type === filterScope);

  return (
    <TenantLayout activeNav="provider-availability">
      <style>{`
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
        .av-grid{display:grid;gap:20px}
      `}</style>

      {/* Toast */}
      {toast && (
        <div style={{ position:"fixed", top:72, right:24, zIndex:9999, maxWidth:380,
          padding:"12px 18px", borderRadius:10, boxShadow:"0 4px 24px rgba(0,0,0,0.15)",
          animation:"fadeIn 0.2s ease",
          background: toast.type === "success" ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.type === "success" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.type === "success" ? "var(--success-text)" : "var(--danger-text)",
          fontSize:13, fontWeight:500, display:"flex", alignItems:"center", gap:8 }}>
          {toast.type === "success" ? <CheckCircle2 size={14}/> : <XCircle size={14}/>}
          {toast.msg}
        </div>
      )}

      {/* 1. BREADCRUMB */}
      <div style={{ display:"flex", alignItems:"center", gap:5, marginBottom:16, fontSize:12,
        color:"var(--text-tertiary)", fontWeight:500 }}>
        <span>Tenant Portal</span>
        <ChevronRight size={12}/>
        <span>Setup</span>
        <ChevronRight size={12}/>
        <span style={{ color:"var(--text-primary)" }}>Business Hours & Availability</span>
      </div>

      {/* 2. PAGE HEADER — flat, matches screenshot */}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
        flexWrap:"wrap", gap:16, marginBottom:20 }}>
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:6 }}>
            <h1 style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
              Business Hours & Availability
            </h1>
            {!rulesApi.loading && (
              <StatusBadge
                active={configuredStatus}
                label={configuredStatus ? "Configured" : activeRules.length > 0 ? "Needs Attention" : "Not Configured"}/>
            )}
          </div>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Set when customers can book your services and preview the booking slots they will see.
          </p>
        </div>
        <div style={{ display:"flex", gap:8, alignItems:"center" }}>
          <button onClick={() => { setEditRule(null); setWizardDayIdx(null); setWizardOpen(true); }}
            style={{ padding:"9px 18px", fontSize:13, fontWeight:600, borderRadius:"var(--radius-md)",
              border:"none", background:"var(--brand)", color:"white",
              cursor:"pointer", fontFamily:"inherit", display:"flex", alignItems:"center", gap:6 }}>
            <Plus size={14}/> Add Working Hours
          </button>
          <button onClick={() => setHolidayOpen(true)}
            style={{ padding:"9px 16px", fontSize:13, fontWeight:500, borderRadius:"var(--radius-md)",
              border:"1px solid var(--border)", background:"var(--surface)",
              color:"var(--text-primary)", cursor:"pointer", fontFamily:"inherit",
              display:"flex", alignItems:"center", gap:6 }}>
            Add Holiday
          </button>
        </div>
      </div>

      <div className="av-grid">

        {/* 3. API ERROR BANNER (only shows on load failure) */}
        {rulesApi.error && (
          <SectionError title="Could not load availability" error={rulesApi.error}
            requestId={rulesApi.requestId} onRetry={rulesApi.refetch}/>
        )}

        {/* 4. QUICK PRESETS */}
        <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow:"hidden" }}>
          <div style={{ padding:"16px 20px 12px", borderBottom:"1px solid var(--border)",
            display:"flex", alignItems:"center", gap:8 }}>
            <Clock size={14} style={{ color:"var(--text-secondary)" }}/>
            <h2 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
              Quick Presets
            </h2>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4, 1fr)" }}>
            {PRESETS.map((p, idx) => {
              const active = isPresetActive(p, list);
              const anyBusy = applyingPresetKeyRef.current !== null || removingPresetKeyRef.current !== null;
              const isThisApplying = applyingPresetKey === p.id;
              const isThisRemoving = removingPresetKey === p.id;
              const ICON_BG = ["rgba(200,200,200,0.12)","rgba(200,200,200,0.12)","rgba(200,200,200,0.12)","rgba(200,200,200,0.12)"];
              return (
                <div key={p.id}
                  onClick={() => {
                    if (anyBusy) return;
                    if (active) { setRemovePresetConfirm(p); return; }
                    if (p.id === "custom") { applyPreset(p); return; }
                    setPresetConfirm(p);
                  }}
                  style={{
                    padding:"18px 20px",
                    borderRight: idx < 3 ? "1px solid var(--border)" : "none",
                    cursor: anyBusy ? "not-allowed" : "pointer",
                    display:"flex", alignItems:"flex-start", gap:14,
                    background: active ? "rgba(22,163,74,0.04)" : "transparent",
                    opacity: anyBusy && !isThisApplying && !isThisRemoving ? 0.6 : 1,
                    transition:"background 0.15s",
                  }}>
                  <div style={{ width:36, height:36, borderRadius:"var(--radius-md)", flexShrink:0,
                    background: active ? "rgba(22,163,74,0.12)" : ICON_BG[idx],
                    border:"1px solid var(--border)",
                    display:"flex", alignItems:"center", justifyContent:"center", fontSize:18 }}>
                    {isThisApplying || isThisRemoving
                      ? <RefreshCw size={14} style={{ animation:"spin 1s linear infinite", color:"var(--text-tertiary)" }}/>
                      : p.icon}
                  </div>
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:3 }}>
                      <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{p.title}</p>
                      {active && (
                        <span style={{ fontSize:10, fontWeight:700, padding:"1px 6px", borderRadius:4,
                          background:"var(--success-bg)", color:"var(--success-text)",
                          border:"1px solid var(--success-border)" }}>Active</span>
                      )}
                    </div>
                    <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0, lineHeight:1.4 }}>{p.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 5. WEEKLY SCHEDULE */}
        {rulesApi.loading ? (
          <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", padding:"20px" }}>
            {[...Array(7)].map((_,i) => (
              <div key={i} style={{ marginBottom:8 }}><DsSkeleton height={52} radius="8px"/></div>
            ))}
          </div>
        ) : (
          <WeeklyScheduleView rules={list} onEdit={openEdit} onAdd={openWizardForDay} onDelete={r => setDeleteTarget(r)}/>
        )}

        {/* 6. SLOT PREVIEW */}
        <SlotPreviewPanel rules={list}/>

        {/* 7–10. BOTTOM GRID */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>

          {/* 7. ALL WORKING HOUR RULES */}
          <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow:"hidden" }}>
            <div style={{ padding:"16px 20px", borderBottom:"1px solid var(--border)",
              display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:10 }}>
              <div>
                <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 2px" }}>
                  All Working Hour Rules
                </p>
                <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                  {list.length} rule{list.length !== 1 ? "s" : ""} configured
                </p>
              </div>
              <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                {["all","provider","offering","staff_member","service_area"].map(s => (
                  <button key={s} onClick={() => setFilterScope(s)}
                    style={{ padding:"3px 9px", fontSize:10, fontWeight:600, borderRadius:7,
                      border:"1px solid", cursor:"pointer", fontFamily:"inherit",
                      borderColor: filterScope === s ? "var(--brand)" : "var(--border)",
                      background: filterScope === s ? "rgba(37,99,235,0.08)" : "var(--surface-sunken)",
                      color: filterScope === s ? "var(--brand)" : "var(--text-secondary)" }}>
                    {s === "all" ? "All" : s === "provider" ? "All Services" : s === "offering" ? "Specific Service" : s === "staff_member" ? "Staff Member" : "Service Area"}
                  </button>
                ))}
              </div>
            </div>

            {rulesApi.loading ? (
              <div style={{ padding:"16px 20px" }}>
                {[...Array(3)].map((_,i) => (
                  <div key={i} style={{ marginBottom:8 }}><DsSkeleton height={40} radius="8px"/></div>
                ))}
              </div>
            ) : filteredList.length === 0 ? (
              <div style={{ textAlign:"center", padding:"28px 20px" }}>
                <Clock size={28} style={{ color:"var(--text-tertiary)", opacity:0.3, marginBottom:8 }}/>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                  No working hour rules yet.
                </p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 12px" }}>
                  Add working hours to create rules for your services.
                </p>
                <button onClick={() => { setEditRule(null); setWizardDayIdx(null); setWizardOpen(true); }}
                  style={{ padding:"7px 16px", fontSize:12, fontWeight:600, borderRadius:"var(--radius-md)",
                    border:"none", background:"var(--brand)", color:"white", cursor:"pointer", fontFamily:"inherit" }}>
                  Add Working Hours
                </button>
              </div>
            ) : (
              <div style={{ overflowX:"auto" }}>
                <table style={{ width:"100%", borderCollapse:"collapse" }}>
                  <thead>
                    <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                      {["Day","Hours","Scope","Status","Actions"].map(h => (
                        <th key={h} style={{ padding:"8px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                          color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                          whiteSpace:"nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredList.map((r, i) => (
                      <tr key={r.id} style={{ borderBottom: i < filteredList.length-1 ? "1px solid var(--border)" : "none" }}>
                        <td style={{ padding:"10px 12px", fontSize:12, fontWeight:700, color:"var(--text-primary)" }}>
                          {DAY_NAMES[r.day_of_week] ?? r.day_of_week}
                        </td>
                        <td style={{ padding:"10px 12px" }}>
                          <span style={{ fontSize:11, fontFamily:"monospace", fontWeight:600, color:"var(--text-primary)" }}>
                            {r.start_time}–{r.end_time}
                          </span>
                        </td>
                        <td style={{ padding:"10px 12px" }}>
                          <span style={{ fontSize:10, padding:"2px 7px", borderRadius:6,
                            background:"var(--surface-sunken)", border:"1px solid var(--border)",
                            color:"var(--text-secondary)" }}>
                            {SCOPE_LABEL[r.scope_type] ?? r.scope_type}
                          </span>
                        </td>
                        <td style={{ padding:"10px 12px" }}>
                          <StatusBadge active={r.is_active} label={r.is_active ? "Active" : "Inactive"}/>
                        </td>
                        <td style={{ padding:"10px 12px" }}>
                          <div style={{ display:"flex", gap:4 }}>
                            <button onClick={() => openEdit(r)}
                              style={{ padding:"3px 9px", fontSize:10, borderRadius:6,
                                border:"1px solid var(--border)", background:"var(--surface-sunken)",
                                color:"var(--text-secondary)", cursor:"pointer", fontFamily:"inherit" }}>
                              <Edit2 size={10}/>
                            </button>
                            <button onClick={() => setDeleteTarget(r)}
                              style={{ padding:"3px 9px", fontSize:10, borderRadius:6,
                                border:"1px solid var(--danger-border)", background:"var(--danger-bg)",
                                color:"var(--danger-text)", cursor:"pointer", fontFamily:"inherit" }}>
                              <Trash2 size={10}/>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 8. HOLIDAYS & EXCEPTIONS */}
          <HolidaysPanel
            holidays={holidays}
            onAdd={() => setHolidayOpen(true)}
            onDelete={id => setHolidays(prev => prev.filter(h => h.id !== id))}
          />
        </div>

        {/* Bottom 2-column for checks + activity */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>

          {/* 9. AVAILABILITY CHECKS */}
          <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", padding:"20px 24px" }}>
            <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px",
              display:"flex", alignItems:"center", gap:8 }}>
              <Shield size={15}/> Availability Checks
            </p>
            <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 14px" }}>
              Validation results for your working hour setup.
            </p>

            {issues.length === 0 ? (
              <div style={{ padding:"12px 14px", background:"var(--success-bg)", border:"1px solid var(--success-border)",
                borderRadius:9, fontSize:12, color:"var(--success-text)", display:"flex", gap:6 }}>
                <CheckCircle2 size={13} style={{ flexShrink:0, marginTop:1 }}/>
                <div>
                  <strong>All checks passing.</strong>{" "}
                  {activeRules.length > 0
                    ? "Customers can see booking slots based on your configured hours."
                    : "Add working hours to enable customer bookings."}
                </div>
              </div>
            ) : (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {issues.map((issue, i) => (
                  <div key={i} style={{ padding:"12px 14px", borderRadius:9,
                    background: issue.severity === "danger" ? "var(--danger-bg)" : "var(--warning-bg)",
                    border: `1px solid ${issue.severity === "danger" ? "var(--danger-border)" : "var(--warning-border)"}` }}>
                    <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:8 }}>
                      <div>
                        <p style={{ fontSize:12, fontWeight:700, margin:"0 0 3px",
                          color: issue.severity === "danger" ? "var(--danger-text)" : "var(--warning-text)",
                          display:"flex", alignItems:"center", gap:5 }}>
                          {issue.severity === "danger" ? <XCircle size={12}/> : <AlertTriangle size={12}/>}
                          {issue.title}
                        </p>
                        <p style={{ fontSize:11, margin:0,
                          color: issue.severity === "danger" ? "var(--danger-text)" : "var(--warning-text)",
                          opacity:0.85 }}>
                          {issue.reason}
                        </p>
                      </div>
                      <button onClick={() => { setEditRule(null); setWizardDayIdx(null); setWizardOpen(true); }}
                        style={{ padding:"3px 9px", fontSize:11, fontWeight:600, borderRadius:7, cursor:"pointer",
                          fontFamily:"inherit", flexShrink:0, whiteSpace:"nowrap",
                          border: `1px solid ${issue.severity === "danger" ? "var(--danger-border)" : "var(--warning-border)"}`,
                          background:"transparent",
                          color: issue.severity === "danger" ? "var(--danger-text)" : "var(--warning-text)" }}>
                        {issue.cta}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 10. RECENT ACTIVITY */}
          <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", padding:"20px 24px" }}>
            <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px",
              display:"flex", alignItems:"center", gap:8 }}>
              <Activity size={15}/> Recent Activity
            </p>
            <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 14px" }}>
              Working hour changes and booking events.
            </p>

            {activityApi.error ? (
              <SectionError title="Could not load activity" error={activityApi.error}
                requestId={activityApi.requestId} onRetry={activityApi.refetch}/>
            ) : activityApi.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(3)].map((_,i) => (
                  <DsSkeleton key={i} height={40} radius="8px"/>
                ))}
              </div>
            ) : activities.length === 0 ? (
              <div style={{ textAlign:"center", padding:"20px", color:"var(--text-tertiary)" }}>
                <Activity size={24} style={{ opacity:0.25, marginBottom:6 }}/>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                  No recent activity found.
                </p>
                <p style={{ fontSize:12, margin:0 }}>Changes to your schedule will appear here.</p>
              </div>
            ) : (
              <div style={{ display:"flex", flexDirection:"column" }}>
                {activities.map((ev: unknown, i: number) => {
                  const e = ev as Record<string, unknown>;
                  return (
                    <div key={i} style={{ display:"flex", gap:10, padding:"10px 0",
                      borderBottom: i < activities.length-1 ? "1px solid var(--border)" : "none" }}>
                      <div style={{ width:28, height:28, borderRadius:"50%",
                        background:"var(--surface-sunken)", border:"1px solid var(--border)",
                        display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
                        <Clock size={11} style={{ color:"var(--text-tertiary)" }}/>
                      </div>
                      <div style={{ flex:1 }}>
                        <p style={{ fontSize:12, fontWeight:500, color:"var(--text-primary)", margin:"0 0 2px" }}>
                          {safeText(e.action ?? e.event_type ?? e.type, "Availability event")}
                        </p>
                        <div style={{ display:"flex", gap:8, fontSize:11, color:"var(--text-tertiary)" }}>
                          <span>{safeDate(e.created_at ?? e.timestamp)}</span>
                          {e.request_id && (
                            <button onClick={() => copyText(String(e.request_id))}
                              style={{ background:"none", border:"none", cursor:"pointer",
                                color:"var(--text-tertiary)", fontSize:11, fontFamily:"inherit",
                                display:"flex", alignItems:"center", gap:3, padding:0 }}>
                              <Copy size={9}/> {String(e.request_id).slice(0,12)}…
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* WIZARD */}
      {wizardOpen && (
        <AvailabilityWizard
          initialDayIdx={wizardDayIdx}
          existingRule={editRule}
          onClose={() => { setWizardOpen(false); setEditRule(null); setWizardDayIdx(null); }}
          onSaved={handleSaved}
          staffOptions={staffOptions}
          areaOptions={areaOptions}
        />
      )}

      {/* DELETE CONFIRM */}
      {deleteTarget && (
        <DeleteConfirm
          rule={deleteTarget}
          onConfirm={async () => {
            const id = deleteTarget.id;
            const result = await deleteAction.execute(id);
            if (result !== null || !deleteAction.error) {
              setDeleteTarget(null);
              notify("Working hours removed.");
            }
          }}
          onCancel={() => setDeleteTarget(null)}
          loading={deleteAction.loading}
        />
      )}

      {/* PRESET CONFIRM MODAL */}
      {presetConfirm && (
        <PresetConfirmModal
          preset={presetConfirm}
          onConfirm={() => { const p = presetConfirm; setPresetConfirm(null); applyPreset(p); }}
          onCancel={() => setPresetConfirm(null)}
          loading={applyingPresetKey === presetConfirm.id}
        />
      )}

      {/* REMOVE PRESET CONFIRM */}
      {removePresetConfirm && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.5)", zIndex:1100,
          display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
          <div style={{ background:"var(--surface)", borderRadius:14, maxWidth:420, width:"100%",
            padding:"24px", border:"1px solid var(--border)", boxShadow:"0 20px 60px rgba(0,0,0,0.2)" }}>
            <div style={{ display:"flex", gap:12, marginBottom:14 }}>
              <AlertTriangle size={20} style={{ color:"var(--warning-text)", flexShrink:0 }}/>
              <div>
                <h3 style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 8px" }}>
                  Remove {removePresetConfirm.title}?
                </h3>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 10px" }}>
                  This will remove all {removePresetConfirm.days.length} working hour slots for this preset.
                </p>
              </div>
            </div>
            <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
              <button onClick={() => setRemovePresetConfirm(null)}
                style={{ padding:"9px 16px", fontSize:13, borderRadius:9, border:"1px solid var(--border)",
                  background:"var(--surface-sunken)", color:"var(--text-primary)", cursor:"pointer", fontFamily:"inherit" }}>
                Cancel
              </button>
              <button onClick={() => removePreset(removePresetConfirm)}
                disabled={removingPresetKey !== null}
                style={{ padding:"9px 16px", fontSize:13, fontWeight:600, borderRadius:9,
                  border:"none", background:"var(--danger)", color:"white", fontFamily:"inherit",
                  cursor: removingPresetKey ? "not-allowed" : "pointer",
                  opacity: removingPresetKey ? 0.7 : 1,
                  display:"flex", alignItems:"center", gap:5 }}>
                {removingPresetKey
                  ? <><RefreshCw size={11} style={{ animation:"spin 1s linear infinite" }}/> Removing…</>
                  : <><Trash2 size={11}/> Remove Rules</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HOLIDAY MODAL */}
      {holidayOpen && (
        <AddHolidayModal
          onClose={() => setHolidayOpen(false)}
          onSave={h => setHolidays(prev => [...prev, { ...h, id: String(Date.now()) }])}
        />
      )}
    </TenantLayout>
  );
}

function HeroMeta({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:2 }}>
      <span style={{ fontSize:10, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.07em" }}>
        {label}
      </span>
      <span style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)" }}>{value}</span>
    </div>
  );
}
