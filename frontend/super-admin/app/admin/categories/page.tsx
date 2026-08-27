"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useState, useCallback } from "react";
import Link from "next/link";
import { AdminLayout, useAdminMenuRefresh } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn, Modal, Input, Select, Skeleton, SummaryCard, Pagination } from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import { ActionMenu } from "../../../components/shared/layout";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";
import {
  categoryRuntimeApi, catalogApi,
  type ServiceCategory, type EnterpriseCategory, type CategorySummaryData,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  Layers, Plus, ExternalLink, Search, Filter,
  X, Download, RefreshCw, CheckSquare, Square, ChevronDown, Eye,
  Settings2, Zap, DollarSign, Package, AlertCircle, CheckCircle,
  Clock, MinusCircle,
  FileText, TrendingUp, Users, ArrowUpDown, ChevronLeft, ChevronRight,
} from "lucide-react";

// ── Label Maps ────────────────────────────────────────────────────────────────

const VERTICAL_LABELS: Record<string, string> = {
  home_services: "Home Services",
  coaching: "Coaching / IELTS",
  real_estate: "Real Estate",
  restaurant: "Restaurant & Food",
  salon: "Salon / Beauty",
  automotive: "Automotive",
  professional_services: "Professional Services",
  pharmacy: "Pharmacy",
  hardware: "Hardware / Tools",
  repair_services: "Repair Services",
  cleaning_services: "Cleaning Services",
  laundry: "Laundry",
  marketplace_products: "Marketplace Products",
  other: "Other",
};

const FINANCE_LABELS: Record<string, string> = {
  security_deposit_plus_credit_wallet: "Credit Wallet + Seats",  // backend enum key, unchanged
  monthly_subscription: "Monthly Subscription",
  lead_credit: "Lead Credit",
  commission_wallet: "Commission + Wallet",
  product_order_commission: "Product Commission",
  free_listing: "Free Listing",
  hybrid: "Hybrid",
};

const FLOW_LABELS: Record<string, string> = {
  service_booking: "Service Booking",
  appointment_booking: "Appointment Booking",
  lead_capture: "Lead Capture",
  product_purchase: "Product Purchase",
  subscription_only: "Subscription Only",
  quote_request: "Quote Request",
  inspection_first: "Inspection First",
};

const READINESS_LABELS: Record<string, string> = {
  ready: "Ready",
  missing_services: "Missing Services",
  missing_pricing: "Missing Pricing",
  missing_package: "Missing Package",
  missing_flow_config: "Missing Flow Config",
  inactive: "Inactive",
  incomplete: "Incomplete",
};

const READINESS_COLOR: Record<string, string> = {
  ready: "success",
  missing_services: "warning",
  missing_pricing: "warning",
  missing_package: "muted",
  missing_flow_config: "warning",
  inactive: "muted",
  incomplete: "danger",
};

const VERTICAL_OPTIONS = Object.entries(VERTICAL_LABELS).map(([value, label]) => ({ value, label }));
const FINANCE_OPTIONS = Object.entries(FINANCE_LABELS).map(([value, label]) => ({ value, label }));
const FLOW_OPTIONS = Object.entries(FLOW_LABELS).map(([value, label]) => ({ value, label }));
const READINESS_OPTIONS = Object.entries(READINESS_LABELS).map(([value, label]) => ({ value, label }));

// ── Types ─────────────────────────────────────────────────────────────────────

// Ownership correction (migration 160): requires_location/requires_schedule/
// requires_brand/requires_service_option/requires_issue_type/pricing_supported
// removed -- these vary per Master Service and Job Type and must never be
// set on a Business Vertical (formerly "Service Category"). Editing an
// existing category's other fields no longer touches these deprecated
// columns, so their existing values are preserved untouched.
type FormState = {
  name: string; description: string; icon_url: string; image_url: string; display_order: number;
  vertical_type: string; finance_model: string; customer_flow_type: string; provider_business_model: string;
  tenant_selectable: boolean;
};

const BLANK: FormState = {
  name: "", description: "", icon_url: "", image_url: "", display_order: 0,
  vertical_type: "", finance_model: "", customer_flow_type: "", provider_business_model: "",
  tenant_selectable: true,
};

type Filters = {
  q: string; vertical_type: string; finance_model: string; customer_flow_type: string;
  status: string; readiness_status: string; tenant_selectable: string; pricing_supported: string;
};

const BLANK_FILTERS: Filters = {
  q: "", vertical_type: "", finance_model: "", customer_flow_type: "",
  status: "", readiness_status: "", tenant_selectable: "", pricing_supported: "",
};

