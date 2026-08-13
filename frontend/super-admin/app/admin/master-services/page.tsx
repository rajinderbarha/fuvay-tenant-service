"use client";
import React, { useState, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, SummaryCard,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  catalogApi,
  type MasterService, type MasterServiceEnriched,
  type MasterServicesSummary, type ServiceCategory, type ServiceGroup,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { ChevronRight, Download, RefreshCw, AlertCircle } from "lucide-react";

// ── Constant maps ───────────────────────────────────────────────────────────────
const JOB_TYPES = [
  { value: "repair",          label: "Repair" },
  { value: "installation",    label: "Installation" },
  { value: "uninstallation",  label: "Uninstallation" },
  { value: "inspection",      label: "Inspection" },
  { value: "maintenance",     label: "Maintenance" },
  { value: "cleaning",        label: "Cleaning" },
  { value: "consultation",    label: "Consultation" },
  { value: "service",         label: "Service" },
  { value: "custom",          label: "Custom" },
];
const PRICING_MODELS = [
  { value: "fixed",           label: "Fixed" },
  { value: "range",           label: "Range" },
  { value: "post_assessment", label: "Post-Assessment" },
  { value: "hourly",          label: "Hourly" },
];
const PRICING_MODEL_HELP: Record<string, string> = {
  fixed:           "Customer sees one fixed service price.",
  range:           "Customer sees estimated min–max range.",
  post_assessment: "Customer pays inspection visit fee; quote shared after assessment.",
  hourly:          "Customer is charged based on time spent.",
};
const JOB_TYPE_DEFAULTS: Record<string, Partial<FormRequirements>> = {
  repair:         { requires_issue_type: true,  is_brand_required: true,  is_type_required: true,  requires_checklist: true,  requires_schedule: false, requires_address: false },
  installation:   { requires_issue_type: false, is_brand_required: true,  is_type_required: true,  requires_checklist: true,  requires_schedule: true,  requires_address: true  },
  uninstallation: { requires_issue_type: false, is_brand_required: false, is_type_required: true,  requires_checklist: true,  requires_schedule: false, requires_address: false },
  inspection:     { requires_issue_type: true,  is_brand_required: false, is_type_required: false, requires_checklist: true,  requires_schedule: true,  requires_address: false },
  maintenance:    { requires_issue_type: false, is_brand_required: false, is_type_required: true,  requires_checklist: true,  requires_schedule: true,  requires_address: false },
  cleaning:       { requires_issue_type: false, is_brand_required: false, is_type_required: true,  requires_checklist: true,  requires_schedule: false, requires_address: false },
  consultation:   { requires_issue_type: false, is_brand_required: false, is_type_required: false, requires_checklist: false, requires_schedule: true,  requires_address: false },
  service:        { requires_issue_type: false, is_brand_required: false, is_type_required: false, requires_checklist: true,  requires_schedule: false, requires_address: false },
  custom:         { requires_issue_type: false, is_brand_required: false, is_type_required: false, requires_checklist: false, requires_schedule: false, requires_address: false },
};

const READINESS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  ready: "success", fallback_only: "warning", missing_rules: "danger",
  inactive: "muted", not_required: "muted",
  missing_brand_mapping: "warning", missing_service_options: "warning",
  missing_issue_types: "warning", missing_pricing: "danger",
};
const READINESS_LABEL: Record<string, string> = {
  ready: "Ready", fallback_only: "Fallback", missing_rules: "No Rules",
  inactive: "Inactive", not_required: "—",
  missing_brand_mapping: "No Brands", missing_service_options: "No Options",
  missing_issue_types: "No Issues", missing_pricing: "No Pricing",
};

// ── Form types ─────────────────────────────────────────────────────────────────
type FormRequirements = {
  requires_issue_type: boolean;
  is_brand_required: boolean;
  is_type_required: boolean;
  requires_checklist: boolean;
  requires_schedule: boolean;
  requires_address: boolean;
};
type FormState = {
  name: string;
  category_id: string;
  service_group_id: string;
  job_type: string;
  pricing_model: string;
  base_price: string;
  min_price: string;
  max_price: string;
  description: string;
  unit_label: string;
  is_active: boolean;
  icon_url: string;
} & FormRequirements;

const BLANK: FormState = {
  name: "", category_id: "", service_group_id: "", job_type: "service",
  pricing_model: "fixed", base_price: "", min_price: "", max_price: "",
  description: "", unit_label: "per visit", is_active: true, icon_url: "",
  ...JOB_TYPE_DEFAULTS.service,
} as FormState;

// ── Summary card ───────────────────────────────────────────────────────────────

