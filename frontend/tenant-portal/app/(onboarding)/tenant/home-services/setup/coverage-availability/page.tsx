"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Plus, Trash2, RefreshCw, Info, MapPin, Scale } from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { TenantLayout } from "../../../../../../components/layout/TenantLayout";
import { ProgressRing } from "../../../../../../components/onboarding/ProgressRing";
import { StepProgressBar } from "../../../../../../components/onboarding/StepProgressBar";
import { Card, Btn, Badge, Skeleton, Input, KpiGrid, SummaryCard } from "../../../../../../components/shared/ui";
import { PageHeader, PageShell } from "@serviceos/design-system";
import {
  providerServiceAreasApi, providerAvailabilityApi, bookingWindowApi, availabilityExceptionsApi,
  ServiceOSError, type ProviderServiceArea, type ProviderAvailabilityRule,
  type BookingWindowSettings, type AvailabilityException,
} from "../../../../../../lib/api";
import { topupApi } from "../../../../../../lib/api-topup";
import { WeeklyScheduleEditor } from "../../../../../../components/availability/WeeklyScheduleEditor";
import { scheduleDraft, schedulePayload, dayError, businessDate, type DayDraft } from "../../../../../../lib/coverage-schedule";

const SETUP_STEPS = [
  "business-profile", "documents", "services-pricing",
  "plan", "staff", "coverage-availability", "finance", "review",
] as const;
const STEP_NUMBER = SETUP_STEPS.indexOf("coverage-availability") + 1;
const TOTAL_STEPS = SETUP_STEPS.length;

const DAYS = [
  { idx: 0, name: "Sunday" }, { idx: 1, name: "Monday" }, { idx: 2, name: "Tuesday" },
  { idx: 3, name: "Wednesday" }, { idx: 4, name: "Thursday" }, { idx: 5, name: "Friday" },
  { idx: 6, name: "Saturday" },
];

function CoverageShell({ mode, children }: { mode: "onboarding" | "workspace"; children: React.ReactNode }) {
  return mode === "workspace"
    ? <TenantLayout activeNav="business-hours"><PageShell>{children}</PageShell></TenantLayout>
    : <OnboardingShell activeNav="coverage-availability"><PageShell>{children}</PageShell></OnboardingShell>;
}

function CoverageAvailabilityWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const mode: "onboarding" | "workspace" = pathname.startsWith("/business/coverage-hours") ? "workspace" : "onboarding";
  const workspace = mode === "workspace";
  const [areas, setAreas] = useState<ProviderServiceArea[] | null>(null);
  const [rules, setRules] = useState<ProviderAvailabilityRule[] | null>(null);
  const [bookingWindow, setBookingWindow] = useState<BookingWindowSettings | null>(null);
  const [days, setDays] = useState<DayDraft[]>([]);
  const [windowDraft, setWindowDraft] = useState<BookingWindowSettings | null>(null);
  const [notice, setNotice] = useState("");
  const [exceptionSaving, setExceptionSaving] = useState(false);
  const [exceptions, setExceptions] = useState<AvailabilityException[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [technicianCapacity, setTechnicianCapacity] = useState<number | null>(null);
  const [previewDay, setPreviewDay] = useState(() => businessDate());
  const [previewLoading, setPreviewLoading] = useState(false);
  const [slotPreview, setSlotPreview] = useState<Awaited<ReturnType<typeof providerAvailabilityApi.slotPreview>> | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [previewRevision, setPreviewRevision] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setPreviewLoading(true);
    setSlotPreview(null);
    const refresh = () => providerAvailabilityApi.slotPreview(previewDay).then(data => {
      if (!cancelled) { setSlotPreview(data); setPreviewError(""); setPreviewLoading(false); }
    }).catch(() => { if (!cancelled) { setSlotPreview(null); setPreviewLoading(false); setPreviewError("Could not load live slots. Try Refresh slots."); } });
    void refresh();
    const timer = setInterval(() => { void refresh(); }, 30000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [previewDay, previewRevision, rules, exceptions]);

  const [newPincode, setNewPincode] = useState("");
  const [addingPincode, setAddingPincode] = useState(false);
  const [pincodeNeedsManualLocation, setPincodeNeedsManualLocation] = useState(false);
  const [manualPincodeCity, setManualPincodeCity] = useState("");
  const [manualPincodeState, setManualPincodeState] = useState("");
  const [newExceptionDate, setNewExceptionDate] = useState("");
  const [newExceptionReason, setNewExceptionReason] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      providerServiceAreasApi.list(),
      providerAvailabilityApi.list(),
      bookingWindowApi.get(),
      availabilityExceptionsApi.list(),
      topupApi.status(),
    ])
      .then(([a, r, bw, ex, seats]) => {
        setTechnicianCapacity(Math.min(seats.entitled_seats, seats.used_seats));
        setAreas(a.areas);
        setRules(r.rules);
        setDays(scheduleDraft(r.rules));
        setBookingWindow(bw);
        setWindowDraft(bw);
        setExceptions(ex.exceptions);
      })
      .catch((err: unknown) => setError(err instanceof ServiceOSError ? err.message : "We couldn't load your coverage and availability settings."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const activePincodes = useMemo(() => (areas ?? []).filter(a => a.coverage_type === "zipcode" && a.is_active), [areas]);
  const activeCoverageCount = activePincodes.length;
  const rulesByDay = useMemo(() => {
    const map = new Map<number, ProviderAvailabilityRule>();
    for (const r of rules ?? []) if (r.is_active && r.scope_type === "provider" && !r.scope_id) map.set(r.day_of_week, r);
    return map;
  }, [rules]);
  const openDaysCount = rulesByDay.size;
  const bufferMinutes = Math.max(0, Number(windowDraft?.buffer_minutes_between_jobs) || 0);
  const hasUnsavedChanges = JSON.stringify(days) !== JSON.stringify(scheduleDraft(rules ?? [])) || JSON.stringify(windowDraft) !== JSON.stringify(bookingWindow);
  const dayErrors = days.map(day => dayError(day, technicianCapacity ?? 0, bufferMinutes));
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasUnsavedChanges]);

  async function handleAddPincode() {
    const pin = newPincode.trim();
    if (!/^\d{6}$/.test(pin)) {
      setError("Enter a valid 6-digit pincode.");
      return;
    }
    if (activePincodes.some(a => a.zipcode === pin)) {
      setError("This pincode is already in your coverage list.");
      return;
    }
    const manualCity = manualPincodeCity.trim();
    const manualState = manualPincodeState.trim();
    if (pincodeNeedsManualLocation && (!manualCity || !manualState)) {
      setError("Enter the city and state for this pincode.");
      return;
    }
    setAddingPincode(true);
    setError(null);
    try {
      const validation = await providerServiceAreasApi.validate({
        coverage_type: "zipcode", zipcode: pin,
        ...(pincodeNeedsManualLocation ? { city: manualCity, state: manualState } : {}),
      });
      if (!validation.coverage_valid || !validation.resolved_city || !validation.resolved_state) {
        if (!pincodeNeedsManualLocation) {
          // Auto-resolution (our small pincode lookup table) doesn't cover this
          // pincode. Fall back to letting the tenant confirm the city/state
          // manually instead of dead-ending on a raw backend error.
          setPincodeNeedsManualLocation(true);
          setError("We couldn't auto-detect this pincode's locality. Enter the city and state below to continue.");
          return;
        }
        setError(validation.coverage_error || "This pincode could not be resolved to a valid locality.");
        return;
      }
      if (validation.is_duplicate) {
        setError("This pincode is already in your coverage list.");
        return;
      }
      const created = await providerServiceAreasApi.create({
        coverage_type: "zipcode", zipcode: pin, country: "India",
        city: validation.resolved_city, state: validation.resolved_state, district: validation.resolved_district ?? undefined,
      });
      setAreas(list => [...(list ?? []), created]);
      setNewPincode("");
      setPincodeNeedsManualLocation(false);
      setManualPincodeCity("");
      setManualPincodeState("");
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not add this pincode.");
    } finally {
      setAddingPincode(false);
    }
  }

  async function handleRemovePincode(id: string) {
    setError(null);
    try {
      await providerServiceAreasApi.delete(id);
      setAreas(list => (list ?? []).filter(a => a.id !== id));
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not remove this pincode.");
    }
  }

  function editDay(dayIdx: number, values: Partial<DayDraft>) {
    setDays(previous => previous.map(day => day.day_of_week === dayIdx ? { ...day, ...values } : day));
    setNotice("");
  }

  function handleCopyMondayToWeekdays() {
    const monday = days.find(day => day.day_of_week === 1);
    if (!monday?.is_active) { setError("Open Monday and configure its hours first."); return; }
    const invalid = dayError(monday, technicianCapacity ?? 0, bufferMinutes);
    if (invalid) { setError(`Monday: ${invalid}`); return; }
    setDays(previous => previous.map(day => [2, 3, 4, 5].includes(day.day_of_week)
      ? { ...monday, day_of_week: day.day_of_week } : day));
    setError(null); setNotice("Monday's hours, break and daily limit copied to Tuesday–Friday. Save to apply.");
  }

  function handleBookingWindowChange(field: string, value: string | boolean) {
    setWindowDraft(previous => ({ ...previous, [field]: value }));
    setNotice("");
  }

  async function saveSchedule(): Promise<boolean> {
    if (!windowDraft) return false;
    setError(null); setNotice("");
    const invalidIndex = dayErrors.findIndex(Boolean);
    if (invalidIndex >= 0) {
      setError(`${DAYS[invalidIndex].name}: ${dayErrors[invalidIndex]}`);
      document.getElementById(`schedule-day-${invalidIndex}`)?.scrollIntoView({ block: "center" });
      return false;
    }
    const controls = { ...windowDraft, slot_duration_minutes: 120 };
    for (const [key, minimum, maximum] of [
      ["minimum_notice_minutes", 0, 43200], ["maximum_advance_booking_days", 1, 62],
      ["buffer_minutes_between_jobs", 0, 1440],
    ] as const) {
      const value = Number(windowDraft[key]);
      if (windowDraft[key] === "" || !Number.isInteger(value) || value < minimum || value > maximum) {
        setError(`${key.replaceAll("_", " ")} must be a whole number between ${minimum} and ${maximum}.`);
        return false;
      }
      controls[key] = value;
    }
    setSaving(true);
    try {
      const result = await providerAvailabilityApi.saveSchedule({ rules: schedulePayload(days), booking_window: controls });
      setRules(result.rules); setDays(scheduleDraft(result.rules));
      setBookingWindow(result.booking_window); setWindowDraft(result.booking_window);
      setNotice("Business hours and booking controls saved. Technician schedules and customer slots now use these settings.");
      setPreviewRevision(value => value + 1);
      window.dispatchEvent(new Event("home-services-setup-updated"));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your schedule. Your edits are still here; please retry.");
      return false;
    } finally { setSaving(false); }
  }

  async function handleAddException() {
    if (!newExceptionDate || !newExceptionReason.trim()) {
      setError("Enter a date and a reason for the exception.");
      return;
    }
    if (newExceptionDate < businessDate(String(windowDraft?.timezone || "Asia/Kolkata"))) { setError("Choose today or a future closure date."); return; }
    if ((exceptions ?? []).some(ex => ex.date === newExceptionDate)) { setError("A closure is already configured for this date."); return; }
    setError(null);
    setExceptionSaving(true);
    try {
      const created = await availabilityExceptionsApi.create({
        date: newExceptionDate, reason: newExceptionReason.trim(), full_day_closed: true,
      });
      setExceptions(list => [...(list ?? []), created]);
      setNewExceptionDate(""); setNewExceptionReason("");
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not add this exception.");
    } finally { setExceptionSaving(false); }
  }

  async function handleRemoveException(id: string) {
    setError(null);
    try {
      await availabilityExceptionsApi.delete(id);
      setExceptions(list => (list ?? []).filter(e => e.id !== id));
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not remove this exception.");
    }
  }

  function handleBack() {
    if (hasUnsavedChanges && !confirm("Leave without saving the schedule changes?")) return;
    router.push(workspace ? "/dashboard" : "/tenant/home-services/setup/staff");
  }

  async function handleSaveDraft() { await saveSchedule(); }

  async function handleSaveAndContinue() {
    if (activeCoverageCount === 0) { setError("Add at least one coverage pincode before continuing."); return; }
    if (!days.some(day => day.is_active)) { setError("Configure at least one open day before continuing."); return; }
    if (await saveSchedule()) router.push(workspace ? "/dashboard" : "/tenant/home-services/setup/finance");
  }

  const readinessChecks = [
    { label: "Pincodes added", done: activeCoverageCount > 0 },
    { label: "Hours configured", done: openDaysCount > 0 },
    { label: "Booking controls configured", done: !!bookingWindow },
  ];
  const readinessPct = Math.round((readinessChecks.filter(c => c.done).length / readinessChecks.length) * 100);
  const isReady = readinessChecks.every(c => c.done);

  if (loading) {
    return (
      <CoverageShell mode={mode}>
        <PageHeader title={workspace ? "Coverage & hours" : "Coverage & availability"} description="Manage the pincodes, weekly hours, booking rules, and closures used by customer booking and provider matching." />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))", gap: 20 }}>
          <Skeleton height={520}/><Skeleton height={520}/>
        </div>
      </CoverageShell>
    );
  }

  if (error && !areas) {
    return (
      <CoverageShell mode={mode}>
        <PageHeader title={workspace ? "Coverage & hours" : "Coverage & availability"} description="Manage the pincodes, weekly hours, booking rules, and closures used by customer booking and provider matching." />
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your coverage and availability settings.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </CoverageShell>
    );
  }

  if (!areas || !rules || !bookingWindow || !windowDraft) return null;

  return (
    <CoverageShell mode={mode}>
      <PageHeader
        title={workspace ? "Coverage & hours" : "Coverage & availability"}
        description="Manage the pincodes, weekly hours, booking rules, and closures used by customer booking and provider matching."
        actions={<div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <Badge variant={isReady ? "success" : "warning"} size="lg">
            {isReady ? (workspace ? "Coverage setup ready" : "Ready for review") : "Setup incomplete"}
          </Badge>
          {workspace && <Btn variant="secondary" size="sm" disabled={saving || hasUnsavedChanges} icon={<RefreshCw size={14}/>} onClick={load}>Refresh</Btn>}
        </div>}
      />

      {!workspace && <StepProgressBar step={STEP_NUMBER} total={TOTAL_STEPS} />}
      {notice && <div role="status" className="cov-notice">{notice}</div>}

      {workspace && (
        <KpiGrid minCardWidth={190}>
          <SummaryCard label="Active pincodes" value={activePincodes.length} sub="Customer bookable areas" icon={<MapPin/>} tone={activePincodes.length ? "success" : "warning"}/>
          <SummaryCard label="Open days" value={`${openDaysCount}/7`} sub="Weekly business schedule" icon={<Info/>} tone={openDaysCount ? "success" : "warning"}/>
          <SummaryCard label="Notice window" value={`${bookingWindow.minimum_notice_minutes} min`} sub={`${bookingWindow.maximum_advance_booking_days} days advance`} icon={<Scale/>} tone="info"/>
          <SummaryCard label="Exceptions" value={(exceptions ?? []).length} sub="Upcoming closures" icon={<Plus/>} tone={(exceptions ?? []).length ? "warning" : "success"}/>
        </KpiGrid>
      )}

      {error && (
        <div role="alert" style={{
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
          padding: "10px 14px", marginTop: 14, background: "var(--danger-bg)",
          border: "1px solid var(--danger-border)", borderRadius: "var(--radius-md)",
        }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{error}</p>
          <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>Dismiss</button>
        </div>
      )}

      <style>{`
        .cov-grid { display: grid; grid-template-columns: minmax(0,1fr) 280px; gap: 20px; align-items: start; margin-top: 20px; padding-bottom: 20px; }
        @media (max-width: 1000px) { .cov-grid { grid-template-columns: 1fr; } }
        .cov-day-row { border:1px solid var(--border); border-radius:12px; padding:14px; margin-top:10px; background:var(--surface); }
        .cov-day-head { display:flex; align-items:center; justify-content:space-between; gap:12px; }
        .cov-day-head label { display:flex; align-items:center; gap:9px; min-height:32px; font-size:13px; cursor:pointer; }
        .cov-day-head input { width:18px; height:18px; accent-color:var(--brand); }
        .cov-fields { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:14px; }
        .cov-field { display:flex; flex-direction:column; gap:6px; font-size:12px; color:var(--text-secondary); }
        .cov-field input, .cov-date { width:100%; min-width:0; height:40px; padding:0 10px; border:1px solid var(--border); border-radius:8px; background:var(--surface-sunken); color:var(--text-primary); font:inherit; box-sizing:border-box; }
        .cov-field input:focus-visible, .cov-date:focus-visible { outline:2px solid var(--brand); outline-offset:2px; }
        .cov-day-error { color:var(--danger-text); font-size:12px; margin:10px 0 0; }
        .cov-chips { display:flex; gap:7px; flex-wrap:wrap; margin-top:12px; }
        .cov-chips span { padding:6px 9px; background:var(--accent-muted); color:var(--text-primary); border-radius:8px; font-size:11px; }
        .cov-hint { font-size:12px; color:var(--text-secondary); line-height:1.6; }
        .cov-notice { padding:12px 14px; margin-top:16px; border-radius:10px; background:var(--accent-muted); font-size:13px; }
        .cov-preview-tools { display:flex; align-items:end; gap:12px; flex-wrap:wrap; margin:14px 0; }
        .cov-slots { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; }
        .cov-slot { padding:12px; border:1px solid var(--border); border-radius:10px; display:flex; flex-direction:column; gap:6px; font-size:12px; }
        .cov-save-bar { position:sticky; bottom:0; z-index:5; display:flex; gap:10px; justify-content:space-between; align-items:center; flex-wrap:wrap; padding:14px 18px; margin-top:20px; background:var(--surface); border:1px solid var(--border); border-radius:12px; box-shadow:var(--shadow-sm); }
        .cov-save-bar>div { display:flex; gap:8px; flex-wrap:wrap; }
        @media (max-width: 640px) { .cov-fields { grid-template-columns:1fr 1fr; } .cov-fields>.cov-field:last-child { grid-column:1/-1; } .cov-grid { gap:14px; } .cov-save-bar>div { width:100%; } .cov-save-bar>div>button { flex:1; } }
      `}</style>

      <div className="cov-grid">
        <div style={{ minWidth: 0 }}>
          <Card style={{ marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Coverage pincodes</h2>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>
              Add the exact pincodes where your team accepts Home Services bookings.
            </p>

            <div style={{ display: "flex", gap: 10, marginBottom: pincodeNeedsManualLocation ? 10 : 16 }}>
              <div style={{ flex: 1 }}>
                <Input placeholder="Enter 6-digit pincode" value={newPincode} onChange={v => {
                  setNewPincode(v);
                  setPincodeNeedsManualLocation(false);
                  setManualPincodeCity("");
                  setManualPincodeState("");
                }} icon={<MapPin size={14}/>}/>
              </div>
              <Btn variant="primary" icon={<Plus size={14}/>} loading={addingPincode} onClick={handleAddPincode}>Add pincode</Btn>
            </div>
            {pincodeNeedsManualLocation && (
              <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                <div style={{ flex: 1 }}>
                  <Input placeholder="City" value={manualPincodeCity} onChange={setManualPincodeCity}/>
                </div>
                <div style={{ flex: 1 }}>
                  <Input placeholder="State" value={manualPincodeState} onChange={setManualPincodeState}/>
                </div>
              </div>
            )}
            {activePincodes.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No pincodes added yet. Add at least one to accept bookings.</p>
            ) : (
              <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
                {activePincodes.map((a, i) => (
                  <div key={a.id} style={{
                    display: "grid", gridTemplateColumns: "minmax(0,1fr) auto auto", gap: 12, alignItems: "center", padding: "10px 14px",
                    borderBottom: i < activePincodes.length - 1 ? "1px solid var(--border)" : "none",
                  }}>
                    <span style={{ minWidth: 0 }}>
                      <span style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 700 }}>{a.zipcode}</span>
                      {a.city && <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginLeft: 8 }}>{a.city}{a.state ? `, ${a.state}` : ""}</span>}
                    </span>
                    <Badge variant="success">Active</Badge>
                    <button aria-label={`Remove coverage for ${a.zipcode}`} onClick={() => handleRemovePincode(a.id)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", display: "flex" }}>
                      <Trash2 size={15}/>
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
              <Info size={13} style={{ color: "var(--text-tertiary)" }}/>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Coverage controls eligibility, not pricing.</p>
            </div>
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4, flexWrap: "wrap", gap: 8 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Weekly business hours</h2>
              <Btn variant="secondary" size="sm" disabled={saving} onClick={handleCopyMondayToWeekdays}>Copy Monday to weekdays</Btn>
            </div>
            <WeeklyScheduleEditor days={days} capacity={technicianCapacity ?? 0} buffer={bufferMinutes} timezone={String(windowDraft.timezone)} saving={saving} onChange={editDay}/>
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>Live booking places</h2>
            <p className="cov-hint">Saved schedule capacity, including existing bookings. Customer choices also depend on minimum notice and the advance-booking window. Only technicians with verified required documents contribute to live booking capacity.</p>
            {hasUnsavedChanges && <p className="cov-day-error">Save your edits to update the live preview below.</p>}
            <div className="cov-preview-tools"><label className="cov-field">Preview date<input className="cov-date" type="date" value={previewDay} onChange={e => { if (e.target.value) setPreviewDay(e.target.value); }}/></label>
              <Btn variant="secondary" disabled={previewLoading} onClick={() => setPreviewRevision(n => n + 1)}>Refresh slots</Btn></div>
            {previewError && <p role="alert">{previewError}</p>}
            {previewLoading ? <p role="status">Loading saved booking capacity…</p> : slotPreview && (slotPreview.closed ? <p>Closed day or holiday — no slots available.</p> : <>
              <p className="cov-hint">{slotPreview.daily_remaining} booking places remaining this day. Counts refresh every 30 seconds.</p>
              <div className="cov-slots">{slotPreview.slots.map(slot => <div className="cov-slot" key={slot.time_window}><strong>{slot.time_window}</strong><span>{slot.available_slots} places available</span><small>{slot.already_booked} booked / {slot.capacity} capacity</small></div>)}</div>
              {slotPreview.slots.length === 0 && <p>No complete slots. Check hours, breaks, travel buffer and funded technicians.</p>}
            </>)}
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: "20px 0 14px", color: "var(--text-primary)" }}>Booking controls</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
              <Input label="Minimum notice (minutes)" type="number" disabled={saving} value={String(windowDraft.minimum_notice_minutes)}
                onChange={v => handleBookingWindowChange("minimum_notice_minutes", v)}/>
              <Input label="Advance booking (days)" type="number" disabled={saving} value={String(windowDraft.maximum_advance_booking_days)}
                onChange={v => handleBookingWindowChange("maximum_advance_booking_days", v)}/>
              <Input label="Travel buffer (minutes)" type="number" disabled={saving} value={String(windowDraft.buffer_minutes_between_jobs)}
                onChange={v => handleBookingWindowChange("buffer_minutes_between_jobs", v)}/>
            </div>
            <div style={{ display: "flex", gap: 20, marginTop: 16, flexWrap: "wrap" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                <input type="checkbox" disabled={saving} checked={windowDraft.allow_same_day_booking}
                  onChange={e => handleBookingWindowChange("allow_same_day_booking", e.target.checked)}/>
                Same-day booking enabled
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                <input type="checkbox" disabled={saving} checked={windowDraft.emergency_booking_allowed}
                  onChange={e => handleBookingWindowChange("emergency_booking_allowed", e.target.checked)}/>
                Emergency booking enabled
              </label>
              <p className="cov-hint">Notice hides slots that start too soon. Advance booking limits how far ahead customers can book. Emergency booking waives notice only during open hours; holidays and capacity still apply.</p>
            </div>
          </Card>

          <Card>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Schedule exceptions</h2>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>Add holidays or one-time closures.</p>
            <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <input type="date" disabled={exceptionSaving} aria-label="Exception date" min={businessDate(String(windowDraft.timezone || "Asia/Kolkata"))} value={newExceptionDate} onChange={e => setNewExceptionDate(e.target.value)}
                style={{ height: 38, padding: "0 10px", fontSize: 13, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)" }}/>
              <div style={{ flex: 1, minWidth: 160 }}>
                <Input disabled={exceptionSaving} placeholder="Reason (e.g. Independence Day)" value={newExceptionReason} onChange={setNewExceptionReason}/>
              </div>
              <Btn variant="secondary" loading={exceptionSaving} icon={<Plus size={14}/>} onClick={handleAddException}>Add exception</Btn>
            </div>
            {(exceptions ?? []).length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No upcoming exceptions.</p>
            ) : (exceptions ?? []).map(ex => (
              <div key={ex.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{ex.date} · {ex.full_day_closed ? "Closed" : "Custom hours"} · {ex.reason}</span>
                <button aria-label={`Remove schedule exception for ${ex.date}`} onClick={() => handleRemoveException(ex.id)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", display: "flex" }}>
                  <Trash2 size={15}/>
                </button>
              </div>
            ))}
          </Card>
        </div>

        <div style={{ minWidth: 0 }}>
          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>{workspace ? "Coverage setup readiness" : "Setup readiness"}</h3>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
              <ProgressRing pct={readinessPct} tone={isReady ? "success" : "brand"} />
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {readinessChecks.map(c => (
                <li key={c.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                  <span style={{ width: 14, height: 14, borderRadius: "50%", flexShrink: 0, background: c.done ? "var(--success)" : "transparent", border: c.done ? "none" : "1px solid var(--border-strong)" }}/>
                  <span style={{ color: c.done ? "var(--text-primary)" : "var(--text-tertiary)" }}>{c.label}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>Coverage summary</h3>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--accent-muted)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)" }}>
                <MapPin size={18}/>
              </div>
              <div>
                <p style={{ fontSize: 22, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>{activeCoverageCount}</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                  Active pincodes
                </p>
              </div>
            </div>
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>Availability summary</h3>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 6px" }}>{openDaysCount} of 7 days open</p>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              Same-day booking: {bookingWindow.allow_same_day_booking ? "Enabled" : "Disabled"} · Advance limit: {bookingWindow.maximum_advance_booking_days} days
            </p>
          </Card>

          <Card>
            <div style={{ display: "flex", gap: 10 }}>
              <Scale size={16} style={{ color: "var(--brand)", flexShrink: 0, marginTop: 2 }}/>
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>Matching impact</h3>
                <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0 }}>
                  Only providers who pass your coverage and availability rules enter ranking for matching.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <div className="cov-save-bar">
        <span role="status" className="cov-hint">{saving ? "Saving schedule…" : hasUnsavedChanges ? "Unsaved hours or booking controls" : "No unsaved schedule changes"}</span>
        <div>
          <Btn variant="secondary" disabled={saving} onClick={handleBack}>Back</Btn>
          <Btn variant="secondary" disabled={saving || !hasUnsavedChanges} onClick={() => { setDays(scheduleDraft(rules)); setWindowDraft(bookingWindow); setError(null); setNotice(""); }}>Discard edits</Btn>
          <Btn variant={workspace ? "primary" : "secondary"} loading={saving} onClick={handleSaveDraft}>{workspace ? "Save changes" : "Save draft"}</Btn>
          {!workspace && <Btn variant="primary" loading={saving} onClick={handleSaveAndContinue}>Save &amp; continue</Btn>}
        </div>
      </div>
    </CoverageShell>
  );
}

export default function CoverageAvailabilityPage() {
  return <CoverageAvailabilityWorkspace/>;
}