const DEFAULT_CATEGORY_COLUMNS: ColumnDef[] = [
  { key: "name", label: "Category", visible: true, order: 0 },
  { key: "vertical_type", label: "Vertical", visible: true, order: 1 },
  { key: "customer_flow_type", label: "Customer Flow", visible: true, order: 2 },
  { key: "finance_model", label: "Finance Model", visible: true, order: 3 },
  { key: "readiness_status", label: "Readiness", visible: true, order: 4 },
  { key: "linked_setup", label: "Linked Setup", visible: true, order: 5 },
  { key: "visibility", label: "Visibility", visible: true, order: 6 },
  { key: "status", label: "Status", visible: true, order: 7 },
  { key: "actions", label: "Actions", visible: true, order: 8 },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function ReadinessBadge({ status }: { status: string }) {
  const label = READINESS_LABELS[status] ?? status;
  const variant = (READINESS_COLOR[status] ?? "muted") as "success" | "warning" | "muted" | "danger" | "info";
  return <Badge variant={variant} size="sm">{label}</Badge>;
}

function LinkedCountsBadges({ counts }: { counts: EnterpriseCategory["linked_counts"] }) {
  if (!counts) return <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>—</span>;
  const items = [
    { label: "Groups", value: counts.service_groups, color: "var(--accent)" },
    { label: "Services", value: counts.services, color: "var(--brand)" },
    { label: "Pricing", value: counts.pricing_rules, color: "var(--success)" },
    { label: "Brands", value: counts.brands, color: "var(--warning)" },
    { label: "Providers", value: counts.providers, color: "#0891b2" },
  ].filter(i => i.value > 0);

  if (!items.length) return <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>No data</span>;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {items.map(item => (
        <span key={item.label} style={{
          display: "inline-flex", gap: 3, alignItems: "center",
          fontSize: 10, padding: "2px 7px", borderRadius: 20, fontWeight: 700,
          background: `${item.color}12`, color: item.color,
        }}>
          {item.value} {item.label}
        </span>
      ))}
    </div>
  );
}

function AdvancedFiltersDrawer({
  open, filters, onChange, onClose, onClear,
}: {
  open: boolean;
  filters: Filters;
  onChange: (k: keyof Filters, v: string) => void;
  onClose: () => void;
  onClear: () => void;
}) {
  const sel = (style?: React.CSSProperties): React.CSSProperties => ({
    height: 34, borderRadius:"var(--radius-md)", fontSize: 13, border: "1px solid var(--border)",
    background: "var(--surface)", color: "var(--text-primary)",
    padding: "0 10px", outline: "none", width: "100%", ...style,
  });

  if (!open) return null;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 500, display: "flex", justifyContent: "flex-end",
    }}>
      <div onClick={onClose} style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.25)" }}/>
      <div style={{
        position: "relative", width: 380, background: "var(--surface)",
        boxShadow: "-4px 0 32px rgba(0,0,0,0.12)", display: "flex", flexDirection: "column",
        height: "100vh", overflowY: "auto",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "20px 24px", borderBottom: "1px solid var(--border)" }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>Advanced Filters</span>
          <Btn size="sm" variant="ghost" onClick={onClose}><X size={14}/></Btn>
        </div>
        <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 18, flex: 1 }}>

          {([
            ["Vertical Type", "vertical_type", VERTICAL_OPTIONS],
            ["Finance Model", "finance_model", FINANCE_OPTIONS],
            ["Customer Flow", "customer_flow_type", FLOW_OPTIONS],
            ["Status", "status", [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]],
            ["Runtime Readiness", "readiness_status", READINESS_OPTIONS],
          ] as [string, keyof Filters, { value: string; label: string }[]][]).map(([label, key, opts]) => (
            <div key={key}>
              <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)",
                textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
                {label}
              </label>
              <select value={filters[key]} onChange={e => onChange(key, e.target.value)} style={sel()}>
                <option value="">All</option>
                {opts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          ))}

          {([
            ["Tenant Selectable", "tenant_selectable"],
            ["Pricing Supported", "pricing_supported"],
          ] as [string, keyof Filters][]).map(([label, key]) => (
            <div key={key}>
              <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)",
                textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
                {label}
              </label>
              <select value={filters[key]} onChange={e => onChange(key, e.target.value)} style={sel()}>
                <option value="">Any</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
          ))}
        </div>
        <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border)", display: "flex", gap: 10 }}>
          <Btn variant="ghost" size="sm" onClick={onClear} style={{ flex: 1 }}>Clear All</Btn>
          <Btn variant="primary" size="sm" onClick={onClose} style={{ flex: 1 }}>Apply</Btn>
        </div>
      </div>
    </div>
  );
}

