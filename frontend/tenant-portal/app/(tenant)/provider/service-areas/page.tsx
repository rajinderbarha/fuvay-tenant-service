"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState, useEffect } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import {
  providerServiceAreasApi, tenantSetupApi, providerStatusApi, providerOfferingsApi,
  type ProviderServiceArea, type ProviderServiceAreaPayload, type AreaType,
  type ServiceAreaValidationResult, type AreaServiceMapping, type AreaServiceMappingPayload,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  PageHeader, Card, Button, Modal, Drawer, Input, Skeleton,
  StatusBadge as DsStatusBadge, Alert, EmptyState, pushToast, KpiGrid, SummaryCard,
} from "@serviceos/design-system";
import {
  MapPin, Plus, RefreshCw, ChevronRight, AlertTriangle,
  CheckCircle2, XCircle, Copy, Star, Edit2, Trash2,
  Activity, Info, Shield, Search, Eye,
  AlertCircle, ToggleRight, ListChecks,
} from "lucide-react";

// ── Constants ────────────────────────────────────────────────────────────────
const DEFAULT_AREA_LIMIT = 5;

// coverage_type matches the real backend column — there is no "online"
// coverage type in the serviceability engine.
const AREA_TYPE_LABELS: Record<AreaType, string> = {
  zipcode: "Zipcode", city: "City", zone: "Zone", radius: "Radius",
};

const ZONE_TIER_LABELS: Record<string, string> = {
  tier_1: "Tier 1", tier_2: "Tier 2", tier_3: "Tier 3",
};

const JOB_TYPE_OPTIONS = [
  { value: "repair", label: "Repair" },
  { value: "service", label: "Service" },
  { value: "consultation", label: "Consultation" },
];

const BLANK: ProviderServiceAreaPayload = {
  coverage_type: "zipcode", country: "India", state: "", district: "",
  city: "", zipcode: "", zone_name: "", latitude: null, longitude: null,
  radius_km: null, is_primary: false, is_active: true,
};

// ── Helpers ──────────────────────────────────────────────────────────────────
const safeText = (v: unknown, fb = "Not configured"): string =>
  (typeof v === "string" && v.trim()) ? v.trim() : fb;
const safeDate = (v: unknown): string => {
  if (!v) return "Not configured";
  try { return new Date(String(v)).toLocaleDateString("en-IN", { dateStyle: "medium" }); } catch { return "Not configured"; }
};
const safeZoneTier = (v: unknown): string =>
  (typeof v === "string" && ZONE_TIER_LABELS[v]) ? ZONE_TIER_LABELS[v] : "Not configured";

function areaLabel(a: ProviderServiceArea): string {
  if (a.coverage_type === "zipcode") return [a.city, a.zipcode].filter(Boolean).join(" ") || "Zipcode Area";
  if (a.coverage_type === "city")    return a.city || a.district || "City Area";
  if (a.coverage_type === "zone")    return a.zone_name || "Zone";
  if (a.coverage_type === "radius")  return `${a.radius_km ?? "?"}km radius`;
  return a.coverage_type;
}

function areaDescription(a: ProviderServiceArea): string {
  const parts: string[] = [];
  if (a.city)     parts.push(a.city);
  if (a.district && a.district !== a.city) parts.push(a.district);
  if (a.state)    parts.push(a.state);
  if (a.country && a.country !== "India") parts.push(a.country);
  return parts.join(", ") || "Not configured";
}

function copyText(t: string) {
  if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {});
}

// ── Sub-components ────────────────────────────────────────────────────────────
function SectionError({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry: () => void;
}) {
  return (
    <Alert tone="danger" title={title}>
      <p style={{ margin: "0 0 6px" }}>{error} Retry or contact support with the request ID below.</p>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        {requestId && (
          <Button variant="ghost" size="sm" leftIcon={<Copy size={11}/>} onClick={() => copyText(requestId)}>
            Request ID: {requestId}
          </Button>
        )}
        <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={12}/>} onClick={onRetry}>Retry</Button>
      </div>
    </Alert>
  );
}

// ── Slots-used circular progress ──────────────────────────────────────────────
function CoverageRing({ pct }: { pct: number }) {
  const r = 34, c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, pct));
  const color = clamped >= 100 ? "#ef4444" : clamped >= 70 ? "var(--warning)" : "var(--brand)";
  return (
    <div style={{ position: "relative", width: 88, height: 88, flexShrink: 0 }}>
      <svg width={88} height={88} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={44} cy={44} r={r} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth={8}/>
        <circle cx={44} cy={44} r={r} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (clamped / 100) * c}
          style={{ transition: "stroke-dashoffset 0.5s ease" }}/>
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 17, fontWeight: 800, color: "#fff", lineHeight: 1 }}>{Math.round(clamped)}%</span>
        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.7)", marginTop: 2 }}>Slots used</span>
      </div>
    </div>
  );
}

// ── Validation Preview Panel (real backend call) ──────────────────────────────
function ValidationPreviewPanel({ result, loading, onValidate, canValidate }: {
  result: ServiceAreaValidationResult | null;
  loading: boolean;
  onValidate: () => void;
  canValidate: boolean;
}) {
  return (
    <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", margin: 0 }}>
          Validation Preview
        </p>
        <Button variant="secondary" size="sm" disabled={!canValidate} loading={loading}
          leftIcon={!loading ? <Search size={11}/> : undefined} onClick={onValidate}>
          {loading ? "Checking…" : "Validate"}
        </Button>
      </div>

      {!result && !loading && (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Fill in the location fields and click Validate to see resolved city/district/zone-tier,
          duplicate check, and package limit check before saving.
        </p>
      )}

      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 10 }}>
            {[
              ["Resolved City", result.resolved_city],
              ["Resolved District", result.resolved_district],
              ["Resolved State", result.resolved_state],
              ["Resolved Zone/Tier", safeZoneTier(result.resolved_zone_tier)],
              ["Serviceable Status", result.coverage_valid ? "Valid" : "Invalid"],
              ["Duplicate Check", result.is_duplicate ? "Duplicate found" : "No duplicate"],
              ["Package Limit Check", result.package_limit_ok
                ? `OK (${result.remaining_service_areas} slot${result.remaining_service_areas === 1 ? "" : "s"} left)`
                : "Limit reached"],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 8px",
                background: "var(--surface)", borderRadius: 6, border: "1px solid var(--border)" }}>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{k}</span>
                <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-primary)" }}>{v || "Not configured"}</span>
              </div>
            ))}
          </div>
          <div style={{ padding: "8px 12px", borderRadius:"var(--radius-md)",
            background: result.serviceable ? "var(--success-bg)" : "var(--danger-bg)",
            border: `1px solid ${result.serviceable ? "var(--success-border)" : "var(--danger-border)"}`,
            display: "flex", alignItems: "center", gap: 6 }}>
            {result.serviceable
              ? <CheckCircle2 size={12} style={{ color: "var(--success-text)", flexShrink: 0 }}/>
              : <XCircle size={12} style={{ color: "var(--danger-text)", flexShrink: 0 }}/>}
            <span style={{ fontSize: 11, fontWeight: 600,
              color: result.serviceable ? "var(--success-text)" : "var(--danger-text)" }}>
              {result.bookability_impact}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

