"use client";
import React, { useState, useCallback, useEffect } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import {
  tenantPricingApi, masterCatalogApi, tenantSetupApi,
} from "../../../../lib/api";
import { ServiceOSError } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  Tag, RefreshCw, ChevronRight, AlertTriangle, CheckCircle2,
  XCircle, Copy, Info, Activity, Search, X, Eye,
  AlertCircle, Shield, DollarSign, FileText,
} from "lucide-react";

// ── Baseline pricing (from Phase 3 platform seed data) ───────────────────────
const BASELINE = {
  service_name:  "AC Repair",
  job_type:      "repair",
  service_type:  "Split AC",
  brand:         "LG",
  issue_type:    "Not Cooling",
  zipcode:       "141001",
  city:          "Ludhiana",
  state:         "Punjab",
  tier:          "Mid",
  base_price:    800,
  min_price:     600,
  max_price:     1200,
  bargain_floor: 650,
  completed_job_deduction_credits: 21,
  payment_mode:  "customer_pays_provider_directly",
};

// ── Safe helpers ──────────────────────────────────────────────────────────────
const safeText  = (v: unknown, fb = "—"): string =>
  (typeof v === "string" && v.trim()) ? v.trim() : fb;
const safeNum   = (v: unknown): number =>
  (typeof v === "number" && isFinite(v)) ? v : 0;
const safeCur   = (v: unknown, fb = "—"): string => {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return isFinite(n) ? `₹${n.toLocaleString("en-IN")}` : fb;
};
const safeDate  = (v: unknown): string => {
  if (!v) return "—";
  try { return new Date(String(v)).toLocaleDateString("en-IN", { dateStyle: "medium" }); } catch { return "—"; }
};

function copyText(t: string) {
  if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {});
}

const STATUS_MAP: Record<string, { label: string; variant: "success"|"warning"|"danger"|"neutral" }> = {
  pending:       { label: "Pending Approval", variant: "warning" },
  approved:      { label: "Approved",          variant: "success" },
  rejected:      { label: "Rejected",          variant: "danger"  },
  cancelled:     { label: "Cancelled",         variant: "neutral" },
  expired:       { label: "Expired",           variant: "neutral" },
};

// ── Sub-components ────────────────────────────────────────────────────────────
function SectionError({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry: () => void;
}) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 12 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--danger-text)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}>
            <XCircle size={14}/> {title}
          </p>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.85 }}>{error}</p>
          {requestId && (
            <button onClick={() => copyText(requestId)}
              style={{ fontSize: 11, color: "var(--danger-text)", background: "none", border: "none",
                cursor: "pointer", padding: "4px 0 0", display: "flex", alignItems: "center",
                gap: 4, fontFamily: "inherit", opacity: 0.75 }}>
              <Copy size={10}/> Request ID: {requestId}
            </button>
          )}
        </div>
        <button onClick={onRetry}
          style={{ padding: "6px 12px", fontSize: 12, borderRadius: 8,
            border: "1px solid var(--danger-border)", background: "transparent",
            color: "var(--danger-text)", cursor: "pointer", fontFamily: "inherit",
            display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
          <RefreshCw size={11}/> Retry
        </button>
      </div>
    </div>
  );
}

function StatusBadge({ raw }: { raw: string | null | undefined }) {
  const s = STATUS_MAP[String(raw ?? "")] ?? { label: safeText(raw, "Unknown"), variant: "neutral" as const };
  const colors: Record<string, { bg: string; text: string; border: string }> = {
    success: { bg: "var(--success-bg)", text: "var(--success-text)", border: "var(--success-border)" },
    warning: { bg: "var(--warning-bg)", text: "var(--warning-text)", border: "var(--warning-border)" },
    danger:  { bg: "var(--danger-bg)",  text: "var(--danger-text)",  border: "var(--danger-border)"  },
    neutral: { bg: "var(--surface-sunken)", text: "var(--text-secondary)", border: "var(--border)"   },
  };
  const c = colors[s.variant];
  return (
    <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 9px", borderRadius: 999,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`, whiteSpace: "nowrap" }}>
      {s.label}
    </span>
  );
}

function KpiCard({ label, value, sub, icon, variant }: {
  label: string; value: string | number; sub?: string;
  icon: React.ReactNode; variant?: "success"|"warning"|"danger"|"neutral";
}) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "18px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
          color: "var(--text-tertiary)" }}>{label}</span>
        <span style={{ color: "var(--text-tertiary)", opacity: 0.6 }}>{icon}</span>
      </div>
      <p style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px", lineHeight: 1 }}>{value}</p>
      {sub && <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>{sub}</p>}
      {variant && variant !== "neutral" && (
        <div style={{ marginTop: 8, fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
          alignSelf: "flex-start", display: "inline-block",
          background: variant === "success" ? "var(--success-bg)" : variant === "warning" ? "var(--warning-bg)" : "var(--danger-bg)",
          color: variant === "success" ? "var(--success-text)" : variant === "warning" ? "var(--warning-text)" : "var(--danger-text)",
          border: `1px solid ${variant === "success" ? "var(--success-border)" : variant === "warning" ? "var(--warning-border)" : "var(--danger-border)"}` }}>
          {variant === "success" ? "OK" : variant === "warning" ? "Notice" : "Action Needed"}
        </div>
      )}
    </div>
  );
}