function FilterChips({ filters, onRemove }: { filters: Filters; onRemove: (k: keyof Filters) => void }) {
  const chips = [
    filters.vertical_type && { key: "vertical_type" as keyof Filters, label: `Vertical: ${VERTICAL_LABELS[filters.vertical_type] ?? filters.vertical_type}` },
    filters.finance_model && { key: "finance_model" as keyof Filters, label: `Finance: ${FINANCE_LABELS[filters.finance_model] ?? filters.finance_model}` },
    filters.customer_flow_type && { key: "customer_flow_type" as keyof Filters, label: `Flow: ${FLOW_LABELS[filters.customer_flow_type] ?? filters.customer_flow_type}` },
    filters.status && { key: "status" as keyof Filters, label: `Status: ${filters.status}` },
    filters.readiness_status && { key: "readiness_status" as keyof Filters, label: `Readiness: ${READINESS_LABELS[filters.readiness_status] ?? filters.readiness_status}` },
    filters.tenant_selectable && { key: "tenant_selectable" as keyof Filters, label: `Tenant Selectable: ${filters.tenant_selectable === "true" ? "Yes" : "No"}` },
    filters.pricing_supported && { key: "pricing_supported" as keyof Filters, label: `Pricing Supported: ${filters.pricing_supported === "true" ? "Yes" : "No"}` },
  ].filter(Boolean) as { key: keyof Filters; label: string }[];

  if (!chips.length) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
      <span style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 500 }}>Active filters:</span>
      {chips.map(chip => (
        <button key={chip.key}
          onClick={() => onRemove(chip.key)}
          style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            fontSize: 11, padding: "3px 10px", borderRadius: 20, fontWeight: 600,
            background: "rgba(37,99,235,0.1)", color: "var(--brand)",
            border: "1px solid rgba(37,99,235,0.25)", cursor: "pointer",
          }}>
          {chip.label} <X size={9}/>
        </button>
      ))}
    </div>
  );
}

// ── Category Form ─────────────────────────────────────────────────────────────

const PROVIDER_BIZ_OPTIONS = [
  { value: "service_provider", label: "Service Provider" },
  { value: "product_seller", label: "Product Seller" },
  { value: "marketplace_lister", label: "Marketplace Lister" },
  { value: "subscription_member", label: "Subscription Member" },
];

// ── New Business Vertical -- canonical creation (migration 160) ─────────────
// Uses the SAME CategoryForm/FormState as Edit (see below), so create and
// edit can never drift apart again. Bug fix: this used to be a separate,
// much shorter form (Name/Description/Display Order/3 checkboxes only) that
// never collected Vertical Type/Finance Model/Customer Flow Type/Provider
// Business Model/Icon/Image -- even though the backend's
// create_category_canonical already accepted finance_model/icon_url/
// image_url, and (after the fix accompanying this change) now also accepts
// vertical_type/customer_flow_type/provider_business_model. A vertical
// created via the old short form landed with all of those null even though
// Edit marks Vertical Type/Customer Flow Type as required -- every new
// vertical needed a second, easy-to-forget Edit pass before it actually
// worked. No Brand/Type/Schedule/Address/pricing fields here or in Edit --
// those vary per Master Service and Job Type and belong on the Job-Type
// Blueprint; the backend rejects them outright.
function BusinessVerticalCreateModal({ open, onClose, onCreated }: {
  open: boolean; onClose: () => void; onCreated: () => void;
}) {
  const [form, setForm] = useState<FormState>(BLANK);
  const createAction = useAction(catalogApi.createBusinessVertical);

  function setF<K extends keyof FormState>(k: K, v: FormState[K]) {
    setForm(p => ({ ...p, [k]: v }));
  }

  async function submit() {
    const result = await createAction.execute({
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      icon_url: form.icon_url || undefined,
      image_url: form.image_url || undefined,
      display_order: form.display_order || 0,
      vertical_type: form.vertical_type || undefined,
      finance_model: form.finance_model || undefined,
      customer_flow_type: form.customer_flow_type || undefined,
      provider_business_model: form.provider_business_model || undefined,
      tenant_selectable: form.tenant_selectable,
    });
    if (result) { setForm(BLANK); onCreated(); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Business Vertical" size="xl">
      <CategoryForm form={form} setF={setF} error={createAction.error}/>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 14 }}>
        <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" size="sm" disabled={!form.name.trim()} loading={createAction.loading} onClick={submit}>
          Create Business Vertical
        </Btn>
      </div>
    </Modal>
  );
}

