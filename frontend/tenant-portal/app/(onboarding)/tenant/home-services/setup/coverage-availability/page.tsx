"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, RefreshCw, Info, MapPin, Scale } from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { ProgressRing } from "../../../../../../components/onboarding/ProgressRing";
import { StepProgressBar } from "../../../../../../components/onboarding/StepProgressBar";
import { Card, Btn, Badge, Skeleton, Input } from "../../../../../../components/shared/ui";
import {
  providerServiceAreasApi, providerAvailabilityApi, bookingWindowApi, availabilityExceptionsApi,
  homeServicesSetupApi, ServiceOSError, type ProviderServiceArea, type ProviderAvailabilityRule,
  type BookingWindowSettings, type AvailabilityException,
} from "../../../../../../lib/api";

const SETUP_STEPS = [
  "overview", "business-profile", "documents", "services-pricing",
  "coverage-availability", "staff", "finance", "review",
] as const;
const STEP_NUMBER = SETUP_STEPS.indexOf("coverage-availability") + 1;
const TOTAL_STEPS = SETUP_STEPS.length;

const DAYS = [
  { idx: 0, name: "Sunday" }, { idx: 1, name: "Monday" }, { idx: 2, name: "Tuesday" },
  { idx: 3, name: "Wednesday" }, { idx: 4, name: "Thursday" }, { idx: 5, name: "Friday" },
  { idx: 6, name: "Saturday" },
];