// ── Price Preview Panel ───────────────────────────────────────────────────────
interface PreviewResult {
  base_price?: number;
  min_price?: number;
  max_price?: number;
  bargain_floor?: number;
  completed_job_deduction_credits?: number;
  payment_collection_mode?: string;
  final_customer_estimate?: number;
  service_name?: string;
  job_type?: string;
  tier?: string | Record<string, unknown>;
  source?: string;
  matched_rule_name?: string;
  error?: string;
  requestId?: string;
}

function PricePreviewPanel({ enabledServices }: { enabledServices: Record<string, unknown>[] }) {
  const [serviceTypeId, setServiceTypeId] = useState("");
  const [serviceCategory, setServiceCategory] = useState("home_services");
  const [cityName, setCityName] = useState("Ludhiana");
  const [pincode, setPincode] = useState("141001");
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px", fontSize: 13, boxSizing: "border-box",
    border: "1px solid var(--border)", borderRadius: 8,
    background: "var(--surface)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit",
  };

  async function preview() {
    if (!serviceTypeId.trim()) return;
    setLoading(true); setResult(null);
    try {
      const data = await tenantPricingApi.previewPrice({
        service_type_id: serviceTypeId.trim(),
        service_category: serviceCategory,
        city_name: cityName,
        pincode: pincode || undefined,
      });
      setResult(data as PreviewResult);
    } catch (e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setResult({ error: e instanceof Error ? e.message : "Preview failed.", requestId: rid ?? undefined });
    } finally { setLoading(false); }
  }

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 24px" }}>
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px",
        display: "flex", alignItems: "center", gap: 8 }}>
        <Search size={15}/> Price Preview
      </p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 18px" }}>
        Resolve the customer price estimate for a service using the platform pricing engine.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr auto", gap: 10, alignItems: "flex-end", marginBottom: 14 }}>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            Service Type ID
          </label>
          <input value={serviceTypeId} onChange={e => setServiceTypeId(e.target.value)}
            placeholder="UUID or slug" style={{ ...inputStyle, fontFamily: "monospace", fontSize: 12 }}/>
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            Category
          </label>
          <input value={serviceCategory} onChange={e => setServiceCategory(e.target.value)}
            placeholder="home_services" style={inputStyle}/>
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            City
          </label>
          <input value={cityName} onChange={e => setCityName(e.target.value)}
            placeholder="Ludhiana" style={inputStyle}/>
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            Zipcode
          </label>
          <input value={pincode} onChange={e => setPincode(e.target.value)}
            placeholder="141001" style={{ ...inputStyle, fontFamily: "monospace" }}/>
        </div>
        <button onClick={preview} disabled={!serviceTypeId.trim() || loading}
          style={{ padding: "9px 18px", fontSize: 13, fontWeight: 600, borderRadius: 9,
            border: "none", background: "var(--brand)", color: "white",
            cursor: serviceTypeId.trim() ? "pointer" : "not-allowed", fontFamily: "inherit",
            display: "flex", alignItems: "center", gap: 6,
            opacity: serviceTypeId.trim() ? 1 : 0.5 }}>
          {loading ? <><RefreshCw size={12} style={{ animation: "spin 1s linear infinite" }}/> …</>
                   : <><Eye size={12}/> Preview</>}
        </button>
      </div>

      {enabledServices.length > 0 && (
        <div style={{ marginBottom: 14, padding: "10px 14px", borderRadius: 9,
          background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 6px" }}>
            Your enabled services (click to copy master_service_id):
          </p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {enabledServices.slice(0, 8).map((s, i) => {
              const id = String(s.master_service_id ?? s.service_id ?? "");
              const name = String(s.tenant_display_name ?? s.service_name ?? s.name ?? id.slice(0,8));
              return (
                <button key={i} onClick={() => { setServiceTypeId(id); }}
                  style={{ fontSize: 11, padding: "3px 10px", borderRadius: 6, cursor: "pointer",
                    border: "1px solid var(--border)", background: "var(--surface)",
                    color: "var(--text-primary)", fontFamily: "inherit" }}>
                  {name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {result && (
        result.error ? (
          <div style={{ padding: "12px 16px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
            borderRadius: 10, fontSize: 12, color: "var(--danger-text)" }}>
            <div style={{ display: "flex", gap: 7, marginBottom: result.requestId ? 6 : 0 }}>
              <XCircle size={13} style={{ flexShrink: 0, marginTop: 1 }}/> {result.error}
            </div>
            {result.requestId && (
              <button onClick={() => copyText(result.requestId!)}
                style={{ fontSize: 11, background: "none", border: "none", cursor: "pointer",
                  color: "var(--danger-text)", fontFamily: "inherit", display: "flex",
                  alignItems: "center", gap: 4, padding: 0, opacity: 0.75 }}>
                <Copy size={10}/> Request ID: {result.requestId}
              </button>
            )}
          </div>
        ) : (
          <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, padding: "16px 20px" }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", margin: "0 0 12px",
              textTransform: "uppercase", letterSpacing: "0.07em" }}>
              Price Preview Result
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
              {[
                ["Customer Price Estimate", safeCur(result.final_customer_estimate ?? result.base_price)],
                ["Base Price",             safeCur(result.base_price)],
                ["Minimum Price",          safeCur(result.min_price)],
                ["Maximum Price",          safeCur(result.max_price)],
                ["Min Floor Price",         safeCur(result.bargain_floor)],
                ["Completed Job Deduction", result.completed_job_deduction_credits != null
                  ? `${result.completed_job_deduction_credits} usage credits` : "—"],
                ["Payment Mode",           result.payment_collection_mode === "customer_pays_provider_directly"
                  ? "Pay provider directly" : safeText(result.payment_collection_mode)],
                ["Pricing Source",         safeText(result.matched_rule_name ?? result.source)],
              ].map(([k, v]) => (
                <div key={k} style={{ padding: "10px 12px", background: "var(--surface)", borderRadius: 8,
                  border: "1px solid var(--border)" }}>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--text-tertiary)", margin: "0 0 4px",
                    textTransform: "uppercase", letterSpacing: "0.06em" }}>{k}</p>
                  <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{v}</p>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--success-bg)",
              border: "1px solid var(--success-border)", borderRadius: 8,
              fontSize: 12, color: "var(--success-text)", display: "flex", gap: 6 }}>
              <CheckCircle2 size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
              Price resolved successfully. Customer pays provider directly — no platform payment collected.
            </div>
          </div>
        )
      )}
    </div>
  );
}

// ── Override Request Wizard ───────────────────────────────────────────────────
interface OverrideForm {
  service_id: string;
  service_name: string;
  base_price: number;
  min_price: number;
  max_price: number;
  requested_price: string;
  reason: string;
  notes: string;
}

function OverrideWizard({ onClose, onSubmitted }: { onClose: () => void; onSubmitted: () => void }) {
  const [form, setForm] = useState<OverrideForm>({
    service_id: "", service_name: "", base_price: 800, min_price: 600, max_price: 1200,
    requested_price: "", reason: "", notes: "",
  });
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const [validationOk, setValidationOk] = useState<boolean | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [saveErrId, setSaveErrId] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const f = (k: keyof OverrideForm, v: string) => setForm(prev => ({ ...prev, [k]: v }));

  function validate() {
    const price = parseFloat(form.requested_price);
    if (isNaN(price)) { setValidationMsg("Enter a valid numeric price."); setValidationOk(false); return false; }
    if (price < form.min_price) {
      setValidationMsg(`₹${price} is below the platform minimum of ₹${form.min_price}. Override rejected.`);
      setValidationOk(false); return false;
    }
    if (price > form.max_price) {
      setValidationMsg(`₹${price} exceeds the platform maximum of ₹${form.max_price}. This will be submitted for admin review.`);
      setValidationOk(true); return true;
    }
    setValidationMsg(`₹${price} is within the valid range (₹${form.min_price}–₹${form.max_price}). Will be submitted for admin approval.`);
    setValidationOk(true); return true;
  }

  const submitAction = useAction(async () => {
    if (!validate()) return;
    if (!form.reason.trim()) { setSaveErr("Please provide a reason for the override request."); return; }
    setSaveErr(null); setSaveErrId(null);
    try {
      await tenantSetupApi.submitOverride({
        service_id: form.service_id || "ac_repair_baseline",
        service_name: form.service_name || "AC Repair",
        requested_price: parseFloat(form.requested_price),
        platform_base: form.base_price,
        platform_min: form.min_price,
        platform_max: form.max_price,
        reason: form.reason,
        notes: form.notes || undefined,
      });
      setSubmitted(true);
      onSubmitted();
    } catch (e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setSaveErr(e instanceof Error ? e.message : "Submission failed.");
      setSaveErrId(rid);
    }
  });

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px", fontSize: 13, boxSizing: "border-box",
    border: "1px solid var(--border)", borderRadius: 8,
    background: "var(--surface)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit",
  };

  if (submitted) {
    return (
      <div style={{ padding: "24px", textAlign: "center" }}>
        <CheckCircle2 size={36} style={{ color: "var(--success-text)", marginBottom: 12 }}/>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Override Request Submitted
        </h3>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
          Your pricing override request has been submitted for admin approval.
        </p>
        <div style={{ padding: "12px 16px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
          borderRadius: 10, fontSize: 12, color: "var(--warning-text)", marginBottom: 16, textAlign: "left",
          display: "flex", gap: 7 }}>
          <Shield size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
          Status: Pending Approval — you cannot self-approve this request.
        </div>
        <button onClick={onClose}
          style={{ padding: "9px 20px", fontSize: 13, fontWeight: 600, borderRadius: 9,
            border: "none", background: "var(--brand)", color: "white",
            cursor: "pointer", fontFamily: "inherit" }}>
          Close
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* Business rule banner */}
      <div style={{ padding: "10px 14px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
        borderRadius: 9, fontSize: 12, color: "var(--warning-text)", display: "flex", gap: 7 }}>
        <Shield size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
        You cannot self-approve this request. Submitted overrides require admin approval.
      </div>

      {/* Service context */}
      <div>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Service</label>
        <input value={form.service_name} onChange={e => f("service_name", e.target.value)}
          placeholder="AC Repair" style={inputStyle}/>
      </div>

      {/* Platform pricing display */}
      <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px" }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
          letterSpacing: "0.07em", margin: "0 0 10px" }}>Platform Pricing (Read-Only)</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          {[["Platform Base", safeCur(form.base_price)], ["Minimum", safeCur(form.min_price)], ["Maximum", safeCur(form.max_price)]].map(([k, v]) => (
            <div key={k} style={{ textAlign: "center", padding: "8px", background: "var(--surface)", borderRadius: 7, border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 3px" }}>{k}</p>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{v}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Override price */}
      <div>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Requested Override Price (₹)
        </label>
        <input type="number" value={form.requested_price} onChange={e => { f("requested_price", e.target.value); setValidationMsg(null); setValidationOk(null); }}
          placeholder="e.g. 900" style={{ ...inputStyle, fontFamily: "monospace" }}/>
        <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
          {[500, 900, 1300].map(p => (
            <button key={p} onClick={() => { f("requested_price", String(p)); setValidationMsg(null); setValidationOk(null); }}
              style={{ fontSize: 11, padding: "3px 10px", borderRadius: 6, cursor: "pointer",
                border: "1px solid var(--border)", background: "var(--surface-sunken)",
                color: "var(--text-secondary)", fontFamily: "inherit" }}>
              ₹{p}
            </button>
          ))}
          <span style={{ fontSize: 10, color: "var(--text-tertiary)", alignSelf: "center" }}>— quick test values</span>
        </div>
      </div>

      {/* Validate button */}
      <button onClick={() => validate()}
        style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 8,
          border: "1px solid var(--border)", background: "var(--surface-sunken)",
          color: "var(--text-primary)", cursor: "pointer", fontFamily: "inherit",
          display: "flex", alignItems: "center", gap: 5, alignSelf: "flex-start" }}>
        <CheckCircle2 size={12}/> Validate Price
      </button>

      {validationMsg && (
        <div style={{ padding: "10px 14px", borderRadius: 9,
          background: validationOk ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${validationOk ? "var(--success-border)" : "var(--danger-border)"}`,
          fontSize: 12, color: validationOk ? "var(--success-text)" : "var(--danger-text)",
          display: "flex", gap: 7 }}>
          {validationOk ? <CheckCircle2 size={13} style={{ flexShrink: 0, marginTop: 1 }}/> : <XCircle size={13} style={{ flexShrink: 0, marginTop: 1 }}/>}
          {validationMsg}
        </div>
      )}

      {/* Reason */}
      <div>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Reason <span style={{ color: "var(--danger-text)" }}>*</span>
        </label>
        <textarea value={form.reason} onChange={e => f("reason", e.target.value)}
          placeholder="e.g. Local market rate for AC repair in Ludhiana is ₹900 for Split AC."
          rows={3}
          style={{ ...inputStyle, resize: "vertical", lineHeight: 1.5 }}/>
      </div>

      {/* Notes */}
      <div>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Additional Notes (optional)
        </label>
        <textarea value={form.notes} onChange={e => f("notes", e.target.value)}
          placeholder="Any additional context for the admin reviewer…" rows={2}
          style={{ ...inputStyle, resize: "vertical", lineHeight: 1.5 }}/>
      </div>

      {saveErr && (
        <div style={{ padding: "10px 14px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          borderRadius: 9, fontSize: 12, color: "var(--danger-text)" }}>
          <p style={{ margin: "0 0 4px", fontWeight: 600 }}>{saveErr}</p>
          {saveErrId && (
            <button onClick={() => copyText(saveErrId)}
              style={{ fontSize: 11, background: "none", border: "none", cursor: "pointer",
                color: "var(--danger-text)", fontFamily: "inherit", display: "flex",
                alignItems: "center", gap: 4, padding: 0, opacity: 0.75 }}>
              <Copy size={10}/> Request ID: {saveErrId}
            </button>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
        <button onClick={onClose}
          style={{ padding: "9px 18px", fontSize: 13, borderRadius: 9, border: "1px solid var(--border)",
            background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer", fontFamily: "inherit" }}>
          Cancel
        </button>
        <button onClick={submitAction.execute} disabled={submitAction.loading || validationOk === false}
          style={{ padding: "9px 20px", fontSize: 13, fontWeight: 600, borderRadius: 9,
            border: "none", background: "var(--brand)", color: "white", fontFamily: "inherit",
            cursor: submitAction.loading || validationOk === false ? "not-allowed" : "pointer",
            opacity: submitAction.loading || validationOk === false ? 0.6 : 1,
            display: "flex", alignItems: "center", gap: 6 }}>
          {submitAction.loading
            ? <><RefreshCw size={12} style={{ animation: "spin 1s linear infinite" }}/> Submitting…</>
            : "Submit for Approval"}
        </button>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function PricingPage() {
  const pricesApi   = useApi(useCallback(() => tenantPricingApi.listPrices(50), []), []);
  const servicesApi = useApi(useCallback(() => masterCatalogApi.listEnabled(), []), []);
  const activityApi = useApi(useCallback(() => tenantSetupApi.getActivity(1), []), []);

  const [overrideOpen, setOverrideOpen] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success"|"error" } | null>(null);

  function notify(msg: string, type: "success"|"error" = "success") {
    setToast({ msg, type }); setTimeout(() => setToast(null), 3800);
  }

  // Prices list — the /v1/pricing/tenants/{tid}/prices endpoint
  const priceRows: Record<string, unknown>[] = (() => {
    const d = pricesApi.data as Record<string, unknown> | null;
    if (!d) return [];
    if (Array.isArray(d)) return d;
    const list = d.prices ?? d.items ?? d.data ?? [];
    return Array.isArray(list) ? list : [];
  })();

  // Enabled services for preview shortcuts
  const enabledServices: Record<string, unknown>[] =
    ((servicesApi.data as unknown) as { services?: Record<string, unknown>[] } | null)?.services ?? [];

  const activities = (()=>{
    const d = activityApi.data as Record<string,unknown>|null;
    if (!d) return [];
    const list = d.events ?? d.activities ?? d.items ?? [];
    return Array.isArray(list) ? (list as unknown[]).slice(0, 6) : [];
  })();

  // Override history (stored locally for this session as the backend endpoint returns 404)
  const [overrideHistory, setOverrideHistory] = useState<Array<{
    id: string; service: string; requested_price: number;
    reason: string; status: string; submitted_at: string;
  }>>([]);

  // Endpoint status
  const pricingEndpointAvailable = !pricesApi.error || pricesApi.error.includes("404") === false;

  return (
    <TenantLayout activeNav="provider-pricing">
      <div style={{ marginBottom: 16, padding: "10px 16px", borderRadius: 10,
        background: "var(--warning-bg, #fffbeb)", border: "1px solid var(--warning-border, #fde68a)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <p style={{ fontSize: 13, color: "var(--warning-text, #92400e)", margin: 0 }}>
          This page has moved. Open the new Home Services setup flow.
        </p>
        <a href="/tenant/setup/services" style={{
          fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Go to Service Setup →
        </a>
      </div>
      <style>{`
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}
        .pg-grid{display:grid;gap:20px}
        .kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}
        @media(max-width:768px){.kpi-grid{grid-template-columns:1fr 1fr}}
      `}</style>

      {/* Toast */}
      {toast && (
        <div style={{ position: "fixed", top: 72, right: 24, zIndex: 9999, maxWidth: 380,
          padding: "12px 18px", borderRadius: 10, boxShadow: "0 4px 24px rgba(0,0,0,0.15)",
          animation: "fadeIn 0.2s ease",
          background: toast.type === "success" ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.type === "success" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.type === "success" ? "var(--success-text)" : "var(--danger-text)",
          fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 8 }}>
          {toast.type === "success" ? <CheckCircle2 size={14}/> : <XCircle size={14}/>}
          {toast.msg}
        </div>
      )}

      {/* 1. BREADCRUMB */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Tenant Portal</span><ChevronRight size={12}/>
        <span>Setup</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Pricing Setup</span>
      </div>

      {/* 2. PAGE HEADER */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px", letterSpacing: "-0.01em" }}>
            Pricing Setup
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            View platform pricing, preview customer estimates, and request approved price overrides for your services.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={() => { pricesApi.refetch(); servicesApi.refetch(); activityApi.refetch(); }}
            style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9,
              border: "1px solid var(--border)", background: "var(--surface-sunken)",
              color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
              display: "flex", alignItems: "center", gap: 5 }}>
            <RefreshCw size={12}/> Refresh
          </button>
          <button onClick={() => setOverrideOpen(true)}
            style={{ padding: "8px 16px", fontSize: 13, fontWeight: 600, borderRadius: 9,
              border: "none", background: "var(--brand)", color: "white",
              cursor: "pointer", fontFamily: "inherit",
              display: "flex", alignItems: "center", gap: 6 }}>
            <Tag size={13}/> Request Override
          </button>
        </div>
      </div>

      <div className="pg-grid">

        {/* 3. PRICING READINESS HERO */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12,
          padding: "22px 24px",
          borderLeft: `4px solid ${pricesApi.error ? "var(--danger-text)" : "var(--success-text)"}` }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
                color: "var(--text-tertiary)", margin: "0 0 6px" }}>Pricing Status</p>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <h2 style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                  {pricesApi.error ? "Pricing Data Unavailable" : priceRows.length > 0 ? "Pricing Ready" : "Platform Pricing Active"}
                </h2>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999,
                  background: pricesApi.error ? "var(--danger-bg)" : "var(--success-bg)",
                  color: pricesApi.error ? "var(--danger-text)" : "var(--success-text)",
                  border: `1px solid ${pricesApi.error ? "var(--danger-border)" : "var(--success-border)"}` }}>
                  {pricesApi.error ? "Error" : "OK"}
                </span>
              </div>
              <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                <MetaChip icon={<DollarSign size={11}/>} label="Base Price (AC Repair)" value={safeCur(BASELINE.base_price)}/>
                <MetaChip icon={<Shield size={11}/>} label="Min Floor Price" value={safeCur(BASELINE.bargain_floor)}/>
                <MetaChip icon={<Tag size={11}/>} label="Deduction" value={`${BASELINE.completed_job_deduction_credits} credits`}/>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1 }}>
                {enabledServices.length}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>enabled services</div>
            </div>
          </div>

          {pricesApi.error && (
            <div style={{ marginTop: 14, padding: "10px 14px", borderRadius: 9,
              background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
              fontSize: 12, color: "var(--danger-text)", display: "flex", gap: 8 }}>
              <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
              <div>
                <strong>Pricing endpoint unavailable</strong> — {pricesApi.error}
                {pricesApi.requestId && (
                  <div style={{ marginTop: 4 }}>
                    <button onClick={() => copyText(pricesApi.requestId!)}
                      style={{ fontSize: 11, background: "none", border: "none", cursor: "pointer",
                        color: "var(--danger-text)", fontFamily: "inherit", display: "inline-flex",
                        alignItems: "center", gap: 4, padding: 0, opacity: 0.75 }}>
                      <Copy size={10}/> {pricesApi.requestId}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {!pricesApi.error && (
            <div style={{ marginTop: 14, padding: "10px 14px", borderRadius: 9,
              background: "var(--success-bg)", border: "1px solid var(--success-border)",
              fontSize: 12, color: "var(--success-text)", display: "flex", gap: 7 }}>
              <CheckCircle2 size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
              Platform pricing is active. Customers pay the provider directly — no payment collected by the platform.
            </div>
          )}
        </div>

        {/* 4. KPI CARDS */}
        <div className="kpi-grid">
          <KpiCard label="Base Price (AC Repair)" value={safeCur(BASELINE.base_price)}
            sub="Platform base — AC Repair / Split AC / LG"
            icon={<DollarSign size={16}/>} variant="neutral"/>
          <KpiCard label="Price Range" value={`${safeCur(BASELINE.min_price)} – ${safeCur(BASELINE.max_price)}`}
            sub="Platform min / max boundary"
            icon={<Tag size={16}/>} variant="neutral"/>
          <KpiCard label="Min Floor Price" value={safeCur(BASELINE.bargain_floor)}
            sub="Customer offers below this are rejected"
            icon={<Shield size={16}/>} variant="neutral"/>
          <KpiCard label="Completed Job Deduction" value={`${BASELINE.completed_job_deduction_credits} credits`}
            sub="Deducted after job completion — not a customer fee"
            icon={<AlertTriangle size={16}/>} variant="neutral"/>
          <KpiCard label="Payment Mode" value="Pay Directly"
            sub="Customer pays provider on-site"
            icon={<CheckCircle2 size={16}/>} variant="success"/>
          <KpiCard label="Enabled Services" value={enabledServices.length}
            sub="Services with platform pricing available"
            icon={<FileText size={16}/>} variant={enabledServices.length > 0 ? "success" : "warning"}/>
        </div>

        {/* 5. PRICING RULES EXPLANATION */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 24px" }}>
          <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px",
            display: "flex", alignItems: "center", gap: 8 }}>
            <Info size={15}/> How Tenant Pricing Works
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
            {[
              ["Platform price is source of truth", "Administrators define base, minimum, maximum, and bargain floor. These cannot be bypassed."],
              ["Overrides require admin approval", "You may request a price override, but it must be approved by an administrator. You cannot self-approve."],
              ["Below-min offers are rejected", `Customer offers below ₹${BASELINE.min_price} (platform minimum) are automatically rejected.`],
              ["Floor price protects minimum pricing", `₹${BASELINE.bargain_floor} is the lowest price the platform allows. Offers below this are automatically rejected.`],
              ["Completed job deduction uses credits", `${BASELINE.completed_job_deduction_credits} provider usage credits are deducted after job completion — not charged to the customer.`],
              ["No platform service payment collection", "For Home Services, customers pay the provider directly on-site. The platform does not collect the service fee."],
            ].map(([title, desc]) => (
              <div key={title} style={{ padding: "12px 14px", background: "var(--surface-sunken)",
                border: "1px solid var(--border)", borderRadius: 9 }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>{title}</p>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 6. PLATFORM PRICING TABLE */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px",
                display: "flex", alignItems: "center", gap: 8 }}>
                <Tag size={15}/> Platform Pricing Rules
              </p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                Baseline pricing for your vertical. Read-only — set by platform administrator.
              </p>
            </div>
          </div>

          {pricesApi.error ? (
            <div style={{ padding: 20 }}>
              <SectionError title="Could not load tenant price list" error={pricesApi.error}
                requestId={pricesApi.requestId} onRetry={pricesApi.refetch}/>
              {/* Show baseline even if tenant-specific prices fail */}
              <div style={{ marginTop: 16, padding: "14px 16px", background: "var(--warning-bg)",
                border: "1px solid var(--warning-border)", borderRadius: 10,
                fontSize: 12, color: "var(--warning-text)", display: "flex", gap: 7 }}>
                <Info size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
                Showing baseline platform pricing below. Use Price Preview to resolve pricing for your enabled services.
              </div>
            </div>
          ) : pricesApi.loading ? (
            <div style={{ padding: "16px 20px" }}>
              {[...Array(2)].map((_,i) => (
                <div key={i} style={{ height: 52, background: "var(--surface-sunken)", borderRadius: 8,
                  marginBottom: 10, animation: "pulse 1.5s ease-in-out infinite" }}/>
              ))}
            </div>
          ) : null}

          {/* Always show the baseline row + any fetched rows */}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Service","Job Type","Type / Brand","Base Price","Min / Max","Floor Price","Deduction","Payment Mode","Source","Actions"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 10, fontWeight: 700,
                      color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Baseline row — always shown */}
                <BaselineRow onRequestOverride={() => setOverrideOpen(true)}/>
                {/* Live rows if available */}
                {priceRows.map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "11px 14px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      {safeText(row.service_name ?? row.name)}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {safeText(row.job_type)}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {safeText(row.service_type ?? row.type)}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                      {safeCur(row.base_price)}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {safeCur(row.min_price)} / {safeCur(row.max_price)}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {row.bargain_floor ? safeCur(row.bargain_floor) : "—"}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {row.completed_job_deduction_credits ? `${row.completed_job_deduction_credits} credits` : "—"}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--success-text)" }}>
                      Pay directly
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {safeText(row.source ?? row.pricing_source)}
                    </td>
                    <td style={{ padding: "11px 14px" }}>
                      <button onClick={() => setOverrideOpen(true)}
                        style={{ fontSize: 11, padding: "4px 10px", borderRadius: 7,
                          border: "1px solid var(--border)", background: "var(--surface-sunken)",
                          color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit" }}>
                        Override
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 7. PRICE PREVIEW PANEL */}
        <PricePreviewPanel enabledServices={enabledServices}/>

        {/* 8. OVERRIDE REQUEST HISTORY */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0,
              display: "flex", alignItems: "center", gap: 8 }}>
              <FileText size={15}/> Override Request History
            </p>
            <button onClick={() => setOverrideOpen(true)}
              style={{ fontSize: 12, fontWeight: 600, padding: "6px 14px", borderRadius: 8,
                border: "1px solid var(--border)", background: "var(--surface-sunken)",
                color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit" }}>
              + New Request
            </button>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px" }}>
            Your submitted override requests and their admin approval status.
          </p>

          {overrideHistory.length === 0 ? (
            <div style={{ padding: "28px", textAlign: "center", color: "var(--text-tertiary)" }}>
              <FileText size={28} style={{ opacity: 0.25, marginBottom: 8 }}/>
              <p style={{ fontSize: 13, margin: 0 }}>No override requests submitted yet.</p>
              <p style={{ fontSize: 12, margin: "4px 0 0" }}>
                Use the Request Override button to submit a pricing override for admin approval.
              </p>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                    {["Service","Requested Price","Platform Range","Reason","Status","Submitted At"].map(h => (
                      <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 10,
                        fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
                        letterSpacing: "0.06em", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {overrideHistory.map((req, i) => (
                    <tr key={i} style={{ borderBottom: i < overrideHistory.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding: "11px 14px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                        {req.service}
                      </td>
                      <td style={{ padding: "11px 14px", fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                        {safeCur(req.requested_price)}
                      </td>
                      <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {safeCur(BASELINE.min_price)} – {safeCur(BASELINE.max_price)}
                      </td>
                      <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)",
                        maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {req.reason}
                      </td>
                      <td style={{ padding: "11px 14px" }}>
                        <StatusBadge raw={req.status}/>
                      </td>
                      <td style={{ padding: "11px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                        {safeDate(req.submitted_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Note about self-approval */}
          <div style={{ marginTop: 14, padding: "10px 14px", background: "var(--warning-bg)",
            border: "1px solid var(--warning-border)", borderRadius: 9,
            fontSize: 12, color: "var(--warning-text)", display: "flex", gap: 7 }}>
            <Shield size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
            Tenants cannot approve or reject override requests. Admin approval is required.
          </div>
        </div>

        {/* 9. ACTIVITY TIMELINE */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0,
              display: "flex", alignItems: "center", gap: 8 }}>
              <Activity size={15}/> Recent Pricing Activity
            </p>
            <a href="/activity" style={{ fontSize: 12, color: "var(--brand)", textDecoration: "none",
              display: "flex", alignItems: "center", gap: 3 }}>
              View All <ChevronRight size={12}/>
            </a>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 14px" }}>
            Price previews, override requests, and approval events.
          </p>

          {activityApi.error ? (
            <SectionError title="Could not load activity" error={activityApi.error}
              requestId={activityApi.requestId} onRetry={activityApi.refetch}/>
          ) : activityApi.loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[...Array(3)].map((_,i) => (
                <div key={i} style={{ height: 44, background: "var(--surface-sunken)", borderRadius: 8,
                  animation: "pulse 1.5s ease-in-out infinite" }}/>
              ))}
            </div>
          ) : activities.length === 0 ? (
            <div style={{ padding: "24px", textAlign: "center", color: "var(--text-tertiary)" }}>
              <Activity size={28} style={{ opacity: 0.25, marginBottom: 8 }}/>
              <p style={{ fontSize: 13, margin: 0 }}>No pricing activity yet.</p>
              <p style={{ fontSize: 12, margin: "4px 0 0" }}>Price previews and override requests will appear here.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {activities.map((ev: unknown, i: number) => {
                const e = ev as Record<string, unknown>;
                return (
                  <div key={i} style={{ display: "flex", gap: 12, padding: "11px 0",
                    borderBottom: i < activities.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div style={{ width: 30, height: 30, borderRadius: "50%",
                      background: "var(--surface-sunken)", border: "1px solid var(--border)",
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Activity size={12} style={{ color: "var(--text-tertiary)" }}/>
                    </div>
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: "0 0 2px" }}>
                        {safeText(e.action ?? e.event_type ?? e.type, "Pricing event")}
                      </p>
                      <div style={{ display: "flex", gap: 10, fontSize: 11, color: "var(--text-tertiary)" }}>
                        <span>{safeDate(e.created_at ?? e.timestamp)}</span>
                        {e.request_id && (
                          <button onClick={() => copyText(String(e.request_id))}
                            style={{ background: "none", border: "none", cursor: "pointer",
                              color: "var(--text-tertiary)", fontSize: 11, fontFamily: "inherit",
                              display: "flex", alignItems: "center", gap: 3, padding: 0 }}>
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

      {/* OVERRIDE WIZARD MODAL */}
      {overrideOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 1000,
          display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ background: "var(--surface)", borderRadius: 14, maxWidth: 560, width: "100%",
            maxHeight: "92vh", display: "flex", flexDirection: "column",
            boxShadow: "0 20px 60px rgba(0,0,0,0.2)", border: "1px solid var(--border)" }}>
            <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border)",
              display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
              <div>
                <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                  Request Price Override
                </h2>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
                  Submit for admin approval — you cannot self-approve
                </p>
              </div>
              <button onClick={() => setOverrideOpen(false)}
                style={{ width: 30, height: 30, borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--surface-sunken)", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
                <X size={14}/>
              </button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
              <OverrideWizard
                onClose={() => setOverrideOpen(false)}
                onSubmitted={() => {
                  notify("Override request submitted for admin approval.");
                  setOverrideHistory(prev => [{
                    id: String(Date.now()),
                    service: "AC Repair",
                    requested_price: 900,
                    reason: "Local market rate",
                    status: "pending",
                    submitted_at: new Date().toISOString(),
                  }, ...prev]);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </TenantLayout>
  );
}

// ── Baseline table row (always shown) ─────────────────────────────────────────
function BaselineRow({ onRequestOverride }: { onRequestOverride: () => void }) {
  return (
    <tr style={{ borderBottom: "1px solid var(--border)", background: "rgba(37,99,235,0.02)" }}>
      <td style={{ padding: "11px 14px" }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{BASELINE.service_name}</span>
          <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 1 }}>
            {BASELINE.service_type} · {BASELINE.brand} · {BASELINE.issue_type}
          </div>
        </div>
      </td>
      <td style={{ padding: "11px 14px" }}>
        <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6,
          background: "var(--surface-sunken)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
          {BASELINE.job_type}
        </span>
      </td>
      <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
        {BASELINE.service_type} / {BASELINE.brand}
      </td>
      <td style={{ padding: "11px 14px", fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>
        {safeCur(BASELINE.base_price)}
      </td>
      <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
        {safeCur(BASELINE.min_price)} / {safeCur(BASELINE.max_price)}
      </td>
      <td style={{ padding: "11px 14px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
        {safeCur(BASELINE.bargain_floor)}
      </td>
      <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
        {BASELINE.completed_job_deduction_credits} usage credits
      </td>
      <td style={{ padding: "11px 14px" }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--success-text)" }}>
          Pay provider directly
        </span>
      </td>
      <td style={{ padding: "11px 14px" }}>
        <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 5,
          background: "var(--success-bg)", color: "var(--success-text)", border: "1px solid var(--success-border)" }}>
          platform seed
        </span>
      </td>
      <td style={{ padding: "11px 14px" }}>
        <button onClick={onRequestOverride}
          style={{ fontSize: 11, padding: "4px 10px", borderRadius: 7,
            border: "1px solid var(--brand)", background: "rgba(37,99,235,0.06)",
            color: "var(--brand)", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
          Override
        </button>
      </td>
    </tr>
  );
}

function MetaChip({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--text-tertiary)" }}>
      {icon}
      <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>{label}:</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{value}</span>
    </div>
  );
}