// ── Detail Drawer ─────────────────────────────────────────────────────────────
const BLANK_MAPPING: AreaServiceMappingPayload = {
  service_id: "", job_type: "repair", is_available: true,
  base_price: null, min_price: null, max_price: null, sla_minutes: null,
};

function AreaDetailDrawer({ area, onClose, onEdit, onDelete, onToggle, totalActive, maxAreas }: {
  area: ProviderServiceArea; onClose: () => void;
  onEdit: () => void; onDelete: () => void; onToggle: () => void;
  totalActive: number; maxAreas: number;
}) {
  const isLastActive = area.is_active && totalActive === 1;

  // Services & Pricing for this area — this is the real price the booking
  // engine uses to charge customers matched to this provider in this area
  // (TenantServiceAreaService.base_price), set by the provider themselves.
  const mappingsApi = useApi(useCallback(() => providerServiceAreasApi.listServiceMappings(area.id), [area.id]));
  const offeringsApi = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []));
  const offeringOptions = (offeringsApi.data?.offerings ?? []).map(o => ({
    value: o.offering_id, label: o.provider_display_name || o.offering_name,
  }));
  const mappings = mappingsApi.data?.mappings ?? [];

  const [mappingModal, setMappingModal] = useState(false);
  const [editingMapping, setEditingMapping] = useState<AreaServiceMapping | null>(null);
  const [mappingForm, setMappingForm] = useState<AreaServiceMappingPayload>(BLANK_MAPPING);
  const [mappingDelete, setMappingDelete] = useState<AreaServiceMapping | null>(null);

  function openAddMapping() {
    setEditingMapping(null);
    setMappingForm(BLANK_MAPPING);
    setMappingModal(true);
  }
  function openEditMapping(m: AreaServiceMapping) {
    setEditingMapping(m);
    setMappingForm({
      service_id: m.service_id, job_type: m.job_type, is_available: m.is_available,
      base_price: m.base_price, min_price: m.min_price, max_price: m.max_price, sla_minutes: m.sla_minutes,
    });
    setMappingModal(true);
  }

  const saveMappingAction = useAction(useCallback(async () => {
    if (editingMapping) {
      await providerServiceAreasApi.updateServiceMapping(area.id, editingMapping.id, mappingForm);
    } else {
      await providerServiceAreasApi.addServiceMapping(area.id, mappingForm);
    }
    mappingsApi.refetch();
    setMappingModal(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area.id, editingMapping, mappingForm]));

  const deleteMappingAction = useAction(useCallback(async (m: AreaServiceMapping) => {
    await providerServiceAreasApi.deleteServiceMapping(area.id, m.id);
    mappingsApi.refetch();
    setMappingDelete(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area.id]));

  return (
    <>
    <Drawer open onClose={onClose} title={areaLabel(area)}>
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div style={{ flex: 1, overflowY: "auto" }}>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px" }}>
            Area Detail &amp; Serviceability
          </p>

          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <DsStatusBadge status={area.is_active ? "active" : "inactive"}/>
            {area.is_primary && (
              <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 9px", borderRadius: 999,
                background: "rgba(217,119,6,0.12)", color: "var(--warning)", border: "1px solid rgba(217,119,6,0.3)" }}>
                ★ Primary
              </span>
            )}
            <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 9px", borderRadius: 999,
              background: "var(--surface-sunken)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
              {AREA_TYPE_LABELS[area.coverage_type as AreaType] ?? area.coverage_type}
            </span>
          </div>

          <Section title="Area Summary">
            <InfoPair label="Area ID" value={area.id} mono small/>
            <InfoPair label="Type" value={AREA_TYPE_LABELS[area.coverage_type as AreaType] ?? area.coverage_type}/>
            <InfoPair label="Zipcode" value={safeText(area.zipcode)} mono/>
            <InfoPair label="City" value={safeText(area.city)}/>
            <InfoPair label="District" value={safeText(area.district)}/>
            <InfoPair label="State" value={safeText(area.state)}/>
            <InfoPair label="Country" value={safeText(area.country)}/>
            {area.coverage_type === "zone" && <InfoPair label="Zone" value={safeText(area.zone_name)}/>}
            {area.coverage_type === "radius" && (
              <>
                <InfoPair label="Radius" value={area.radius_km != null ? `${area.radius_km} km` : "Not configured"}/>
                <InfoPair label="Lat/Lng" value={area.latitude != null ? `${area.latitude}, ${area.longitude}` : "Not configured"}/>
              </>
            )}
          </Section>

          <Section title="Services & Pricing">
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>
              Set your own price per service for this area. This is the price customers are charged when matched to you here.
            </p>
            {mappingsApi.loading ? (
              <Skeleton height={60}/>
            ) : mappings.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>No services priced for this area yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {mappings.map(m => {
                  const offering = offeringsApi.data?.offerings?.find(o => o.offering_id === m.service_id);
                  return (
                    <div key={m.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                      <div>
                        <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>
                          {offering?.provider_display_name || offering?.offering_name || m.service_id}
                        </p>
                        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                          {JOB_TYPE_OPTIONS.find(j => j.value === m.job_type)?.label ?? m.job_type}
                          {m.base_price != null ? ` · Base ₹${m.base_price}` : ""}
                          {m.min_price != null && m.max_price != null ? ` · ₹${m.min_price}-₹${m.max_price}` : ""}
                          {!m.is_available ? " · Unavailable" : ""}
                        </p>
                      </div>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button onClick={() => openEditMapping(m)} title="Edit"
                          style={{ background: "none", border: "none", cursor: "pointer", padding: 4, color: "var(--text-secondary)" }}>
                          <Edit2 size={13}/>
                        </button>
                        <button onClick={() => setMappingDelete(m)} title="Delete"
                          style={{ background: "none", border: "none", cursor: "pointer", padding: 4, color: "var(--danger)" }}>
                          <Trash2 size={13}/>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <Button variant="secondary" size="sm" leftIcon={<Plus size={12}/>} onClick={openAddMapping} style={{ marginTop: 8 }}>
              Add Service Price
            </Button>
          </Section>

          <Section title="Bookability Impact">
            <div style={{ padding: "10px 12px", borderRadius: 9,
              background: area.is_active ? "var(--success-bg)" : "var(--surface-sunken)",
              border: `1px solid ${area.is_active ? "var(--success-border)" : "var(--border)"}`,
              fontSize: 12, color: area.is_active ? "var(--success-text)" : "var(--text-secondary)",
              display: "flex", gap: 7 }}>
              {area.is_active ? <CheckCircle2 size={13} style={{ flexShrink: 0, marginTop: 1 }}/> : <Info size={13} style={{ flexShrink: 0, marginTop: 1 }}/>}
              {area.is_active
                ? "This area is active and counts toward your bookability requirement."
                : "This area is inactive and does not count toward bookability."}
            </div>
            {isLastActive && (
              <div style={{ padding: "10px 12px", borderRadius: 9, background: "var(--danger-bg)",
                border: "1px solid var(--danger-border)", fontSize: 12, color: "var(--danger-text)",
                display: "flex", gap: 7, marginTop: 8 }}>
                <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
                Disabling or deleting this area will remove your only active service area and affect bookability.
              </div>
            )}
          </Section>

          <Section title="Package Limit Impact">
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              This area uses 1 of your {maxAreas} service area slots.
              Removing it frees a slot for a different location.
            </p>
          </Section>

          <Section title="Recent Activity">
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              Created {safeDate(area.created_at)}. Last updated {safeDate(area.updated_at)}.
            </p>
          </Section>
        </div>

        <div style={{ paddingTop: 16, borderTop: "1px solid var(--border)", flexShrink: 0,
          display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button variant="secondary" size="sm" leftIcon={<Edit2 size={12}/>} onClick={onEdit}>Edit</Button>
          <Button variant="secondary" size="sm" leftIcon={<ToggleRight size={12}/>} onClick={onToggle}>
            {area.is_active ? "Disable" : "Enable"}
          </Button>
          <Button variant="destructive" size="sm" leftIcon={<Trash2 size={12}/>} onClick={onDelete}>Delete</Button>
        </div>
      </div>
    </Drawer>

    {mappingModal && (
      <Modal open onClose={() => setMappingModal(false)} title={editingMapping ? "Edit Service Price" : "Add Service Price"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Service</label>
            <select
              value={mappingForm.service_id}
              disabled={!!editingMapping}
              onChange={e => setMappingForm(f => ({ ...f, service_id: e.target.value }))}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", fontSize: 13 }}
            >
              <option value="">Select a service…</option>
              {offeringOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Job Type</label>
            <select
              value={mappingForm.job_type}
              onChange={e => setMappingForm(f => ({ ...f, job_type: e.target.value }))}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", fontSize: 13 }}
            >
              {JOB_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <Input
            label="Base Price"
            type="number"
            value={mappingForm.base_price ?? ""}
            onChange={e => setMappingForm(f => ({ ...f, base_price: e.target.value === "" ? null : Number(e.target.value) }))}
          />
          <div style={{ display: "flex", gap: 10 }}>
            <div style={{ flex: 1 }}>
              <Input
                label="Min Price"
                type="number"
                value={mappingForm.min_price ?? ""}
                onChange={e => setMappingForm(f => ({ ...f, min_price: e.target.value === "" ? null : Number(e.target.value) }))}
              />
            </div>
            <div style={{ flex: 1 }}>
              <Input
                label="Max Price"
                type="number"
                value={mappingForm.max_price ?? ""}
                onChange={e => setMappingForm(f => ({ ...f, max_price: e.target.value === "" ? null : Number(e.target.value) }))}
              />
            </div>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
            <input
              type="checkbox"
              checked={mappingForm.is_available ?? true}
              onChange={e => setMappingForm(f => ({ ...f, is_available: e.target.checked }))}
            />
            Available for booking
          </label>
          {saveMappingAction.error && <Alert tone="danger">{saveMappingAction.error}</Alert>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <Button variant="secondary" size="sm" onClick={() => setMappingModal(false)}>Cancel</Button>
            <Button
              variant="primary" size="sm"
              disabled={!mappingForm.service_id || saveMappingAction.loading}
              onClick={() => saveMappingAction.execute()}
            >
              {saveMappingAction.loading ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </Modal>
    )}

    {mappingDelete && (
      <Modal open onClose={() => setMappingDelete(null)} title="Remove Service Price">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Remove this priced service from this area? Customers will no longer be matched for it here.
          </p>
          {deleteMappingAction.error && <Alert tone="danger">{deleteMappingAction.error}</Alert>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Button variant="secondary" size="sm" onClick={() => setMappingDelete(null)}>Cancel</Button>
            <Button variant="destructive" size="sm" disabled={deleteMappingAction.loading}
              onClick={() => deleteMappingAction.execute(mappingDelete)}>
              {deleteMappingAction.loading ? "Removing…" : "Remove"}
            </Button>
          </div>
        </div>
      </Modal>
    )}
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
        color: "var(--text-tertiary)", margin: "0 0 10px" }}>{title}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>{children}</div>
    </div>
  );
}

function InfoPair({ label, value, mono, small }: { label: string; value: string; mono?: boolean; small?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontSize: small ? 10 : 12, fontWeight: 600, color: "var(--text-primary)",
        fontFamily: mono ? "monospace" : "inherit", maxWidth: "60%", overflow: "hidden",
        textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value || "Not configured"}</span>
    </div>
  );
}

// ── Delete Confirm Modal ──────────────────────────────────────────────────────
function DeleteConfirmModal({ area, totalActive, loading, onConfirm, onCancel }: {
  area: ProviderServiceArea; totalActive: number;
  loading: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  const isLastActive = area.is_active && totalActive === 1;
  return (
    <Modal open onClose={onCancel} title="Delete service area?"
      footer={<>
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
        <Button variant="destructive" size="sm" loading={loading}
          leftIcon={!loading ? <Trash2 size={12}/> : undefined} onClick={onConfirm}>
          Delete Area
        </Button>
      </>}>
      <div style={{ padding: "12px 16px", background: "var(--surface-sunken)", borderRadius: 10,
        border: "1px solid var(--border)", marginBottom: 16 }}>
        <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          Area: {areaLabel(area)}
        </p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 2px" }}>
          Pincode: {safeText(area.zipcode)}
        </p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          Status: {area.is_active ? "Active" : "Inactive"}
        </p>
      </div>

      <Alert tone="warning">
        Deleting this area may reduce where customers can book your services.
      </Alert>

      {isLastActive && (
        <div style={{ marginTop: 10 }}>
          <Alert tone="danger">
            This is your last active area. Removing it may make your business not bookable.
          </Alert>
        </div>
      )}
    </Modal>
  );
}

// ── Set Primary Confirm Modal ─────────────────────────────────────────────────
function SetPrimaryConfirmModal({ area, loading, onConfirm, onCancel }: {
  area: ProviderServiceArea; loading: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  return (
    <Modal open onClose={onCancel} title={`Set ${areaLabel(area)} as primary area?`}
      footer={<>
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" size="sm" loading={loading}
          leftIcon={!loading ? <Star size={12}/> : undefined} onClick={onConfirm}>
          Set Primary
        </Button>
      </>}>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
        This area will be used as your default coverage area for matching and pricing.
      </p>
    </Modal>
  );
}

// ── Area Wizard ───────────────────────────────────────────────────────────────
function AreaWizard({ initial, existingAreas, limitReached, maxAreas, loading, error, requestId,
  onSubmit, onCancel, submitLabel, isEdit }: {
  initial: ProviderServiceAreaPayload;
  existingAreas: ProviderServiceArea[];
  limitReached: boolean;
  maxAreas: number;
  loading: boolean;
  error: string | null;
  requestId?: string | null;
  onSubmit: (p: ProviderServiceAreaPayload) => void;
  onCancel: () => void;
  submitLabel?: string;
  isEdit?: boolean;
}) {
  const [form, setForm] = useState<ProviderServiceAreaPayload>(initial);
  const [fieldErr, setFieldErr] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<ServiceAreaValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  useEffect(() => { setForm(initial); setValidationResult(null); }, [initial]);

  const f = (key: keyof ProviderServiceAreaPayload, val: unknown) => {
    setForm(prev => ({ ...prev, [key]: val }));
    setValidationResult(null);
  };

  const existingPrimary = existingAreas.find(a => a.is_primary && a.is_active);

  function validateForm(): string | null {
    if (form.coverage_type === "zipcode" && !form.zipcode?.trim()) return "Zipcode is required.";
    if (form.coverage_type === "city"    && !form.city?.trim())    return "City is required.";
    if (form.coverage_type === "zone"    && !form.zone_name?.trim()) return "Zone name is required.";
    if (form.coverage_type === "radius"  && (!form.latitude || !form.longitude || !form.radius_km))
      return "Latitude, longitude, and radius are required.";
    if (!form.state?.trim()) return "State is required.";
    return null;
  }

  async function runValidation() {
    setValidating(true);
    try {
      const res = await providerServiceAreasApi.validate({
        coverage_type: form.coverage_type, state: form.state, district: form.district,
        city: form.city, zipcode: form.zipcode, zone_name: form.zone_name,
        latitude: form.latitude, longitude: form.longitude, radius_km: form.radius_km,
      });
      setValidationResult(res);
      if (res.resolved_city && !form.city) f("city", res.resolved_city);
      if (res.resolved_district && !form.district) f("district", res.resolved_district);
      if (res.resolved_state && !form.state) f("state", res.resolved_state);
    } catch {
      // Section-level: validation preview failure doesn't block manual save.
    } finally { setValidating(false); }
  }

  function handleSubmit() {
    const err = validateForm();
    if (err) { setFieldErr(err); return; }
    setFieldErr(null);
    onSubmit(form);
  }

  const replacingPrimary = form.is_primary && !!existingPrimary && existingPrimary.id !== (initial as { id?: string }).id;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
        Add a city, pincode, zone, or radius where customers can book your services.
      </p>

      {limitReached && !isEdit && (
        <Alert tone="danger">
          Service area limit reached ({maxAreas}/{maxAreas}). Disable or delete an existing area, or upgrade your plan to add more.
        </Alert>
      )}

      {/* Area Type */}
      <div>
        <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 8 }}>
          Area Type
        </label>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {(["zipcode","city","zone","radius"] as AreaType[]).map(t => (
            <Button key={t} variant={form.coverage_type === t ? "primary" : "secondary"} size="sm"
              onClick={() => f("coverage_type", t)}>
              {AREA_TYPE_LABELS[t]}
            </Button>
          ))}
        </div>
      </div>

      {/* Location Details */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Input label="State" required value={form.state ?? ""} onChange={e => f("state", e.target.value)} placeholder="Punjab"/>
        <Input label="District" value={form.district ?? ""} onChange={e => f("district", e.target.value)} placeholder="Ludhiana"/>
      </div>

      {(form.coverage_type === "city" || form.coverage_type === "zipcode") && (
        <Input label="City" required={form.coverage_type === "city"} value={form.city ?? ""}
          onChange={e => f("city", e.target.value)} placeholder="Ludhiana" disabled={isEdit}/>
      )}

      {form.coverage_type === "zipcode" && (
        <div>
          <Input label="Zipcode / Pincode" required value={form.zipcode ?? ""}
            onChange={e => f("zipcode", e.target.value)}
            placeholder="141001" style={{ fontFamily: "monospace" }} disabled={isEdit}/>
          {isEdit && (
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "5px 0 0" }}>
              To change pincode, add a new service area.
            </p>
          )}
        </div>
      )}

      {form.coverage_type === "zone" && (
        <Input label="Zone Name" required value={form.zone_name ?? ""}
          onChange={e => f("zone_name", e.target.value)} placeholder="North Ludhiana" disabled={isEdit}/>
      )}

      {form.coverage_type === "radius" && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Latitude" type="number" value={form.latitude != null ? String(form.latitude) : ""}
              onChange={e => f("latitude", e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="30.9" disabled={isEdit}/>
            <Input label="Longitude" type="number" value={form.longitude != null ? String(form.longitude) : ""}
              onChange={e => f("longitude", e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="75.8" disabled={isEdit}/>
          </div>
          <Input label="Radius (km)" type="number" value={form.radius_km != null ? String(form.radius_km) : ""}
            onChange={e => f("radius_km", e.target.value ? parseFloat(e.target.value) : null)}
            placeholder="10" disabled={isEdit}/>
        </>
      )}

      {!isEdit && (
        <Input label="Country" value={form.country ?? "India"} onChange={e => f("country", e.target.value)}/>
      )}

      {/* Validation Preview */}
      {!isEdit && (
        <ValidationPreviewPanel
          result={validationResult}
          loading={validating}
          onValidate={runValidation}
          canValidate={!validateForm()}
        />
      )}

      {/* Flags */}
      <div style={{ display: "flex", gap: 20 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", userSelect: "none" }}>
          <input type="checkbox" checked={!!form.is_primary} onChange={e => f("is_primary", e.target.checked)}
            style={{ width: 15, height: 15 }}/>
          <span style={{ fontSize: 13, color: "var(--text-primary)" }}>Primary Area</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", userSelect: "none" }}>
          <input type="checkbox" checked={form.is_active ?? true} onChange={e => f("is_active", e.target.checked)}
            style={{ width: 15, height: 15 }}/>
          <span style={{ fontSize: 13, color: "var(--text-primary)" }}>Active</span>
        </label>
      </div>

      {replacingPrimary && (
        <Alert tone="warning">
          Setting this as primary will replace the current primary area ({areaLabel(existingPrimary!)}).
        </Alert>
      )}

      {(fieldErr || error) && (
        <Alert tone="danger">
          <p style={{ margin: 0 }}>{fieldErr ?? error}</p>
          {requestId && (
            <Button variant="ghost" size="sm" leftIcon={<Copy size={10}/>} onClick={() => copyText(requestId)}>
              Request ID: {requestId}
            </Button>
          )}
        </Alert>
      )}

      <Alert tone="info">
        Active service areas count toward your bookability requirement. At least one active area is required to accept bookings.
      </Alert>

      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" size="sm" loading={loading} disabled={limitReached && !isEdit}
          onClick={handleSubmit}>
          {submitLabel ?? "Save"}
        </Button>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function ProviderServiceAreasPage() {
  const areasApi    = useApi(useCallback(() => providerServiceAreasApi.list(), []), []);
  const limitsApi    = useApi(useCallback(() => providerServiceAreasApi.getLimits(), []), []);
  const statusApi   = useApi(useCallback(() => providerStatusApi.get(), []), []);
  const activityApi = useApi(useCallback(() => tenantSetupApi.getActivity(1), []), []);

  const [createOpen,  setCreateOpen]  = useState(false);
  const [editArea,    setEditArea]    = useState<ProviderServiceArea | null>(null);
  const [detailArea,  setDetailArea]  = useState<ProviderServiceArea | null>(null);
  const [deleteArea,  setDeleteArea]  = useState<ProviderServiceArea | null>(null);
  const [primaryArea_, setPrimaryTarget] = useState<ProviderServiceArea | null>(null);
  const [search,      setSearch]      = useState("");
  const [filterStatus,setFilterStatus]= useState<"all"|"active"|"inactive">("all");

  function notify(msg: string, type: "success"|"danger" = "success") {
    pushToast({ tone: type, title: msg });
  }

  const list: ProviderServiceArea[] = areasApi.data?.areas ?? [];
  const totalActive  = list.filter(a => a.is_active).length;
  const primaryArea  = list.find(a => a.is_primary);

  const maxAreas   = limitsApi.data?.max_service_areas ?? DEFAULT_AREA_LIMIT;
  const remaining  = limitsApi.data?.remaining_service_areas ?? Math.max(0, maxAreas - list.length);
  const limitReached = list.length >= maxAreas;
  const slotsUsedPct = maxAreas > 0 ? (list.length / maxAreas) * 100 : 0;

  // Permission-aware — matches backend's require_permission(P.TENANT_SERVICE_AREA_*) gate.
  // No granular permissions array is returned by /v1/auth/me today, so these
  // default to true for any authenticated tenant user (see Remaining Blockers).
  const canCreate = true, canUpdate = true, canDelete = true, canSetPrimary = true;

  // Filtered list
  const filtered = list.filter(a => {
    if (filterStatus === "active"   && !a.is_active)  return false;
    if (filterStatus === "inactive" &&  a.is_active)  return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        areaLabel(a).toLowerCase().includes(q) ||
        (a.zipcode ?? "").includes(q) ||
        (a.city ?? "").toLowerCase().includes(q) ||
        (a.state ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  function refetchAll() {
    areasApi.refetch(); limitsApi.refetch(); statusApi.refetch(); activityApi.refetch();
  }

  const createAction = useAction(useCallback(async (payload: ProviderServiceAreaPayload) => {
    await providerServiceAreasApi.create(payload);
    refetchAll();
    setCreateOpen(false);
    notify("Service area added.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []));

  const updateAction = useAction(useCallback(async (payload: ProviderServiceAreaPayload) => {
    if (!editArea) return;
    await providerServiceAreasApi.update(editArea.id, payload);
    refetchAll();
    setEditArea(null); setDetailArea(null);
    notify("Service area updated.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editArea]));

  const deleteAction = useAction(useCallback(async (id: string) => {
    await providerServiceAreasApi.delete(id);
    refetchAll();
    setDeleteArea(null); setDetailArea(null);
    notify("Service area removed.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []));

  const toggleAction = useAction(useCallback(async (area: ProviderServiceArea) => {
    await providerServiceAreasApi.update(area.id, { coverage_type: area.coverage_type, is_active: !area.is_active });
    refetchAll();
    notify(area.is_active ? "Area disabled." : "Area enabled.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []));

  const setPrimaryAction = useAction(useCallback(async (id: string) => {
    await providerServiceAreasApi.setPrimary(id);
    refetchAll();
    setPrimaryTarget(null);
    notify("Primary area updated.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []));

  // Issues / Action Required list
  const issues: { severity: "warning"|"danger"; title: string; desc: string; action: () => void; actionLabel: string }[] = [];
  if (totalActive === 0) issues.push({
    severity: "danger", title: "Add at least one active area",
    desc: "Add at least one active service area to receive bookings.",
    action: () => setCreateOpen(true), actionLabel: "Add Area",
  });
  if (!primaryArea && list.length > 0) issues.push({
    severity: "warning", title: "Set a primary area",
    desc: "Choose one default service area for matching and pricing.",
    action: () => setPrimaryTarget(list.find(a => a.is_active) ?? list[0]), actionLabel: "Set Primary",
  });
  if (limitReached) issues.push({
    severity: "warning", title: "Upgrade plan to add more areas",
    desc: `You have used all ${maxAreas} service area slots on your current plan.`,
    action: () => {}, actionLabel: "Contact Sales",
  });

  const activities = (()=>{
    const d = activityApi.data as unknown as Record<string,unknown>|null;
    if (!d) return [];
    const list2 = d.events ?? d.activities ?? d.items ?? [];
    return Array.isArray(list2) ? (list2 as unknown[]).slice(0,5) : [];
  })();

  const coverageStatus = totalActive === 0
    ? { label: "Coverage Not Ready", badge: "No Active Areas", tone: "danger" as const,
        banner: "Add at least one active service area to receive bookings." }
    : !primaryArea
    ? { label: "Needs Attention", badge: "Primary Area Missing", tone: "warning" as const,
        banner: "Set a primary area to complete your coverage setup." }
    : { label: "Coverage Ready", badge: "Areas Active", tone: "success" as const,
        banner: `Customers in your active area${totalActive > 1 ? "s" : ""} can discover and book your services.` };

  const heroToneBg = coverageStatus.tone === "success" ? "var(--success-bg)"
    : coverageStatus.tone === "warning" ? "var(--warning-bg)" : "var(--danger-bg)";
  const heroToneBorder = coverageStatus.tone === "success" ? "var(--success-border)"
    : coverageStatus.tone === "warning" ? "var(--warning-border)" : "var(--danger-border)";
  const heroToneText = coverageStatus.tone === "success" ? "var(--success-text)"
    : coverageStatus.tone === "warning" ? "var(--warning-text)" : "var(--danger-text)";

  return (
    <TenantLayout activeNav="provider-service-areas">
      <style>{`
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        @keyframes spin{to{transform:rotate(360deg)}}
        .sa-grid{display:grid;gap:20px}
        .kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
        .sa-cols{display:grid;grid-template-columns:2fr 1fr;gap:20px;align-items:start}
        @media(max-width:1100px){.sa-cols{grid-template-columns:1fr}}
        @media(max-width:768px){.kpi-grid{grid-template-columns:1fr 1fr}}
        @media(max-width:520px){.kpi-grid{grid-template-columns:1fr}}
      `}</style>

      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16,
        fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Tenant Portal</span><ChevronRight size={12}/>
        <span>Setup</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Service Coverage Areas</span>
      </div>

      <div style={{ marginBottom: 24 }}>
        <PageHeader
          title="Service Coverage Areas"
          description="Define where your business can receive customer bookings and manage location readiness."
          actions={<>
            <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={12}/>} onClick={refetchAll}>Refresh</Button>
            {canCreate && (
              <Button variant="primary" size="sm" leftIcon={<Plus size={13}/>} disabled={limitReached}
                onClick={() => setCreateOpen(true)}>
                Add Service Area
              </Button>
            )}
          </>}
        />
      </div>

      <div className="sa-grid">

        {/* Coverage Readiness Hero */}
        <div style={{ background: "#111a2c", borderRadius: 14, padding: "22px 28px", color: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
            flexWrap: "wrap", gap: 28 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, flexShrink: 0 }}>
              <span style={{ width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
                background: heroToneBg, border: `1px solid ${heroToneBorder}`,
                display: "flex", alignItems: "center", justifyContent: "center" }}>
                {coverageStatus.tone === "success"
                  ? <CheckCircle2 size={24} style={{ color: heroToneText }}/>
                  : <XCircle size={24} style={{ color: heroToneText }}/>}
              </span>
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 6px" }}>{coverageStatus.label}</h2>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999,
                  background: heroToneBg, color: heroToneText, border: `1px solid ${heroToneBorder}` }}>
                  {coverageStatus.badge}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", gap: 40, flexWrap: "wrap" }}>
              <HeroMeta label="Active Areas" value={String(totalActive)}/>
              <HeroMeta label="Slots Used" value={`${list.length} / ${maxAreas}`}/>
              <HeroMeta label="Primary Area" value={primaryArea ? areaLabel(primaryArea) : "Not set"}/>
              <HeroMeta label="Remaining Slots" value={String(remaining)}/>
            </div>

            <CoverageRing pct={slotsUsedPct}/>
          </div>
        </div>

        <Alert tone="info">{coverageStatus.banner}</Alert>

        {/* KPI Cards */}
        <KpiGrid minCardWidth={190}>
          <SummaryCard label="Total Areas" value={list.length}
            sub={`${maxAreas} slot${maxAreas === 1 ? "" : "s"} on your plan`}
            icon={<MapPin size={15}/>}/>
          <SummaryCard label="Primary Area" value={primaryArea ? areaLabel(primaryArea) : "Not set"}
            sub={primaryArea ? areaDescription(primaryArea) : "Set a primary area"}
            icon={<Star size={15}/>} tone={primaryArea ? "success" : "warning"}/>
          <SummaryCard label="Coverage Health" value={issues.length === 0 ? "Good" : issues.some(i=>i.severity==="danger") ? "Blocked" : "Needs Attention"}
            sub={issues.length === 0 ? "All checks passing" : `${issues.length} issue${issues.length > 1 ? "s" : ""} found`}
            icon={<Shield size={15}/>} tone={issues.length === 0 ? "success" : issues.some(i=>i.severity==="danger") ? "danger" : "warning"}/>
          <SummaryCard label="Validation Issues" value={issues.length}
            sub={issues.length === 0 ? "No action required" : "Resolve in Action Required panel"}
            icon={<AlertTriangle size={15}/>} tone={issues.length > 0 ? "warning" : "success"}/>
        </KpiGrid>

        {/* Action Required Panel */}
        {issues.length > 0 ? (
          <Card padding="lg">
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px",
              display: "flex", alignItems: "center", gap: 8 }}>
              <AlertTriangle size={15} style={{ color: "var(--warning-text)" }}/> Action Required
            </p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 14px" }}>
              Resolve these issues to optimize coverage and bookability.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {issues.map((iss, i) => {
                const isDanger = iss.severity === "danger";
                return (
                  <div key={i} style={{ padding: "12px 16px", borderRadius: 10,
                    background: isDanger ? "var(--danger-bg)" : "var(--warning-bg)",
                    border: `1px solid ${isDanger ? "var(--danger-border)" : "var(--warning-border)"}`,
                    display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                    <div style={{ display: "flex", gap: 9 }}>
                      <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1,
                        color: isDanger ? "var(--danger-text)" : "var(--warning-text)" }}/>
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 600, margin: "0 0 2px",
                          color: isDanger ? "var(--danger-text)" : "var(--warning-text)" }}>{iss.title}</p>
                        <p style={{ fontSize: 12, margin: 0, opacity: 0.85,
                          color: isDanger ? "var(--danger-text)" : "var(--warning-text)" }}>{iss.desc}</p>
                      </div>
                    </div>
                    {(canCreate || canSetPrimary) && (
                      <Button variant="ghost" size="sm" onClick={iss.action}>{iss.actionLabel}</Button>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        ) : !areasApi.loading && (
          <Alert tone="success" title="All coverage checks are passing.">
            Customers in your active areas can discover your services.
          </Alert>
        )}

        {/* Two-column: table + sidebar */}
        <div className="sa-cols">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Filters */}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <div style={{ position: "relative", flex: 1, minWidth: 200, maxWidth: 320 }}>
                <Search size={13} style={{ position: "absolute", left: 10, top: "50%",
                  transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }}/>
                <Input value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search areas…" style={{ paddingLeft: 32 }}/>
              </div>
              <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
                {(["all","active","inactive"] as const).map(s => (
                  <Button key={s} variant={filterStatus === s ? "primary" : "secondary"} size="sm"
                    onClick={() => setFilterStatus(s)}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </Button>
                ))}
              </div>
              {(search || filterStatus !== "all") && (
                <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setFilterStatus("all"); }}>
                  Clear
                </Button>
              )}
            </div>

            {/* Table */}
            {areasApi.error ? (
              <SectionError title="We couldn't load service coverage" error={areasApi.error}
                requestId={areasApi.requestId} onRetry={areasApi.refetch}/>
            ) : areasApi.loading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[...Array(3)].map((_, i) => <Skeleton key={i} height="4rem" radius="10px"/>)}
              </div>
            ) : filtered.length === 0 ? (
              <Card padding="lg">
                <EmptyState
                  title={list.length === 0 ? "No service areas configured" : "No areas match your filters"}
                  description={list.length === 0
                    ? "Add at least one active service area to allow customers to find and book your services."
                    : "Try adjusting your search or filter settings."}
                  primaryAction={list.length === 0 && canCreate
                    ? <Button variant="primary" size="sm" leftIcon={<Plus size={13}/>} onClick={() => setCreateOpen(true)}>Add Your First Area</Button>
                    : undefined}
                />
              </Card>
            ) : (
              <Card padding="none">
                <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)" }}>
                  <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                    Coverage Areas
                  </p>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                        {["Area Name","State","District","City","Pincode","Zone/Tier","Primary","Status","Updated","Actions"].map(h => (
                          <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 10,
                            fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
                            letterSpacing: "0.06em", whiteSpace: "nowrap" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((a, i) => (
                        <tr key={a.id}
                          style={{ borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none",
                            cursor: "pointer" }}
                          onClick={() => setDetailArea(a)}
                          onMouseEnter={e => (e.currentTarget as HTMLTableRowElement).style.background = "var(--surface-sunken)"}
                          onMouseLeave={e => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}>
                          <td style={{ padding: "12px 14px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                                background: a.is_active ? "var(--success)" : "var(--border)" }}/>
                              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", whiteSpace: "nowrap" }}>
                                {areaLabel(a)}
                              </span>
                            </div>
                          </td>
                          <td style={{ padding: "12px 14px", fontSize: 12, color: "var(--text-secondary)" }}>{safeText(a.state)}</td>
                          <td style={{ padding: "12px 14px", fontSize: 12, color: "var(--text-secondary)" }}>{safeText(a.district)}</td>
                          <td style={{ padding: "12px 14px", fontSize: 12, color: "var(--text-secondary)" }}>{safeText(a.city)}</td>
                          <td style={{ padding: "12px 14px", fontSize: 12, fontFamily: "monospace", color: "var(--text-secondary)" }}>
                            {safeText(a.zipcode)}
                          </td>
                          <td style={{ padding: "12px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                            {a.coverage_type === "zone" ? safeText(a.zone_name) : "Not configured"}
                          </td>
                          <td style={{ padding: "12px 14px" }}>
                            {a.is_primary
                              ? <Star size={14} style={{ color: "var(--warning)" }} fill="var(--warning)"/>
                              : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>No</span>}
                          </td>
                          <td style={{ padding: "12px 14px" }}>
                            <DsStatusBadge status={a.is_active ? "active" : "inactive"} size="sm"/>
                          </td>
                          <td style={{ padding: "12px 14px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                            {safeDate(a.updated_at ?? a.created_at)}
                          </td>
                          <td style={{ padding: "12px 14px" }}>
                            <div style={{ display: "flex", gap: 4 }}>
                              <Button variant="icon" size="sm" aria-label="View Details"
                                onClick={e => { e.stopPropagation(); setDetailArea(a); }}>
                                <Eye size={11}/>
                              </Button>
                              {canUpdate && (
                                <Button variant="icon" size="sm" aria-label="Edit"
                                  onClick={e => { e.stopPropagation(); setEditArea(a); }}>
                                  <Edit2 size={11}/>
                                </Button>
                              )}
                              {canSetPrimary && !a.is_primary && (
                                <Button variant="icon" size="sm" aria-label="Set as Primary"
                                  style={{ color: "var(--warning)" }}
                                  onClick={e => { e.stopPropagation(); setPrimaryTarget(a); }}>
                                  <Star size={11}/>
                                </Button>
                              )}
                              {canDelete && (
                                <Button variant="icon" size="sm" aria-label="Delete"
                                  style={{ color: "var(--danger-text)" }}
                                  onClick={e => { e.stopPropagation(); setDeleteArea(a); }}>
                                  <Trash2 size={11}/>
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </TableSurface>
                </div>
                <div style={{ padding: "10px 16px", borderTop: "1px solid var(--border)",
                  fontSize: 11, color: "var(--text-tertiary)", display: "flex", justifyContent: "space-between" }}>
                  <span>{list.length} area{list.length !== 1 ? "s" : ""}</span>
                  <span>{list.length} / {maxAreas} slots used</span>
                </div>
              </Card>
            )}
          </div>

          {/* Right sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Coverage Summary */}
            <Card padding="md">
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>
                Coverage Summary
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <SummaryRow icon={<CheckCircle2 size={13}/>} label="Bookable Areas" value={String(totalActive)}/>
                <SummaryRow icon={<Plus size={13}/>} label="Unused Slots" value={String(remaining)}/>
                <SummaryRow icon={<MapPin size={13}/>} label="Zone Match"
                  value={primaryArea ? safeZoneTier((primaryArea as unknown as { resolved_zone_tier?: string }).resolved_zone_tier) : "Not configured"}/>
                <SummaryRow icon={<Activity size={13}/>} label="Last Sync" value="Today"/>
              </div>
            </Card>

            {/* Coverage Rules */}
            <Card padding="md">
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px",
                display: "flex", alignItems: "center", gap: 6 }}>
                <ListChecks size={14}/> Coverage Rules
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <RuleRow ok={!!primaryArea} text="One primary area required"/>
                <RuleRow ok={!limitReached} text={`Maximum ${maxAreas} service areas on current plan`}/>
                <RuleRow ok={totalActive > 0} text="Active areas are visible for customer matching"/>
              </div>
            </Card>

            {/* Recent Activity */}
            <Card padding="md">
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px",
                display: "flex", alignItems: "center", gap: 6 }}>
                <Activity size={14}/> Recent Activity
              </p>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "0 0 12px" }}>
                Service area updates and coverage events.
              </p>

              {activityApi.error ? (
                <SectionError title="Could not load activity" error={activityApi.error}
                  requestId={activityApi.requestId} onRetry={activityApi.refetch}/>
              ) : activityApi.loading ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {[...Array(2)].map((_, i) => <Skeleton key={i} height="2.75rem" radius="8px"/>)}
                </div>
              ) : activities.length === 0 ? (
                <div style={{ padding: "18px 8px", textAlign: "center", color: "var(--text-tertiary)" }}>
                  <Activity size={24} style={{ opacity: 0.25, marginBottom: 6 }}/>
                  <p style={{ fontSize: 12, margin: 0 }}>No service area activity yet.</p>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                  {activities.map((ev: unknown, i: number) => {
                    const e = ev as Record<string, unknown>;
                    return (
                      <div key={i} style={{ padding: "9px 0",
                        borderBottom: i < activities.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <p style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)", margin: "0 0 2px" }}>
                          {safeText(e.action ?? e.event_type ?? e.type, "Activity event")}
                        </p>
                        <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>
                          {safeDate(e.created_at ?? e.timestamp)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
              <Link href="/activity" style={{ fontSize: 11, color: "var(--brand)", textDecoration: "none",
                display: "flex", alignItems: "center", gap: 3, marginTop: 10 }}>
                View all activity <ChevronRight size={11}/>
              </Link>
            </Card>
          </div>
        </div>
      </div>

      {/* DRAWERS & MODALS */}

      {detailArea && (
        <AreaDetailDrawer
          area={detailArea}
          totalActive={totalActive}
          maxAreas={maxAreas}
          onClose={() => setDetailArea(null)}
          onEdit={() => { setEditArea(detailArea); setDetailArea(null); }}
          onDelete={() => { setDeleteArea(detailArea); setDetailArea(null); }}
          onToggle={() => toggleAction.execute(detailArea)}
        />
      )}

      {deleteArea && (
        <DeleteConfirmModal
          area={deleteArea}
          totalActive={totalActive}
          loading={deleteAction.loading}
          onConfirm={() => deleteAction.execute(deleteArea.id)}
          onCancel={() => setDeleteArea(null)}
        />
      )}

      {primaryArea_ && (
        <SetPrimaryConfirmModal
          area={primaryArea_}
          loading={setPrimaryAction.loading}
          onConfirm={() => setPrimaryAction.execute(primaryArea_.id)}
          onCancel={() => setPrimaryTarget(null)}
        />
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add Service Area">
        <AreaWizard
          initial={{ ...BLANK }}
          existingAreas={list}
          limitReached={limitReached}
          maxAreas={maxAreas}
          loading={createAction.loading}
          error={createAction.error}
          requestId={createAction.requestId}
          onSubmit={p => createAction.execute(p)}
          onCancel={() => setCreateOpen(false)}
          submitLabel="Add Area"
        />
      </Modal>

      <Modal open={editArea !== null} onClose={() => setEditArea(null)} title="Edit Service Area">
        {editArea && (
          <AreaWizard
            initial={{
              coverage_type: editArea.coverage_type as AreaType,
              country:   editArea.country ?? "India",
              state:     editArea.state ?? "",
              district:  editArea.district ?? "",
              city:      editArea.city ?? "",
              zipcode:   editArea.zipcode ?? "",
              zone_name: editArea.zone_name ?? "",
              latitude:  editArea.latitude,
              longitude: editArea.longitude,
              radius_km: editArea.radius_km,
              is_primary: editArea.is_primary,
              is_active:  editArea.is_active,
            }}
            existingAreas={list.filter(a => a.id !== editArea.id)}
            limitReached={false}
            maxAreas={maxAreas}
            loading={updateAction.loading}
            error={updateAction.error}
            requestId={updateAction.requestId}
            onSubmit={p => updateAction.execute(p)}
            onCancel={() => setEditArea(null)}
            submitLabel="Save Changes"
            isEdit
          />
        )}
      </Modal>
    </TenantLayout>
  );
}

function HeroMeta({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 12, fontWeight: 500, color: "rgba(255,255,255,0.55)" }}>{label}</span>
      <span style={{ fontSize: 16, color: "#fff", fontWeight: 700 }}>{value}</span>
    </div>
  );
}

function SummaryRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ color: "var(--text-tertiary)" }}>{icon}</span>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

function RuleRow({ ok, text }: { ok: boolean; text: string }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
      {ok
        ? <CheckCircle2 size={14} style={{ color: "var(--success-text)", flexShrink: 0, marginTop: 1 }}/>
        : <AlertTriangle size={14} style={{ color: "var(--warning-text)", flexShrink: 0, marginTop: 1 }}/>}
      <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{text}</span>
    </div>
  );
}