export default function CoverageAvailabilityPage() {
  const router = useRouter();
  const [areas, setAreas] = useState<ProviderServiceArea[] | null>(null);
  const [rules, setRules] = useState<ProviderAvailabilityRule[] | null>(null);
  const [bookingWindow, setBookingWindow] = useState<BookingWindowSettings | null>(null);
  const [exceptions, setExceptions] = useState<AvailabilityException[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [coverageMode, setCoverageMode] = useState<"pincode" | "radius">("pincode");
  const [newPincode, setNewPincode] = useState("");
  const [addingPincode, setAddingPincode] = useState(false);
  const [pincodeNeedsManualLocation, setPincodeNeedsManualLocation] = useState(false);
  const [manualPincodeCity, setManualPincodeCity] = useState("");
  const [manualPincodeState, setManualPincodeState] = useState("");
  const [radiusLat, setRadiusLat] = useState("");
  const [radiusLng, setRadiusLng] = useState("");
  const [radiusKm, setRadiusKm] = useState("");
  const [radiusCity, setRadiusCity] = useState("");
  const [radiusState, setRadiusState] = useState("");
  const [addingRadius, setAddingRadius] = useState(false);
  const [savingWindow, setSavingWindow] = useState(false);
  const [newExceptionDate, setNewExceptionDate] = useState("");
  const [newExceptionReason, setNewExceptionReason] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      providerServiceAreasApi.list(),
      providerAvailabilityApi.list(),
      bookingWindowApi.get(),
      availabilityExceptionsApi.list(),
    ])
      .then(([a, r, bw, ex]) => {
        setAreas(a.areas);
        setRules(r.rules);
        setBookingWindow(bw);
        setExceptions(ex.exceptions);
      })
      .catch((err: unknown) => setError(err instanceof ServiceOSError ? err.message : "We couldn't load your coverage and availability settings."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const activePincodes = useMemo(() => (areas ?? []).filter(a => a.coverage_type === "zipcode" && a.is_active), [areas]);
  const activeRadiusAreas = useMemo(() => (areas ?? []).filter(a => a.coverage_type === "radius" && a.is_active), [areas]);
  const activeCoverageCount = activePincodes.length + activeRadiusAreas.length;
  const rulesByDay = useMemo(() => {
    const map = new Map<number, ProviderAvailabilityRule>();
    for (const r of rules ?? []) if (r.is_active) map.set(r.day_of_week, r);
    return map;
  }, [rules]);
  const openDaysCount = rulesByDay.size;

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

  async function handleAddRadius() {
    const lat = Number(radiusLat), lng = Number(radiusLng), km = Number(radiusKm);
    if (!radiusLat || !radiusLng || !radiusKm || Number.isNaN(lat) || Number.isNaN(lng) || Number.isNaN(km)) {
      setError("Enter a valid latitude, longitude and radius.");
      return;
    }
    if (km <= 0 || km > 200) {
      setError("Radius must be greater than 0 and no more than 200 km.");
      return;
    }
    if (!radiusCity.trim() || !radiusState.trim()) {
      setError("Enter the city and state for this operating location.");
      return;
    }
    setAddingRadius(true);
    setError(null);
    try {
      const validation = await providerServiceAreasApi.validate({ coverage_type: "radius", latitude: lat, longitude: lng, radius_km: km });
      if (!validation.coverage_valid) {
        setError(validation.coverage_error || "This radius zone could not be validated.");
        return;
      }
      const created = await providerServiceAreasApi.create({
        coverage_type: "radius", latitude: lat, longitude: lng, radius_km: km,
        city: validation.resolved_city ?? radiusCity.trim(), state: validation.resolved_state ?? radiusState.trim(),
        country: "India",
      });
      setAreas(list => [...(list ?? []), created]);
      setRadiusLat(""); setRadiusLng(""); setRadiusKm(""); setRadiusCity(""); setRadiusState("");
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not add this radius zone.");
    } finally {
      setAddingRadius(false);
    }
  }

  async function handleToggleDay(dayIdx: number, enabled: boolean) {
    setError(null);
    const existing = rulesByDay.get(dayIdx);
    try {
      if (enabled) {
        if (existing) {
          const updated = await providerAvailabilityApi.update(existing.id, { is_active: true });
          setRules(list => (list ?? []).map(r => r.id === updated.id ? updated : r));
        } else {
          const created = await providerAvailabilityApi.create({
            scope_type: "provider", day_of_week: dayIdx, start_time: "09:00", end_time: "18:00",
          });
          setRules(list => [...(list ?? []), created]);
        }
      } else if (existing) {
        const updated = await providerAvailabilityApi.update(existing.id, { is_active: false });
        setRules(list => (list ?? []).map(r => r.id === updated.id ? updated : r));
      }
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not update this day's schedule.");
    }
  }

  async function handleTimeChange(dayIdx: number, field: "start_time" | "end_time", value: string) {
    const existing = rulesByDay.get(dayIdx);
    if (!existing) return;
    try {
      const updated = await providerAvailabilityApi.update(existing.id, { [field]: value });
      setRules(list => (list ?? []).map(r => r.id === updated.id ? updated : r));
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not update the schedule time.");
    }
  }

  async function handleCopyMondayToWeekdays() {
    const monday = rulesByDay.get(1);
    if (!monday) { setError("Configure Monday's hours first."); return; }
    setError(null);
    try {
      for (const dayIdx of [2, 3, 4, 5]) {
        const existing = rulesByDay.get(dayIdx);
        if (existing) {
          await providerAvailabilityApi.update(existing.id, { start_time: monday.start_time, end_time: monday.end_time, is_active: true });
        } else {
          await providerAvailabilityApi.create({ scope_type: "provider", day_of_week: dayIdx, start_time: monday.start_time, end_time: monday.end_time });
        }
      }
      const r = await providerAvailabilityApi.list();
      setRules(r.rules);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not copy Monday's hours.");
    }
  }

  async function handleBookingWindowChange(field: keyof BookingWindowSettings, value: string | boolean | number) {
    if (!bookingWindow) return;
    const next = { ...bookingWindow, [field]: value };
    setBookingWindow(next);
    setSavingWindow(true);
    try {
      const updated = await bookingWindowApi.update({ [field]: value });
      setBookingWindow(updated);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save booking controls.");
    } finally {
      setSavingWindow(false);
    }
  }

  async function handleAddException() {
    if (!newExceptionDate || !newExceptionReason.trim()) {
      setError("Enter a date and a reason for the exception.");
      return;
    }
    setError(null);
    try {
      const created = await availabilityExceptionsApi.create({
        date: newExceptionDate, reason: newExceptionReason.trim(), full_day_closed: true,
      });
      setExceptions(list => [...(list ?? []), created]);
      setNewExceptionDate(""); setNewExceptionReason("");
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not add this exception.");
    }
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
    router.push("/tenant/home-services/setup/services-pricing");
  }

  async function handleSaveDraft() {
    setSaving(true);
    try {
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveAndContinue() {
    if (activeCoverageCount === 0) {
      setError("Add at least one coverage area before continuing.");
      return;
    }
    if (openDaysCount === 0) {
      setError("Configure at least one open day before continuing.");
      return;
    }
    setSaving(true);
    try {
      // Publishing a service requires an active coverage area
      // (admin_catalog/tenant_service.py::publish_service), and Services &
      // Pricing (step 4) runs before this step -- so no service configured
      // there could ever be published yet. This is the first point in the
      // flow both requirements (pricing + coverage) are met, so eligible
      // draft services are published here rather than staying in draft
      // forever with no other trigger anywhere in onboarding.
      const { services } = await homeServicesSetupApi.listEnabled();
      const publishErrors: string[] = [];
      for (const svc of services) {
        if (svc.setup_status === "published") continue;
        try {
          await homeServicesSetupApi.publish(svc.tenant_service_id);
        } catch (err) {
          const name = svc.tenant_display_name ?? "A service";
          publishErrors.push(err instanceof ServiceOSError ? `${name}: ${err.message}` : `${name}: could not be published.`);
        }
      }
      if (publishErrors.length) {
        setError(`Some services still need attention before they can be published: ${publishErrors.join(" ")}`);
        return;
      }
      router.push("/tenant/home-services/setup/staff");
    } finally {
      setSaving(false);
    }
  }

  const readinessChecks = [
    { label: "Coverage added", done: activeCoverageCount > 0 },
    { label: "Hours configured", done: openDaysCount > 0 },
    { label: "Booking controls configured", done: !!bookingWindow },
  ];
  const readinessPct = Math.round((readinessChecks.filter(c => c.done).length / readinessChecks.length) * 100);
  const isReady = readinessChecks.every(c => c.done);

  if (loading) {
    return (
      <OnboardingShell activeNav="coverage-availability">
        <Skeleton height={70} style={{ marginBottom: 20 }}/>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
          <Skeleton height={520}/><Skeleton height={520}/>
        </div>
      </OnboardingShell>
    );
  }

  if (error && !areas) {
    return (
      <OnboardingShell activeNav="coverage-availability">
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your coverage and availability settings.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  if (!areas || !rules || !bookingWindow) return null;

  return (
    <OnboardingShell activeNav="coverage-availability">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginBottom: 4 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 4px" }}>TENANT ONBOARDING</p>
          <h1 style={{ fontSize: 32, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>Coverage &amp; availability</h1>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "6px 0 0" }}>Define where and when your business accepts Home Services bookings.</p>
        </div>
        <Badge variant={isReady ? "success" : "warning"} size="lg">{isReady ? "Ready for bookings" : "Setup incomplete"}</Badge>
      </div>

      <StepProgressBar step={STEP_NUMBER} total={TOTAL_STEPS} />

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
        .cov-grid { display: grid; grid-template-columns: minmax(0,1fr) 380px; gap: 28px; align-items: start; margin-top: 20px; }
        @media (max-width: 1000px) { .cov-grid { grid-template-columns: 1fr; } }
        .cov-day-row { display: grid; grid-template-columns: 120px auto 1fr 1fr; align-items: center; gap: 12px; padding: 8px 0; }
        @media (max-width: 640px) { .cov-day-row { grid-template-columns: 1fr; } }
      `}</style>

      <div className="cov-grid">
        <div style={{ minWidth: 0 }}>
          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Service coverage</h3>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>Choose the areas where your team can provide Home Services.</p>

            <div style={{ display: "flex", gap: 4, marginBottom: 16, background: "var(--surface-sunken)", borderRadius: "var(--radius-lg)", padding: 4, width: "fit-content" }}>
              {(["pincode", "radius"] as const).map(mode => (
                <button key={mode} onClick={() => setCoverageMode(mode)} style={{
                  padding: "7px 16px", borderRadius: "var(--radius-md)", border: "none", fontSize: 13, fontWeight: 600,
                  cursor: "pointer", fontFamily: "inherit",
                  background: coverageMode === mode ? "var(--brand)" : "transparent",
                  color: coverageMode === mode ? "var(--text-on-brand)" : "var(--text-secondary)",
                }}>
                  {mode === "pincode" ? "Pincodes" : "Radius"}
                </button>
              ))}
            </div>

            {coverageMode === "pincode" ? (
              <>
                <div style={{ display: "flex", gap: 10, marginBottom: pincodeNeedsManualLocation ? 10 : 16 }}>
                  <div style={{ flex: 1 }}>
                    <Input placeholder="Enter pincode" value={newPincode} onChange={v => {
                      setNewPincode(v);
                      setPincodeNeedsManualLocation(false);
                      setManualPincodeCity("");
                      setManualPincodeState("");
                    }} icon={<MapPin size={14}/>}/>
                  </div>
                  <Btn variant="primary" icon={<Plus size={14}/>} loading={addingPincode} onClick={handleAddPincode}>Add</Btn>
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
                        display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px",
                        borderBottom: i < activePincodes.length - 1 ? "1px solid var(--border)" : "none",
                      }}>
                        <span>
                          <span style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600 }}>{a.zipcode}</span>
                          {a.city && <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginLeft: 8 }}>{a.city}{a.state ? `, ${a.state}` : ""}</span>}
                        </span>
                        <Badge variant="success">Active</Badge>
                        <button onClick={() => handleRemovePincode(a.id)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", display: "flex" }}>
                          <Trash2 size={15}/>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
                  Set an operating location and a maximum service radius. Distance is calculated in kilometers.
                </p>
                <div className="cov-row3" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
                  <Input placeholder="Latitude" type="number" value={radiusLat} onChange={setRadiusLat}/>
                  <Input placeholder="Longitude" type="number" value={radiusLng} onChange={setRadiusLng}/>
                  <Input placeholder="Radius (km)" type="number" value={radiusKm} onChange={setRadiusKm}/>
                </div>
                <div className="cov-row3" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
                  <Input placeholder="City" value={radiusCity} onChange={setRadiusCity}/>
                  <Input placeholder="State" value={radiusState} onChange={setRadiusState}/>
                </div>
                <Btn variant="primary" icon={<Plus size={14}/>} loading={addingRadius} onClick={handleAddRadius} style={{ marginBottom: 16 }}>
                  Add radius zone
                </Btn>
                {activeRadiusAreas.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No radius zones added yet.</p>
                ) : (
                  <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
                    {activeRadiusAreas.map((a, i) => (
                      <div key={a.id} style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px",
                        borderBottom: i < activeRadiusAreas.length - 1 ? "1px solid var(--border)" : "none",
                      }}>
                        <span style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600 }}>
                          {a.radius_km} km from ({a.latitude}, {a.longitude})
                        </span>
                        <Badge variant="success">Active</Badge>
                        <button onClick={() => handleRemovePincode(a.id)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", display: "flex" }}>
                          <Trash2 size={15}/>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
              <Info size={13} style={{ color: "var(--text-tertiary)" }}/>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Coverage controls eligibility, not pricing.</p>
            </div>
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4, flexWrap: "wrap", gap: 8 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Weekly business hours</h3>
              <Btn variant="secondary" size="sm" onClick={handleCopyMondayToWeekdays}>Copy Monday to weekdays</Btn>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 12px" }}>Timezone: {bookingWindow.timezone}</p>
            {DAYS.map(d => {
              const rule = rulesByDay.get(d.idx);
              const enabled = !!rule;
              return (
                <div key={d.idx} className="cov-day-row">
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{d.name}</span>
                  <label style={{ position: "relative", display: "inline-block", width: 40, height: 22 }}>
                    <input type="checkbox" checked={enabled} onChange={e => handleToggleDay(d.idx, e.target.checked)} style={{ opacity: 0, width: 0, height: 0 }}/>
                    <span onClick={() => handleToggleDay(d.idx, !enabled)} style={{
                      position: "absolute", inset: 0, borderRadius: 999, cursor: "pointer",
                      background: enabled ? "var(--brand)" : "var(--border)",
                    }}>
                      <span style={{ position: "absolute", top: 2, left: enabled ? 20 : 2, width: 18, height: 18, borderRadius: "50%", background: "#fff", transition: "left 0.15s" }}/>
                    </span>
                  </label>
                  {enabled ? (
                    <>
                      <input type="time" value={rule!.start_time} onChange={e => handleTimeChange(d.idx, "start_time", e.target.value)}
                        style={{ height: 34, padding: "0 8px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)" }}/>
                      <input type="time" value={rule!.end_time} onChange={e => handleTimeChange(d.idx, "end_time", e.target.value)}
                        style={{ height: 34, padding: "0 8px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)" }}/>
                    </>
                  ) : <span style={{ fontSize: 13, color: "var(--text-tertiary)", gridColumn: "span 2" }}>Closed</span>}
                </div>
              );
            })}
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>Booking controls</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
              <Input label="Minimum notice (minutes)" type="number" value={String(bookingWindow.minimum_notice_minutes)}
                onChange={v => handleBookingWindowChange("minimum_notice_minutes", Number(v))}/>
              <Input label="Advance booking (days)" type="number" value={String(bookingWindow.maximum_advance_booking_days)}
                onChange={v => handleBookingWindowChange("maximum_advance_booking_days", Number(v))}/>
              <Input label="Travel buffer (minutes)" type="number" value={String(bookingWindow.buffer_minutes_between_jobs)}
                onChange={v => handleBookingWindowChange("buffer_minutes_between_jobs", Number(v))}/>
            </div>
            <div style={{ display: "flex", gap: 20, marginTop: 16, flexWrap: "wrap" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                <input type="checkbox" checked={bookingWindow.allow_same_day_booking}
                  onChange={e => handleBookingWindowChange("allow_same_day_booking", e.target.checked)}/>
                Same-day booking enabled
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                <input type="checkbox" checked={bookingWindow.emergency_booking_allowed}
                  onChange={e => handleBookingWindowChange("emergency_booking_allowed", e.target.checked)}/>
                Emergency booking enabled
              </label>
              {savingWindow && <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Saving…</span>}
            </div>
          </Card>

          <Card>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Schedule exceptions</h3>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>Add holidays or one-time closures.</p>
            <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <input type="date" value={newExceptionDate} onChange={e => setNewExceptionDate(e.target.value)}
                style={{ height: 38, padding: "0 10px", fontSize: 13, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)" }}/>
              <div style={{ flex: 1, minWidth: 160 }}>
                <Input placeholder="Reason (e.g. Independence Day)" value={newExceptionReason} onChange={setNewExceptionReason}/>
              </div>
              <Btn variant="secondary" icon={<Plus size={14}/>} onClick={handleAddException}>Add exception</Btn>
            </div>
            {(exceptions ?? []).length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No upcoming exceptions.</p>
            ) : (exceptions ?? []).map(ex => (
              <div key={ex.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{ex.date} · {ex.full_day_closed ? "Closed" : "Custom hours"} · {ex.reason}</span>
                <button onClick={() => handleRemoveException(ex.id)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", display: "flex" }}>
                  <Trash2 size={15}/>
                </button>
              </div>
            ))}
          </Card>
        </div>

        <div style={{ minWidth: 0 }}>
          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>Setup readiness</h3>
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
                  Active {activePincodes.length > 0 && activeRadiusAreas.length > 0 ? "areas" : activeRadiusAreas.length > 0 ? "radius zones" : "pincodes"}
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

      <div style={{
        position: "sticky", bottom: 0, marginTop: 24, padding: "16px 20px",
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
        display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap",
      }}>
        <Btn variant="secondary" onClick={handleBack}>Back</Btn>
        <Btn variant="secondary" loading={saving} onClick={handleSaveDraft}>Save draft</Btn>
        <Btn variant="primary" loading={saving} onClick={handleSaveAndContinue}>Save &amp; continue</Btn>
      </div>
    </OnboardingShell>
  );
}