function CategoryForm({
  form, setF, error,
}: {
  form: FormState;
  setF: <K extends keyof FormState>(k: K, v: FormState[K]) => void;
  error?: string | null;
}) {
  const inp: React.CSSProperties = {
    width: "100%", padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
    background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box",
    outline: "none",
  };

  const verticalHint: Record<string, string> = {
    home_services: "Recommended: Credit Wallet + Seats · Service Booking",
    coaching: "Recommended: Monthly Subscription · Appointment Booking",
    real_estate: "Recommended: Lead Credit · Lead Capture",
  };
  const hint = form.vertical_type ? verticalHint[form.vertical_type] : null;

  const sectionLabel: React.CSSProperties = {
    fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
    textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {error && (
        <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Basic */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <Input label="Name *" placeholder="Home Repairs" value={form.name} onChange={v => setF("name", v)}/>
        <Input label="Display Order" type="number" placeholder="0"
          value={String(form.display_order)} onChange={v => setF("display_order", Number(v) || 0)}/>
      </div>
      <div>
        <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
        <textarea value={form.description} onChange={e => setF("description", e.target.value)}
          placeholder="Short description shown to customers…" rows={2} style={{ ...inp, resize: "vertical", fontFamily: "inherit" }}/>
      </div>

      {/* Universal classification */}
      <div style={sectionLabel}>Behavior &amp; Finance</div>
      {hint && (
        <div style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", background: "rgba(37,99,235,0.06)", border: "1px solid rgba(37,99,235,0.2)", fontSize: 12, color: "var(--brand)" }}>
          {hint}
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12 }}>
        <Select label="Vertical Type *" value={form.vertical_type} onChange={v => setF("vertical_type", v)}
          options={VERTICAL_OPTIONS} placeholder="Select…"/>
        <Select label="Finance Model *" value={form.finance_model} onChange={v => setF("finance_model", v)}
          options={FINANCE_OPTIONS} placeholder="Select…"/>
        <Select label="Customer Flow Type *" value={form.customer_flow_type} onChange={v => setF("customer_flow_type", v)}
          options={FLOW_OPTIONS} placeholder="Select…"/>
        <Select label="Provider Business Model" value={form.provider_business_model} onChange={v => setF("provider_business_model", v)}
          options={PROVIDER_BIZ_OPTIONS} placeholder="Select…"/>
      </div>

      {/* Visibility + Appearance combined -- Brand/Type/Schedule/Address/
          pricing requirements removed (migration 160): those vary per
          Master Service and Job Type and are configured in each service's
          Job-Type Blueprint. */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 12, alignItems: "end" }}>
        <IconPicker label="Icon" context="category_icon" value={form.icon_url} onChange={v => setF("icon_url", v ?? "")}/>
        <IconPicker label="Image" context="category_icon" value={form.image_url} onChange={v => setF("image_url", v ?? "")}/>
        <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, cursor: "pointer", whiteSpace: "nowrap", paddingBottom: 8 }}>
          <input type="checkbox" checked={form.tenant_selectable}
            onChange={e => setF("tenant_selectable", e.target.checked)}
            style={{ width: 15, height: 15 }}/>
          Tenant Selectable
        </label>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CategoriesPage() {
  const refreshMenu = useAdminMenuRefresh();
  const [filters, setFilters] = useState<Filters>(BLANK_FILTERS);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState<"none" | "create" | "edit" | "create-vertical">("none");
  const [editing, setEditing] = useState<EnterpriseCategory | null>(null);
  const [form, setForm] = useState<FormState>(BLANK);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [hardDeleteId, setHardDeleteId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const [columns, setColumns] = useState<ColumnDef[]>(DEFAULT_CATEGORY_COLUMNS);
  const [sortBy, setSortBy] = useState("display_order");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const PAGE_SIZE = 25;

  // Summary cards
  const summary = useApi(useCallback(() => categoryRuntimeApi.summary(), []));

  // Categories list with all active filters
  const cats = useApi(useCallback(() => categoryRuntimeApi.listCategories({
    q: filters.q || undefined,
    vertical_type: filters.vertical_type || undefined,
    finance_model: filters.finance_model || undefined,
    customer_flow_type: filters.customer_flow_type || undefined,
    status: filters.status || undefined,
    readiness_status: filters.readiness_status || undefined,
    tenant_selectable: filters.tenant_selectable ? filters.tenant_selectable === "true" : undefined,
    pricing_supported: filters.pricing_supported ? filters.pricing_supported === "true" : undefined,
    page, page_size: PAGE_SIZE, sort_by: sortBy, sort_dir: sortDir,
  }), [filters, page, sortBy, sortDir]));

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  function setF<K extends keyof FormState>(k: K, v: FormState[K]) {
    setForm(p => ({ ...p, [k]: v }));
  }

  function setFilter(k: keyof Filters, v: string) {
    setFilters(p => ({ ...p, [k]: v }));
    setPage(1);
    setSelected(new Set());
  }

  function clearFilter(k: keyof Filters) {
    setFilters(p => ({ ...p, [k]: "" }));
    setPage(1);
  }

  function clearAll() {
    setFilters(BLANK_FILTERS);
    setPage(1);
    setActiveCard(null);
    setSelected(new Set());
  }

  function openCreate() { setModal("create-vertical"); }

  function openEdit(c: EnterpriseCategory) {
    setForm({
      name: c.name, description: c.description ?? "",
      icon_url: c.icon_url ?? "", image_url: c.image_url ?? "",
      display_order: c.display_order,
      vertical_type: c.vertical_type ?? "",
      finance_model: c.finance_model ?? "",
      customer_flow_type: c.customer_flow_type ?? "",
      provider_business_model: c.provider_business_model ?? "",
      tenant_selectable: c.tenant_selectable ?? true,
    });
    setEditing(c); setModal("edit");
  }

  function buildPayload(data: FormState) {
    return {
      name: data.name,
      description: data.description || undefined,
      icon_url: data.icon_url || undefined,
      image_url: data.image_url || undefined,
      display_order: data.display_order || 0,
      vertical_type: data.vertical_type || undefined,
      finance_model: data.finance_model || undefined,
      customer_flow_type: data.customer_flow_type || undefined,
      provider_business_model: data.provider_business_model || undefined,
      tenant_selectable: data.tenant_selectable,
    };
  }

  const editAction = useAction(useCallback(async ({ id, data }: { id: string; data: FormState }) => {
    await catalogApi.updateCategory(id, buildPayload(data));
    cats.refetch(); setModal("none"); notify("Category updated.");
  }, [cats]));

  const deleteAction = useAction(useCallback(async (id: string) => {
    await catalogApi.deleteCategory(id);
    cats.refetch(); summary.refetch(); setDeleteId(null); notify("Category deleted.");
  }, [cats, summary]));

  const hardDeleteAction = useAction(useCallback(async (id: string) => {
    await catalogApi.hardDeleteCategory(id);
    cats.refetch(); summary.refetch(); setHardDeleteId(null); notify("Category permanently deleted.");
  }, [cats, summary]));

  // FINAL-L5-04: also refresh AdminLayout's sidebar effective-menu, since
  // category activation can affect vertical/module visibility derived from it.
  const activateAction = useAction(useCallback(async (id: string) => {
    await categoryRuntimeApi.activateCategory(id);
    cats.refetch(); summary.refetch(); refreshMenu(); notify("Category activated.");
  }, [cats, summary, refreshMenu]));

  const deactivateAction = useAction(useCallback(async (id: string) => {
    await categoryRuntimeApi.deactivateCategory(id);
    cats.refetch(); summary.refetch(); refreshMenu(); notify("Category deactivated.");
  }, [cats, summary, refreshMenu]));

  const items: EnterpriseCategory[] = cats.data?.items ?? cats.data?.categories ?? [];
  const totalPages = cats.data?.pages ?? 1;
  const total = cats.data?.total ?? 0;
  const sum: CategorySummaryData | null = summary.data ?? null;

  const activeFiltersCount = Object.values(filters).filter(Boolean).length;

  // Card click: toggle filter
  function handleCardClick(key: string, filterKey: keyof Filters, value: string) {
    if (activeCard === key) {
      clearFilter(filterKey);
      setActiveCard(null);
    } else {
      setFilter(filterKey, value);
      setActiveCard(key);
    }
  }

  // Row selection
  function toggleRow(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }
  function toggleAll() {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map(c => c.category_id)));
  }
  const allSelected = items.length > 0 && selected.size === items.length;

  return (
    <AdminLayout activeNav="categories">
      <SectionHeader
        title="Home Services Categories"
        subtitle="Business categories and customer-flow policy. Service and job-type requirements are configured downstream in the blueprint workspace."
        icon={<Layers/>}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="ghost" onClick={() => { cats.refetch(); summary.refetch(); }}>
              <RefreshCw size={13}/> Refresh
            </Btn>
            <Btn size="sm" variant="primary" onClick={openCreate}>
              <Plus size={14}/> New Category
            </Btn>
          </div>
        }
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {toast && (
        <div style={{
          padding: "10px 16px", borderRadius: 10,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
        }}>
          {toast.ok ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      {/* Summary Cards */}
      {summary.loading ? (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {[...Array(6)].map((_, i) => <Skeleton key={i} height={88} style={{ flex: "1 1 140px", borderRadius:"var(--radius-lg)" }}/>)}
        </div>
      ) : sum ? (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <SummaryCard label="Total Categories" value={sum.total} icon={<Layers size={16}/>} accent="#6366f1"/>
          <SummaryCard label="Active" value={sum.active} icon={<CheckCircle size={16}/>} accent="var(--success)"
            active={activeCard === "active"}
            onClick={() => handleCardClick("active", "status", "active")}/>
          <SummaryCard label="Inactive" value={sum.inactive} icon={<MinusCircle size={16}/>} accent="#94a3b8"
            active={activeCard === "inactive"}
            onClick={() => handleCardClick("inactive", "status", "inactive")}/>
          <SummaryCard label="Customer Visible" value={sum.customer_visible} icon={<Eye size={16}/>} accent="#0891b2"/>
          <SummaryCard label="Tenant Selectable" value={sum.tenant_selectable} icon={<Users size={16}/>} accent="var(--accent)"/>
          <SummaryCard label="Runtime Ready" value={sum.runtime_ready} icon={<Zap size={16}/>} accent="var(--success)"
            active={activeCard === "ready"}
            onClick={() => handleCardClick("ready", "readiness_status", "ready")}/>
          <SummaryCard label="Missing Setup" value={sum.missing_required_setup} icon={<AlertCircle size={16}/>} accent="var(--danger)"
            active={activeCard === "missing"}
            onClick={() => handleCardClick("missing", "readiness_status", "missing_flow_config")}/>
          <SummaryCard label="With Services" value={sum.with_services} icon={<TrendingUp size={16}/>} accent="var(--warning)"/>
        </div>
      ) : null}

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 240px" }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)",
            color: "var(--text-tertiary)", pointerEvents: "none" }}/>
          <input value={filters.q} onChange={e => setFilter("q", e.target.value)}
            placeholder="Search categories, slug…"
            style={{ width: "100%", paddingLeft: 32, paddingRight: 10, height: 34, borderRadius:"var(--radius-md)", fontSize: 13,
              border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
              outline: "none", boxSizing: "border-box" }}/>
        </div>

        {/* Quick filters */}
        <select value={filters.vertical_type} onChange={e => setFilter("vertical_type", e.target.value)}
          style={{ height: 34, borderRadius:"var(--radius-md)", fontSize: 13, border: "1px solid var(--border)",
            background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", outline: "none" }}>
          <option value="">All Verticals</option>
          {VERTICAL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>

        <select value={filters.status} onChange={e => setFilter("status", e.target.value)}
          style={{ height: 34, borderRadius:"var(--radius-md)", fontSize: 13, border: "1px solid var(--border)",
            background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", outline: "none" }}>
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <select aria-label="Sort categories" value={`${sortBy}:${sortDir}`} onChange={e => {
          const [field, direction] = e.target.value.split(":"); setSortBy(field); setSortDir(direction as "asc" | "desc"); setPage(1);
        }} style={{ height: 34, borderRadius:"var(--radius-md)", fontSize: 13, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px" }}>
          <option value="display_order:asc">Configured order</option><option value="name:asc">Name A–Z</option><option value="name:desc">Name Z–A</option><option value="updated_at:desc">Recently updated</option>
        </select>

        <Btn size="sm" variant={drawerOpen || activeFiltersCount > 2 ? "secondary" : "ghost"}
          onClick={() => setDrawerOpen(true)}>
          <Filter size={13}/>
          Advanced Filters
          {activeFiltersCount > 0 && (
            <span style={{ marginLeft: 4, background: "var(--brand-primary)", color: "#fff",
              borderRadius: 10, fontSize: 10, padding: "1px 6px", fontWeight: 700 }}>
              {activeFiltersCount}
            </span>
          )}
        </Btn>

        {activeFiltersCount > 0 && (
          <Btn size="sm" variant="ghost" onClick={clearAll}>
            <X size={12}/> Clear All
          </Btn>
        )}

        <span style={{ fontSize: 12, color: "var(--text-tertiary)", whiteSpace: "nowrap", marginLeft: "auto" }}>
          {total} categor{total !== 1 ? "ies" : "y"}
        </span>
      </div>

      {/* Active filter chips */}
      <FilterChips filters={filters} onRemove={clearFilter}/>

      <OperationsDirectoryControls
        resourceKey="admin_categories"
        filters={Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ""))}
        sort={{ sort_by: sortBy, sort_direction: sortDir }} columns={columns} onColumnsChange={setColumns}
        onApplyView={(nextFilters, nextSort) => {
          setFilters({ ...BLANK_FILTERS, ...nextFilters } as Filters);
          if (typeof nextSort.sort_by === "string") setSortBy(nextSort.sort_by);
          if (nextSort.sort_direction === "asc" || nextSort.sort_direction === "desc") setSortDir(nextSort.sort_direction);
          setPage(1);
        }}
      />

      <HomeServicesCatalogNav active="categories" />

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 16px",
          borderRadius: 10, background: "rgba(37,99,235,0.06)", border: "1px solid rgba(37,99,235,0.2)" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--brand)" }}>{selected.size} selected</span>
          <div style={{ height: 16, width: 1, background: "rgba(37,99,235,0.3)" }}/>
          <Btn size="xs" variant="ghost" onClick={() => {
            selected.forEach(id => activateAction.execute(id));
            setSelected(new Set());
          }}>Activate</Btn>
          <Btn size="xs" variant="ghost" onClick={() => {
            selected.forEach(id => deactivateAction.execute(id));
            setSelected(new Set());
          }}>Deactivate</Btn>
          <Btn size="xs" variant="ghost" onClick={() => setSelected(new Set())}>
            <X size={11}/> Deselect
          </Btn>
        </div>
      )}

      {/* Table */}
      <Card padding={0}>
        {cats.loading ? (
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={60} style={{ borderRadius:"var(--radius-md)" }}/>)}
          </div>
        ) : cats.error ? (
          <div style={{ padding: 48, textAlign: "center" }}>
            <AlertCircle size={32} style={{ color: "var(--danger-text)", margin: "0 auto 12px", display: "block" }}/>
            <p style={{ fontSize: 14, color: "var(--danger-text)", margin: "0 0 16px", fontWeight: 600 }}>
              Could not load service categories.
            </p>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{cats.error}</p>
            <Btn size="sm" variant="secondary" onClick={() => cats.refetch()}>Retry</Btn>
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center" }}>
            <Layers size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px", display: "block" }}/>
            {activeFiltersCount > 0 ? (
              <>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 12px" }}>
                  No categories match these filters.
                </p>
                <Btn size="sm" variant="secondary" onClick={clearAll}>Clear Filters</Btn>
              </>
            ) : (
              <>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 12px" }}>
                  No service categories yet. Create the first one.
                </p>
                <Btn size="sm" variant="primary" onClick={openCreate}><Plus size={13}/> New Business Vertical</Btn>
              </>
            )}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <style>{columns.filter(column => !column.visible).map(column => `.catalog-categories-table .cat-col-${column.key}{display:none}`).join("\n")}</style>
            <TableSurface className="catalog-categories-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 14px", width: 32 }}>
                    <button onClick={toggleAll} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
                      {allSelected ? <CheckSquare size={14}/> : <Square size={14}/>}
                    </button>
                  </th>
                  {[["name","Category"], ["vertical_type","Vertical"], ["customer_flow_type","Customer Flow"], ["finance_model","Finance Model"], ["readiness_status","Readiness"], ["linked_setup","Linked Setup"], ["visibility","Visibility"], ["status","Status"], ["actions","Actions"]].map(([key, h]) => (
                    <th key={key} className={`cat-col-${key}`} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 700,
                      color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em",
                      whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((cat, i) => (
                  <tr key={cat.category_id}
                    style={{ borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none",
                      background: selected.has(cat.category_id) ? "rgba(37,99,235,0.03)" : undefined }}>

                    {/* Checkbox */}
                    <td style={{ padding: "12px 14px" }}>
                      <button onClick={() => toggleRow(cat.category_id)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
                        {selected.has(cat.category_id) ? <CheckSquare size={14} style={{ color: "var(--brand)" }}/> : <Square size={14}/>}
                      </button>
                    </td>

                    {/* Category */}
                    <td className="cat-col-name" style={{ padding: "12px 14px", minWidth: 180 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        {cat.icon_url ? (
                          <img src={cat.icon_url} alt="" width={32} height={32}
                            style={{ borderRadius:"var(--radius-md)", objectFit: "cover", flexShrink: 0 }}/>
                        ) : (
                          <div style={{ width: 32, height: 32, borderRadius:"var(--radius-md)", background: "var(--brand-light)",
                            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                            <Layers size={14} style={{ color: "var(--brand)" }}/>
                          </div>
                        )}
                        <div>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{cat.name}</p>
                          <span style={{ fontSize: 10, fontFamily: "monospace", color: "var(--text-tertiary)",
                            background: "var(--surface-sunken)", padding: "1px 5px", borderRadius: 4,
                            border: "1px solid var(--border)" }}>{cat.slug}</span>
                        </div>
                      </div>
                    </td>

                    {/* Vertical */}
                    <td className="cat-col-vertical_type" style={{ padding: "12px 14px" }}>
                      {cat.vertical_type
                        ? <Badge variant="info" size="sm">{VERTICAL_LABELS[cat.vertical_type] ?? cat.vertical_type}</Badge>
                        : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                    </td>

                    {/* Customer Flow */}
                    <td className="cat-col-customer_flow_type" style={{ padding: "12px 14px" }}>
                      {cat.customer_flow_type
                        ? <Badge variant="muted" size="sm">{FLOW_LABELS[cat.customer_flow_type] ?? cat.customer_flow_type}</Badge>
                        : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                    </td>

                    {/* Finance Model */}
                    <td className="cat-col-finance_model" style={{ padding: "12px 14px", maxWidth: 160 }}>
                      {cat.finance_model
                        ? <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>
                            {FINANCE_LABELS[cat.finance_model] ?? cat.finance_model}
                          </span>
                        : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                    </td>

                    {/* Readiness */}
                    <td className="cat-col-readiness_status" style={{ padding: "12px 14px" }}>
                      <ReadinessBadge status={cat.readiness_status ?? "inactive"}/>
                    </td>

                    {/* Linked Setup */}
                    <td className="cat-col-linked_setup" style={{ padding: "12px 14px", minWidth: 160 }}>
                      <LinkedCountsBadges counts={cat.linked_counts}/>
                    </td>

                    {/* Visibility */}
                    <td className="cat-col-visibility" style={{ padding: "12px 14px" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        {cat.is_customer_visible
                          ? <span style={{ fontSize: 10, fontWeight: 600, color: "var(--success)" }}>Customer Visible</span>
                          : <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>Customer Hidden</span>}
                        {cat.tenant_selectable
                          ? <span style={{ fontSize: 10, fontWeight: 600, color: "var(--brand)" }}>Tenant Selectable</span>
                          : <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>Not Selectable</span>}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="cat-col-status" style={{ padding: "12px 14px" }}>
                      <Badge variant={cat.is_active ? "success" : "muted"} size="sm">
                        {cat.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>

                    {/* Actions */}
                    <td className="cat-col-actions" style={{ padding: "12px 14px" }}>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <Link href={`/admin/categories/${cat.category_id}`}>
                          <Btn size="xs" variant="ghost"><Eye size={11}/> View</Btn>
                        </Link>
                        <ActionMenu
                          size="xs"
                          items={[
                            { label: "View Details", onClick: () => window.location.assign(`/admin/categories/${cat.category_id}`) },
                            { label: "Edit Category", onClick: () => openEdit(cat) },
                            { label: "Runtime Preview", onClick: () => window.location.assign(`/admin/categories/${cat.category_id}`) },
                            cat.is_active
                              ? { label: "Deactivate", onClick: () => deactivateAction.execute(cat.category_id), variant: "danger", divider: true }
                              : { label: "Activate", onClick: () => activateAction.execute(cat.category_id), divider: true },
                            { label: "Delete", onClick: () => setDeleteId(cat.category_id), variant: "danger" },
                            cat.linked_counts.services === 0 && { label: "Delete Permanently", onClick: () => setHardDeleteId(cat.category_id), variant: "danger" },
                          ]}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSurface>
          </div>
        )}

        {/* Pagination */}
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} pageCount={totalPages} onPage={setPage} itemLabel="categories" />
      </Card>

      </div>{/* end flex column */}

      {/* Edit Modal (existing verticals only -- deprecated Brand/Type/Schedule/
          Address/pricing fields removed; editing other fields never touches
          them, so their existing values are preserved untouched) */}
      <Modal open={modal === "edit"} onClose={() => setModal("none")} title={`Edit: ${editing?.name}`} size="xl">
        <CategoryForm form={form} setF={setF} error={editAction.error}/>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 16 }}>
          <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
          <Btn variant="primary" size="sm"
            disabled={!form.name.trim()}
            loading={editAction.loading}
            onClick={() => { if (editing) editAction.execute({ id: editing.category_id, data: form }); }}>
            Save Changes
          </Btn>
        </div>
      </Modal>

      {/* New Business Vertical -- canonical creation (migration 160), now
          the same CategoryForm as Edit (see BusinessVerticalCreateModal). */}
      <BusinessVerticalCreateModal open={modal === "create-vertical"} onClose={() => setModal("none")}
        onCreated={() => { cats.refetch(); summary.refetch(); setModal("none"); notify("Business Vertical created."); }}/>

      {/* Delete Confirm */}
      <Modal open={deleteId !== null} onClose={() => setDeleteId(null)} title="Delete Category">
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px" }}>
          This will deactivate the category. Services linked to it will lose their grouping.
          Are you sure?
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={() => setDeleteId(null)}>Cancel</Btn>
          <Btn variant="danger" size="sm" loading={deleteAction.loading}
            onClick={() => deleteId && deleteAction.execute(deleteId)}>
            Delete
          </Btn>
        </div>
      </Modal>

      {/* Hard Delete Confirm -- only offered when linked_counts.services === 0
          (same guard the backend itself enforces server-side; this is a
          real, permanent row delete, not the deactivate-only "Delete" above,
          previously built on the backend but never exposed in any UI). */}
      <Modal open={hardDeleteId !== null} onClose={() => setHardDeleteId(null)} title="Delete Category Permanently">
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px" }}>
          This category has no master services linked to it, so it can be permanently removed. This cannot be undone.
        </p>
        {hardDeleteAction.error && (
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: "0 0 12px" }}>{hardDeleteAction.error}</p>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={() => setHardDeleteId(null)}>Cancel</Btn>
          <Btn variant="danger" size="sm" loading={hardDeleteAction.loading}
            onClick={() => hardDeleteId && hardDeleteAction.execute(hardDeleteId)}>
            Delete Permanently
          </Btn>
        </div>
      </Modal>

      {/* Advanced Filters Drawer */}
      <AdvancedFiltersDrawer
        open={drawerOpen}
        filters={filters}
        onChange={(k, v) => setFilter(k, v)}
        onClose={() => setDrawerOpen(false)}
        onClear={clearAll}
      />
    </AdminLayout>
  );
}