// ── Chip group display ─────────────────────────────────────────────────────────
function ReqChips({ svc }: { svc: MasterServiceEnriched }) {
  const flags: { label: string; on: boolean }[] = [
    { label: "Brand", on: !!svc.is_brand_required },
    { label: "Type",  on: !!svc.is_type_required },
    { label: "Issue", on: !!svc.requires_issue_type },
    { label: "Checklist", on: !!svc.requires_checklist },
    { label: "Schedule",  on: !!svc.requires_schedule },
    { label: "Address",   on: !!svc.requires_address },
  ].filter(f => f.on);
  if (!flags.length) return <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>None</span>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {flags.map(f => (
        <span key={f.label} style={{
          fontSize: 10, padding: "2px 6px", borderRadius: 4,
          background: "var(--brand-muted, rgba(26,86,219,.08))", color: "var(--brand, #1a56db)", fontWeight: 600,
        }}>{f.label}</span>
      ))}
    </div>
  );
}

// ── Linked counts display ──────────────────────────────────────────────────────
function LinkedCounts({ lc }: { lc: MasterServiceEnriched["linked_counts"] }) {
  const items = [
    { k: "brands", label: "Br" },
    { k: "options", label: "Opt" },
    { k: "issues", label: "Iss" },
    { k: "pricing_rules", label: "Pr" },
    { k: "providers", label: "Prov" },
  ] as const;
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {items.map(({ k, label }) => (
        <div key={k} style={{ textAlign: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: lc[k] === 0 ? "var(--text-tertiary, var(--text-secondary))" : "var(--text-primary)" }}>{lc[k]}</span>
          <span style={{ fontSize: 10, color: "var(--text-secondary)", marginLeft: 2 }}>{label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Action menu ────────────────────────────────────────────────────────────────
function ServiceActionMenu({ row, onEdit, onActivate, onDeactivate, onArchive, onView }: {
  row: MasterServiceEnriched;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onArchive: () => void;
  onView: () => void;
}) {
  const [open, setOpen] = useState(false);
  const items = [
    { label: "View Details", action: onView },
    { label: "Edit Service", action: onEdit },
    null,
    !row.is_active ? { label: "Activate", action: onActivate } : null,
    row.is_active ? { label: "Deactivate", action: onDeactivate } : null,
    { label: "Archive", action: onArchive, danger: true },
  ];
  return (
    <div style={{ position: "relative" }} onClick={e => e.stopPropagation()}>
      <Btn variant="ghost" size="xs" onClick={() => setOpen(o => !o)}>Actions ▾</Btn>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 1000 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", right: 0, top: "100%", zIndex: 1001, marginTop: 4,
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, minWidth: 180, boxShadow: "0 8px 24px rgba(0,0,0,.12)",
            overflow: "hidden",
          }}>
            {items.map((item, i) =>
              item === null ? (
                <hr key={i} style={{ margin: 0, border: "none", borderTop: "1px solid var(--border)" }} />
              ) : item ? (
                <button key={i} onClick={() => { setOpen(false); item.action(); }} style={{
                  display: "block", width: "100%", textAlign: "left",
                  padding: "9px 16px", fontSize: 13, background: "none", border: "none",
                  cursor: "pointer", color: item.danger ? "var(--danger-text, #e53e3e)" : "var(--text-primary)",
                }}>
                  {item.label}
                </button>
              ) : null
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Brand management modal ──────────────────────────────────────────────────────
function BrandManagementModal({ svc, onClose }: { svc: MasterServiceEnriched; onClose: () => void }) {
  const brandMgmtService = svc;
  const mappings = useApi(useCallback(() => catalogApi.listBrandMappings(brandMgmtService.id), [brandMgmtService.id]));
  const allBrands = useApi(useCallback(() => catalogApi.listBrands({ status: "active", page_size: 200 }), []));
  const [selectedBrandToAdd, setSelectedBrandToAdd] = useState("");

  const mapBrandServices = useAction(async (brandId: string) => {
    await catalogApi.mapBrand(brandMgmtService.id, brandId);
  });

  const mapped = mappings.data?.brands ?? [];
  const mappedIds = new Set(mapped.map(m => m.brand_id));
  const available = (allBrands.data?.brands ?? []).filter(b => !mappedIds.has(b.brand_id));

  const handleAdd = async () => {
    if (!selectedBrandToAdd) return;
    await mapBrandServices.execute(selectedBrandToAdd);
    setSelectedBrandToAdd("");
    mappings.refetch();
  };

  return (
    <Modal open onClose={onClose} title={`Manage Brands — ${brandMgmtService.name}`}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 380 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <Select value={selectedBrandToAdd} onChange={setSelectedBrandToAdd}
            options={[{ value: "", label: "Select a brand to add…" },
              ...available.map(b => ({ value: b.brand_id, label: b.name }))]} />
          <Btn variant="primary" size="sm" onClick={handleAdd} disabled={!selectedBrandToAdd || mapBrandServices.loading}>
            {mapBrandServices.loading ? "Adding…" : "Add"}
          </Btn>
        </div>
        <div>
          {mappings.loading ? (
            <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Loading brand mappings…</p>
          ) : mapped.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>No brands mapped to this service yet.</p>
          ) : (
            mapped.map(m => (
              <div key={m.mapping_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "8px 0", borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                <span style={{ fontSize: 13 }}>{m.name}</span>
                {m.is_required && <Badge variant="warning">Required</Badge>}
              </div>
            ))
          )}
        </div>
      </div>
    </Modal>
  );
}

// ── Detail drawer ──────────────────────────────────────────────────────────────
function ServiceDetailDrawer({ svc, catMap, groupMap, onClose }: {
  svc: MasterServiceEnriched | null;
  catMap: Record<string, string>;
  groupMap: Record<string, string>;
  onClose: () => void;
}) {
  const [showBrandMgmt, setShowBrandMgmt] = useState(false);
  if (!svc) return null;
  const lc = svc.linked_counts;
  const reqFlags = [
    ["Brand Required", svc.is_brand_required],
    ["Type Required", svc.is_type_required],
    ["Issue Type", svc.requires_issue_type],
    ["Checklist", svc.requires_checklist],
    ["Schedule", svc.requires_schedule],
    ["Address", svc.requires_address],
  ] as [string, boolean | undefined][];

  const priceDisplay = svc.pricing_model === "range"
    ? `${svc.min_price ?? 0} – ${svc.max_price ?? 0} ${svc.currency ?? "AED"}`
    : svc.pricing_model === "post_assessment"
    ? `Visit fee: ${svc.base_price ?? 0} ${svc.currency ?? "AED"}`
    : `${svc.base_price ?? 0} ${svc.currency ?? "AED"} / ${svc.unit_label ?? "visit"}`;

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, height: "100vh", width: 440, zIndex: 2000,
      background: "var(--surface)", borderLeft: "1px solid var(--border)",
      overflowY: "auto", boxShadow: "-4px 0 24px rgba(0,0,0,.12)",
    }}>
      <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{svc.name}</h3>
          <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
            <Badge variant={svc.is_active ? "success" : "muted"}>{svc.is_active ? "Active" : "Inactive"}</Badge>
            <Badge variant={READINESS_VARIANT[svc.runtime_readiness] ?? "muted"}>
              Runtime: {READINESS_LABEL[svc.runtime_readiness] ?? svc.runtime_readiness}
            </Badge>
          </div>
        </div>
        <Btn variant="ghost" size="xs" onClick={onClose}>✕</Btn>
      </div>

      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Catalog hierarchy */}
        <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span>{catMap[svc.category_id] ?? "—"}</span>
          {svc.service_group_id && <><ChevronRight size={12} /><span>{groupMap[svc.service_group_id] ?? "—"}</span></>}
          <ChevronRight size={12} />
          <span style={{ color: "var(--brand, #1a56db)", fontWeight: 600 }}>{svc.name}</span>
        </div>

        {/* Core info */}
        <section>
          <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Service Details</p>
          {[
            ["Job Type",       JOB_TYPES.find(j => j.value === svc.job_type)?.label ?? svc.job_type],
            ["Pricing Model",  PRICING_MODELS.find(p => p.value === svc.pricing_model)?.label ?? svc.pricing_model],
            ["Base Pricing",   priceDisplay],
            ["Description",    svc.description || "—"],
          ].map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--border-subtle, var(--border))", fontSize: 13 }}>
              <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{k}</span>
              <span style={{ color: "var(--text-primary)", textAlign: "right", maxWidth: 250, wordBreak: "break-word" }}>{v}</span>
            </div>
          ))}
        </section>

        {/* Pricing readiness */}
        <section>
          <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Pricing Readiness</p>
          <Badge variant={READINESS_VARIANT[svc.pricing_readiness] ?? "muted"}>
            {READINESS_LABEL[svc.pricing_readiness] ?? svc.pricing_readiness}
          </Badge>
          <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
            {lc.pricing_rules} pricing rule{lc.pricing_rules !== 1 ? "s" : ""} linked
          </p>
        </section>

        {/* Requirements */}
        <section>
          <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Requirements</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {reqFlags.map(([label, on]) => (
              <span key={label} style={{
                fontSize: 12, padding: "4px 10px", borderRadius: 6, fontWeight: 500,
                background: on ? "var(--brand-muted, rgba(26,86,219,.08))" : "var(--surface-alt, var(--surface))",
                color: on ? "var(--brand, #1a56db)" : "var(--text-tertiary, var(--text-secondary))",
                border: `1px solid ${on ? "var(--brand-border, rgba(26,86,219,.2))" : "var(--border)"}`,
              }}>{label}: {on ? "Yes" : "No"}</span>
            ))}
          </div>
        </section>

        {/* Linked resources */}
        <section>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <p style={{ margin: 0, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Linked Resources</p>
            <Btn variant="ghost" size="xs" onClick={() => setShowBrandMgmt(true)}>Manage Brands</Btn>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            {[
              { label: "Brands",       count: lc.brands },
              { label: "Options",      count: lc.options },
              { label: "Issues",       count: lc.issues },
              { label: "Pricing Rules", count: lc.pricing_rules },
              { label: "Providers",    count: lc.providers },
              { label: "Service Types", count: lc.service_types },
            ].map(({ label, count }) => (
              <div key={label} style={{ background: "var(--surface-alt, var(--surface))", border: "1px solid var(--border)", borderRadius: 10, padding: "10px 12px", textAlign: "center" }}>
                <p style={{ margin: 0, fontSize: 20, fontWeight: 700, color: count === 0 ? "var(--text-tertiary, var(--text-secondary))" : "var(--text-primary)" }}>{count}</p>
                <p style={{ margin: "3px 0 0", fontSize: 10, color: "var(--text-secondary)" }}>{label}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
      {showBrandMgmt && <BrandManagementModal svc={svc} onClose={() => setShowBrandMgmt(false)} />}
    </div>
  );
}

// ── Requirement toggle row ────────────────────────────────────────────────────
function ReqToggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0" }}>
      <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{label}</span>
      <button onClick={() => onChange(!value)} style={{
        width: 40, height: 22, borderRadius: 11, border: "none", cursor: "pointer", position: "relative",
        background: value ? "var(--brand, #1a56db)" : "var(--border)",
        transition: "background .2s",
      }}>
        <span style={{
          position: "absolute", top: 2, left: value ? 20 : 2, width: 18, height: 18,
          borderRadius: "50%", background: "#fff", transition: "left .2s",
        }} />
      </button>
    </div>
  );
}

// ── New Master Service -- canonical creation (migration 160) ────────────────
// Job-type-agnostic: Service Group, Service Name, Description, Display Order
// only. No Job Type, Pricing Model, prices, or Brand/Type/workflow
// requirement fields -- those are added afterward as Job-Type Blueprint
// child records in the Catalog Workspace, which this navigates to on success.
function MasterServiceCreateModal({ open, onClose, onCreated, catOptions, allGroups }: {
  open: boolean; onClose: () => void; onCreated: () => void;
  catOptions: { value: string; label: string }[];
  allGroups: { id: string; name: string; category_id: string }[];
}) {
  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [description, setDescription] = useState("");
  const [displayOrder, setDisplayOrder] = useState(0);
  const [iconUrl, setIconUrl] = useState<string | null>(null);
  const createAction = useAction(catalogApi.createMasterServiceV2);

  const groupOptions = useMemo(
    () => allGroups.filter(g => !categoryId || g.category_id === categoryId).map(g => ({ value: g.id, label: g.name })),
    [allGroups, categoryId]);

  function reset() {
    setName(""); setCategoryId(""); setGroupId(""); setDescription(""); setDisplayOrder(0); setIconUrl(null);
  }

  async function submit() {
    const result = await createAction.execute({
      service_name: name.trim(), category_id: categoryId, service_group_id: groupId,
      description: description.trim() || undefined, display_order: displayOrder,
      icon_url: iconUrl || undefined,
    });
    if (result) { reset(); onCreated(); }
  }

  const canSave = !!name.trim() && !!categoryId && !!groupId;

  return (
    <Modal open={open} onClose={onClose} title="New Master Service">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {createAction.error && (
          <div style={{ padding: "10px 14px", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
            <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{createAction.error}</p>
          </div>
        )}
        <Input label="Service Name *" placeholder="e.g. Air Conditioner" value={name} onChange={setName}/>
        <Select label="Business Vertical *" value={categoryId}
          onChange={v => { setCategoryId(v); setGroupId(""); }}
          options={catOptions} placeholder="Select…"/>
        <Select label="Service Group *" value={groupId} onChange={setGroupId}
          options={groupOptions} placeholder={categoryId ? "Select…" : "Select a vertical first"}/>
        <Input label="Description" placeholder="Optional description for this service"
          value={description} onChange={setDescription}/>
        <Input label="Display Order" type="number" value={String(displayOrder)}
          onChange={v => setDisplayOrder(parseInt(v, 10) || 0)}/>
        <IconPicker label="Icon" context="service_icon" value={iconUrl} onChange={setIconUrl}/>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Job types (Repair, Installation, …), pricing behavior, and Brand/Type requirements are
          configured after creation, per job type, in this service's Job-Type Blueprint.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={createAction.loading} disabled={!canSave} onClick={submit}>
            Create Service
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function MasterServicesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Filters
  const [q, setQ] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [groupFilter, setGroupFilter] = useState(() => searchParams.get("service_group_id") ?? "");
  const [jobTypeFilter, setJobTypeFilter] = useState("");
  const [pricingModelFilter, setPricingModelFilter] = useState("");
  const [isActiveFilter, setIsActiveFilter] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Modal / detail
  const [modal, setModal] = useState<"none" | "create-service" | "edit">("none");
  const [editing, setEditing] = useState<MasterServiceEnriched | null>(null);
  const [detailSvc, setDetailSvc] = useState<MasterServiceEnriched | null>(null);
  const [archiveId, setArchiveId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>({ ...BLANK });
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  // Data
  // BUG FIX: useApi(fetcher, deps) needs deps passed to BOTH the inner
  // useCallback AND useApi itself -- its own `run` callback was memoized
  // with an empty/stale deps array, so category/group/filter changes never
  // actually refetched (same pattern already fixed on other pages this
  // session).
  const summary = useApi(useCallback(() => catalogApi.getMasterServicesSummary(), []), []);
  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []), []);
  const allGroups = useApi(useCallback(
    () => catalogApi.listServiceGroups({ categoryId: categoryFilter || undefined }),
    [categoryFilter],
  ), [categoryFilter]);
  const services = useApi(useCallback(
    () => catalogApi.listMasterServicesEnterprise({
      q: q || undefined,
      categoryId: categoryFilter || undefined,
      serviceGroupId: groupFilter || undefined,
      jobType: jobTypeFilter || undefined,
      pricingModel: pricingModelFilter || undefined,
      isActive: isActiveFilter === "" ? undefined : isActiveFilter === "true",
      limit: pageSize,
      offset: (page - 1) * pageSize,
    }),
    [q, categoryFilter, groupFilter, jobTypeFilter, pricingModelFilter, isActiveFilter, page],
  ), [q, categoryFilter, groupFilter, jobTypeFilter, pricingModelFilter, isActiveFilter, page]);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const catMap = useMemo(() => {
    const m: Record<string, string> = {};
    (categories.data?.categories ?? []).forEach((c: ServiceCategory) => { m[c.category_id] = c.name; });
    return m;
  }, [categories.data]);

  const groupMap = useMemo(() => {
    const m: Record<string, string> = {};
    (allGroups.data?.groups ?? []).forEach((g: ServiceGroup) => { m[g.id] = g.name; });
    return m;
  }, [allGroups.data]);

  const catOptions = useMemo(() =>
    (categories.data?.categories ?? []).map((c: ServiceCategory) => ({ value: c.category_id, label: c.name })),
    [categories.data]);

  const groupOptions = useMemo(() =>
    (allGroups.data?.groups ?? []).map((g: ServiceGroup) => ({ value: g.id, label: g.name })),
    [allGroups.data]);

  // Actions
  const editAction = useAction(async ({ id, data }: { id: string; data: FormState }) => {
    await catalogApi.updateMasterService(id, {
      service_name: data.name, job_type: data.job_type, pricing_model: data.pricing_model as "fixed" | "range" | "post_assessment" | "hourly",
      service_group_id: data.service_group_id || undefined,
      // base_price/min_price/max_price are no longer admin-writable
      // (MODULE-L5-56) -- pricing is tenant-owned only.
      description: data.description || undefined,
      unit_label: data.unit_label || undefined,
      icon_url: data.icon_url || undefined,
      is_active: data.is_active,
      // Brand/Type/Issue/Checklist/Schedule/Address requirements are no
      // longer edited from this form -- they are configured per exact Job
      // Type in the Job-Type Blueprint (Dimensions/Problems & Questions/
      // Checklist/Workflow tabs). Existing values are left untouched here.
    });
    services.refetch(); summary.refetch(); setModal("none"); notify("Service updated.");
  });

  const activateAction = useAction(async (id: string) => {
    await catalogApi.activateMasterService(id);
    services.refetch(); summary.refetch(); notify("Service activated.");
  });

  const deactivateAction = useAction(async (id: string) => {
    await catalogApi.deactivateMasterService(id);
    services.refetch(); summary.refetch(); notify("Service deactivated.");
  });

  const archiveAction = useAction(async (id: string) => {
    await catalogApi.archiveMasterService(id);
    services.refetch(); summary.refetch(); setArchiveId(null); notify("Service archived.");
  });

  const exportAction = useAction(async () => {
    const result = await catalogApi.exportMasterServices({
      categoryId: categoryFilter || undefined,
      jobType: jobTypeFilter || undefined,
    });
    const rows = result?.rows ?? [];
    const csv = [
      ["Name", "Category", "Group", "Job Type", "Pricing Model", "Brands", "Options", "Issues", "Pricing Rules", "Providers", "Pricing Readiness", "Runtime Readiness", "Active"].join(","),
      ...rows.map((r: MasterServiceEnriched) => [
        `"${r.name}"`,
        `"${catMap[r.category_id] ?? r.category_id}"`,
        `"${r.service_group_id ? (groupMap[r.service_group_id] ?? r.service_group_id) : ""}"`,
        r.job_type, r.pricing_model,
        r.linked_counts?.brands ?? 0, r.linked_counts?.options ?? 0,
        r.linked_counts?.issues ?? 0, r.linked_counts?.pricing_rules ?? 0,
        r.linked_counts?.providers ?? 0,
        r.pricing_readiness, r.runtime_readiness, r.is_active ? "Yes" : "No",
      ].join(","))
    ].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "master-services.csv"; a.click();
    notify("Exported.");
  });

  function openCreate() { setModal("create-service"); }
  function openEdit(svc: MasterServiceEnriched) {
    setForm({
      name: svc.name, category_id: svc.category_id,
      service_group_id: svc.service_group_id ?? "",
      job_type: svc.job_type, pricing_model: svc.pricing_model,
      base_price: svc.base_price != null ? String(svc.base_price) : "",
      min_price: svc.min_price != null ? String(svc.min_price) : "",
      max_price: svc.max_price != null ? String(svc.max_price) : "",
      description: svc.description ?? "", unit_label: svc.unit_label ?? "per visit",
      icon_url: svc.icon_url ?? "",
      is_active: svc.is_active,
      requires_issue_type: !!svc.requires_issue_type,
      is_brand_required: !!svc.is_brand_required,
      is_type_required: !!svc.is_type_required,
      requires_checklist: !!svc.requires_checklist,
      requires_schedule: !!svc.requires_schedule,
      requires_address: !!svc.requires_address,
    });
    setEditing(svc); setModal("edit");
  }
  function setF<K extends keyof FormState>(k: K, v: FormState[K]) { setForm(p => ({ ...p, [k]: v })); }
  function applyJobTypeDefaults(jt: string) {
    const defaults = JOB_TYPE_DEFAULTS[jt] ?? {};
    setForm(p => ({ ...p, job_type: jt, ...defaults }));
  }

  const canSave = !!form.name && !!form.category_id && !!form.job_type && !!form.pricing_model;
  const s = summary.data;
  const rows = services.data?.services ?? [];
  const activeAction = editAction;

  const columns = [
    {
      key: "name", label: "Service",
      render: (_: unknown, row: MasterServiceEnriched) => (
        <div>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.name}</span>
          <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>
            {catMap[row.category_id] ?? "—"}
            {row.service_group_id ? ` › ${groupMap[row.service_group_id] ?? "—"}` : ""}
          </p>
        </div>
      ),
    },
    {
      key: "job_type", label: "Job Type", width: 110,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant="muted">{JOB_TYPES.find(j => j.value === row.job_type)?.label ?? row.job_type}</Badge>
      ),
    },
    {
      key: "pricing_model", label: "Pricing Model", width: 110,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {PRICING_MODELS.find(p => p.value === row.pricing_model)?.label ?? row.pricing_model}
        </span>
      ),
    },
    {
      key: "requires_issue_type", label: "Requirements",
      render: (_: unknown, row: MasterServiceEnriched) => <ReqChips svc={row} />,
    },
    {
      key: "linked_counts", label: "Linked Setup",
      render: (_: unknown, row: MasterServiceEnriched) => <LinkedCounts lc={row.linked_counts} />,
    },
    {
      key: "pricing_readiness", label: "Pricing",
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant={READINESS_VARIANT[row.pricing_readiness] ?? "muted"}>
          {READINESS_LABEL[row.pricing_readiness] ?? row.pricing_readiness}
        </Badge>
      ),
    },
    {
      key: "runtime_readiness", label: "Runtime",
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant={READINESS_VARIANT[row.runtime_readiness] ?? "muted"}>
          {READINESS_LABEL[row.runtime_readiness] ?? row.runtime_readiness}
        </Badge>
      ),
    },
    {
      key: "is_active", label: "Status", width: 90,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge>
      ),
    },
    {
      key: "id", label: "", width: 120,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <ServiceActionMenu
          row={row}
          onView={() => setDetailSvc(row)}
          onEdit={() => openEdit(row)}
          onActivate={() => activateAction.execute(row.id)}
          onDeactivate={() => deactivateAction.execute(row.id)}
          onArchive={() => setArchiveId(row.id)}
        />
      ),
    },
  ];

  return (
    <AdminLayout activeNav="master-services">
      <SectionHeader
        title="Master Services"
        subtitle="Platform-wide service catalog. Pricing rules are managed in Pricing → Pricing Rules, not stored here."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" loading={exportAction.loading} onClick={() => exportAction.execute()}>
              <Download size={14} style={{ marginRight: 4 }} /> Export
            </Btn>
            <Btn variant="secondary" size="sm" onClick={() => { services.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
            </Btn>
            <Btn variant="primary" size="sm" onClick={openCreate}>+ New Service</Btn>
          </div>
        }
      />
      <HomeServicesCatalogNav active="services" />

      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 9999, padding: "10px 18px",
          borderRadius: 10, background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
        }}>{toast.msg}</div>
      )}

      {/* Summary cards */}
      {s && (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
          <SummaryCard label="Total Services" value={s.total} />
          <SummaryCard label="Active" value={s.active} accent="var(--success-text, #22543d)" />
          <SummaryCard label="Inactive" value={s.inactive} accent="var(--warning-text, #744210)" />
          <SummaryCard label="Pricing Ready" value={s.pricing_ready} accent="var(--brand, #1a56db)" />
          <SummaryCard label="Missing Pricing" value={s.missing_pricing} accent="var(--danger-text, #c53030)" />
          <SummaryCard label="Provider Enabled" value={s.provider_enabled} />
        </div>
      )}
      {summary.loading && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} style={{ flex: "1 1 140px", height: 80, borderRadius:"var(--radius-lg)", background: "var(--border)" }} className="skeleton" />
          ))}
        </div>
      )}

      {/* By job type breakdown */}
      {s?.by_job_type && Object.keys(s.by_job_type).length > 0 && (
        <div style={{ marginBottom: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {Object.entries(s.by_job_type).map(([jt, count]) => (
            <button key={jt} onClick={() => setJobTypeFilter(jobTypeFilter === jt ? "" : jt)} style={{
              padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 500,
              border: `1px solid ${jobTypeFilter === jt ? "var(--brand, #1a56db)" : "var(--border)"}`,
              background: jobTypeFilter === jt ? "var(--brand-muted, rgba(26,86,219,.08))" : "var(--surface)",
              color: jobTypeFilter === jt ? "var(--brand, #1a56db)" : "var(--text-secondary)",
              cursor: "pointer",
            }}>
              {JOB_TYPES.find(j => j.value === jt)?.label ?? jt}: {count as number}
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card padding={16} style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <input
              placeholder="Search by service name…"
              value={q} onChange={e => { setQ(e.target.value); setPage(1); }}
              style={{
                width: "100%", padding: "8px 12px", borderRadius:"var(--radius-md)", fontSize: 13,
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--text-primary)", outline: "none", boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ minWidth: 180 }}>
            <Select label="" value={categoryFilter} onChange={v => { setCategoryFilter(v); setGroupFilter(""); setPage(1); }}
              placeholder="All Categories"
              options={[{ value: "", label: "All Categories" }, ...catOptions]} />
          </div>
          <div style={{ minWidth: 160 }}>
            <Select label="" value={groupFilter} onChange={v => { setGroupFilter(v); setPage(1); }}
              placeholder="All Groups"
              options={[{ value: "", label: "All Groups" }, ...groupOptions]} />
          </div>
          <div style={{ minWidth: 140 }}>
            <Select label="" value={isActiveFilter} onChange={v => { setIsActiveFilter(v); setPage(1); }}
              placeholder="Any Status"
              options={[{ value: "", label: "Any Status" }, { value: "true", label: "Active" }, { value: "false", label: "Inactive" }]} />
          </div>
          <Btn variant="ghost" size="sm" onClick={() => setShowAdvanced(p => !p)}>
            Advanced {showAdvanced ? "▲" : "▼"}
          </Btn>
          {(q || categoryFilter || groupFilter || jobTypeFilter || pricingModelFilter || isActiveFilter) && (
            <Btn variant="ghost" size="sm" onClick={() => { setQ(""); setCategoryFilter(""); setGroupFilter(""); setJobTypeFilter(""); setPricingModelFilter(""); setIsActiveFilter(""); }}>
              Clear
            </Btn>
          )}
        </div>

        {showAdvanced && (
          <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap", paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            <div style={{ minWidth: 160 }}>
              <Select label="Job Type" value={jobTypeFilter} onChange={setJobTypeFilter}
                options={[{ value: "", label: "All Job Types" }, ...JOB_TYPES]} />
            </div>
            <div style={{ minWidth: 180 }}>
              <Select label="Pricing Model" value={pricingModelFilter} onChange={setPricingModelFilter}
                options={[{ value: "", label: "All Models" }, ...PRICING_MODELS]} />
            </div>
          </div>
        )}
      </Card>

      {/* Active filter chips */}
      {(categoryFilter || groupFilter || jobTypeFilter || pricingModelFilter || isActiveFilter || q) && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {categoryFilter && <Badge variant="muted">Category: {catMap[categoryFilter] ?? categoryFilter}</Badge>}
          {groupFilter && <Badge variant="muted">Group: {groupMap[groupFilter] ?? groupFilter}</Badge>}
          {jobTypeFilter && <Badge variant="muted">Job Type: {JOB_TYPES.find(j => j.value === jobTypeFilter)?.label ?? jobTypeFilter}</Badge>}
          {pricingModelFilter && <Badge variant="muted">Model: {PRICING_MODELS.find(p => p.value === pricingModelFilter)?.label ?? pricingModelFilter}</Badge>}
          {isActiveFilter && <Badge variant="muted">Status: {isActiveFilter === "true" ? "Active" : "Inactive"}</Badge>}
          {q && <Badge variant="muted">Search: {q}</Badge>}
        </div>
      )}

      {services.error && (
        <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>
            <AlertCircle size={14} style={{ marginRight: 4 }} />
            {services.error}
          </p>
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={services.loading}
        onRowClick={row => setDetailSvc(row as unknown as MasterServiceEnriched)}
        emptyText="No master services found. Create your first service to populate the catalog."
      />
      <MasterServicesPagination page={page} pageSize={pageSize} total={services.data?.total ?? 0} onPage={setPage} />

      {/* Detail drawer */}
      <ServiceDetailDrawer svc={detailSvc} catMap={catMap} groupMap={groupMap} onClose={() => setDetailSvc(null)} />
      {detailSvc && (
        <div style={{ position: "fixed", inset: 0, zIndex: 1999, background: "rgba(0,0,0,.4)" }}
          onClick={() => setDetailSvc(null)} />
      )}

      {/* Edit Modal (existing services only -- job_type/pricing_model/prices/
          Brand/Type/workflow requirements kept here ONLY for backward
          compatibility with services created before migration 160; new
          services are created job-type-agnostic via the modal below and
          configure these per job type in their Job-Type Blueprint) */}
      <Modal open={modal === "edit"} onClose={() => setModal("none")}
        title={`Edit: ${editing?.name ?? ""}`}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14, maxHeight: "70vh", overflowY: "auto", paddingRight: 4 }}>
          {activeAction.error && (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{activeAction.error}</p>
            </div>
          )}

          <Input label="Service Name *" placeholder="e.g. AC Gas Refill" value={form.name}
            onChange={v => setF("name", v)} />

          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>Category (locked)</label>
            <p style={{ fontSize: 13, color: "var(--text-tertiary, var(--text-secondary))", margin: "6px 0 0" }}>{catMap[form.category_id] ?? form.category_id}</p>
          </div>

          <Select label="Service Group" value={form.service_group_id}
            onChange={v => setF("service_group_id", v)}
            options={[{ value: "", label: "No group (top-level)" }, ...groupOptions]}
            placeholder="No group (top-level)" />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Select label="Job Type *" value={form.job_type}
              onChange={applyJobTypeDefaults} options={JOB_TYPES} />
            <Select label="Pricing Model *" value={form.pricing_model}
              onChange={v => setF("pricing_model", v)} options={PRICING_MODELS} />
          </div>

          <div style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
              Pricing (base/min/max/visit fee) is tenant-owned only — each tenant sets its own price for this
              service in Tenant Setup. Admin no longer enters a price amount here.
            </p>
          </div>
          <Input label="Unit Label" placeholder="per visit" value={form.unit_label}
            onChange={v => setF("unit_label", v)} />

          <Input label="Description" placeholder="Optional description for this service"
            value={form.description} onChange={v => setF("description", v)} />

          <IconPicker label="Icon" context="service_icon" value={form.icon_url}
            onChange={v => setF("icon_url", v ?? "")} />

          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            <p style={{ margin: "0 0 6px", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: ".06em" }}>
              Requirements
            </p>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
              Brand, Type, Issue, Checklist, Schedule and Address requirements are configured per exact Job Type in
              the Job-Type Blueprint (Dimensions, Problems &amp; Questions, Checklist and Workflow tabs) — not here.
              These per-service flags are retained on existing records for history but are no longer authoritative
              once a Job-Type Blueprint exists for a job type.
            </p>
          </div>

          {editing && (
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
              <ReqToggle label="Active" value={form.is_active} onChange={v => setF("is_active", v)} />
            </div>
          )}

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={activeAction.loading} disabled={!canSave}
              onClick={() => { if (editing) editAction.execute({ id: editing.id, data: form }); }}>
              Save Changes
            </Btn>
          </div>
        </div>
      </Modal>

      {/* New Master Service -- canonical creation (migration 160), a focused
          form, not the full legacy modal. Navigates to the Catalog Workspace
          on success so the admin can add and configure job types. */}
      <MasterServiceCreateModal open={modal === "create-service"} onClose={() => setModal("none")}
        catOptions={catOptions} allGroups={allGroups.data?.groups ?? []}
        onCreated={() => {
          services.refetch(); summary.refetch(); setModal("none");
          notify("Master service created. Add job types in the Catalog Workspace.");
          router.push("/admin/catalog-workspace");
        }}/>

      {/* Archive confirm */}
      <Modal open={!!archiveId} onClose={() => setArchiveId(null)} title="Archive Master Service">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
          This will archive the master service. Providers who have enabled it will no longer see it.
          This action cannot be undone without re-activating.
        </p>
        {archiveAction.error && (
          <p style={{ fontSize: 13, color: "var(--danger-text)", marginBottom: 12 }}>{archiveAction.error}</p>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={() => setArchiveId(null)}>Cancel</Btn>
          <Btn variant="danger" size="sm" loading={archiveAction.loading}
            onClick={() => archiveId && archiveAction.execute(archiveId)}>
            Archive
          </Btn>
        </div>
      </Modal>
    </AdminLayout>
  );
}

function MasterServicesPagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 14 }}>
      <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
        {total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}` : "0 records"}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Btn size="sm" variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Btn>
        <Badge variant="muted">Page {page} of {pages}</Badge>
        <Btn size="sm" variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Btn>
      </div>
    </div>
  );
}
