"use client";
import React, { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { AdminLayout, useAdminMenuRefresh } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn, Modal, Input, Select, Skeleton } from "../../../components/shared/ui";
import {
  categoryRuntimeApi, catalogApi,
  type ServiceCategory, type EnterpriseCategory, type CategorySummaryData,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  Layers, Plus, Pencil, ExternalLink, Power, PowerOff, Search, Filter,
  X, Download, RefreshCw, CheckSquare, Square, ChevronDown, Eye,
  Settings2, Zap, DollarSign, Package, AlertCircle, CheckCircle,
  Clock, MinusCircle, XCircle, MoreVertical, MapPin, Calendar,
  Tag, FileText, TrendingUp, Users, ArrowUpDown, ChevronLeft, ChevronRight,
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
  security_deposit_plus_credit_wallet: "Deposit + Credit Wallet",
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

// ── Sub-components ────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, icon, color, active, onClick,
}: {
  label: string; value: number | string; icon: React.ReactNode;
  color?: string; active?: boolean; onClick?: () => void;
}) {
  const accent = color ?? "var(--brand-primary)";
  return (
    <div onClick={onClick}
      style={{
        flex: "1 1 140px", padding: "16px 20px", borderRadius:"var(--radius-lg)",
        background: active ? `${accent}12` : "var(--surface)",
        border: `1px solid ${active ? accent : "var(--border)"}`,
        cursor: onClick ? "pointer" : "default",
        transition: "border-color 0.15s, background 0.15s",
        display: "flex", flexDirection: "column", gap: 6,
      }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: accent }}>{icon}</div>
      <p style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", margin: 0, lineHeight: 1 }}>{value}</p>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, fontWeight: 500 }}>{label}</p>
    </div>
  );
}

function ReadinessBadge({ status }: { status: string }) {
  const label = READINESS_LABELS[status] ?? status;
  const variant = (READINESS_COLOR[status] ?? "muted") as "success" | "warning" | "muted" | "danger" | "info";
  return <Badge variant={variant} size="sm">{label}</Badge>;
}

function RequirementsChips({ cat }: { cat: ServiceCategory }) {
  const chips = [
    cat.requires_location && { key: "location", label: "Location", icon: <MapPin size={9}/> },
    cat.requires_schedule && { key: "schedule", label: "Schedule", icon: <Calendar size={9}/> },
    cat.requires_brand    && { key: "brand",    label: "Brand",    icon: <Tag size={9}/> },
    cat.requires_service_option && { key: "option", label: "Option", icon: <Settings2 size={9}/> },
    cat.requires_issue_type && { key: "issue", label: "Issue", icon: <AlertCircle size={9}/> },
  ].filter(Boolean) as { key: string; label: string; icon: React.ReactNode }[];

  if (!chips.length) return <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>None</span>;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
      {chips.map(chip => (
        <span key={chip.key} style={{
          display: "inline-flex", alignItems: "center", gap: 3,
          fontSize: 10, padding: "2px 6px", borderRadius: 20, fontWeight: 600,
          background: "rgba(37,99,235,0.08)", color: "var(--brand)",
        }}>
          {chip.icon}{chip.label}
        </span>
      ))}
    </div>
  );
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

function ActionMenu({ cat, onEdit, onActivate, onDeactivate, onDelete }: {
  cat: EnterpriseCategory;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const menuItem = (label: string, icon: React.ReactNode, onClick: () => void, danger = false) => (
    <button key={label}
      onClick={() => { onClick(); setOpen(false); }}
      style={{
        display: "flex", alignItems: "center", gap: 8, width: "100%",
        padding: "9px 14px", background: "none", border: "none",
        cursor: "pointer", fontSize: 13, textAlign: "left",
        color: danger ? "var(--danger-text)" : "var(--text-primary)",
        borderRadius: 6,
      }}
      onMouseEnter={e => (e.currentTarget.style.background = danger ? "var(--danger-bg)" : "var(--surface-sunken)")}
      onMouseLeave={e => (e.currentTarget.style.background = "none")}>
      <span style={{ color: danger ? "var(--danger-text)" : "var(--text-tertiary)" }}>{icon}</span>
      {label}
    </button>
  );

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <Btn size="xs" variant="ghost" onClick={() => setOpen(o => !o)}>
        <MoreVertical size={13}/>
      </Btn>
      {open && (
        <div style={{
          position: "fixed", zIndex: 9999,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 10, boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
          minWidth: 200, padding: "6px",
          top: ref.current ? ref.current.getBoundingClientRect().bottom + 4 : 0,
          right: typeof window !== "undefined" ? window.innerWidth - (ref.current?.getBoundingClientRect().right ?? 0) : 0,
        }}>
          {menuItem("View Details", <Eye size={13}/>, () => window.location.assign(`/admin/categories/${cat.category_id}`))}
          {menuItem("Edit Category", <Pencil size={13}/>, onEdit)}
          {menuItem("Runtime Preview", <Zap size={13}/>, () => window.location.assign(`/admin/categories/${cat.category_id}`))}
          <div style={{ height: 1, background: "var(--border)", margin: "4px 0" }}/>
          {cat.is_active
            ? menuItem("Deactivate", <PowerOff size={13}/>, onDeactivate, true)
            : menuItem("Activate", <Power size={13}/>, onActivate)
          }
          {menuItem("Delete", <XCircle size={13}/>, onDelete, true)}
        </div>
      )}
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
// A focused, standalone form (not the full legacy modal): Name, Description,
// Display Order, Status, Tenant Selectable, Customer Visible. No Brand/Type/
// Schedule/Address/pricing fields -- those vary per Master Service and Job
// Type and belong on the Job-Type Blueprint. The backend rejects them
// outright if this form (or anything else) tries to send them.
function BusinessVerticalCreateModal({ open, onClose, onCreated }: {
  open: boolean; onClose: () => void; onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [displayOrder, setDisplayOrder] = useState(0);
  const [tenantSelectable, setTenantSelectable] = useState(true);
  const [customerVisible, setCustomerVisible] = useState(true);
  const [registrationAvailable, setRegistrationAvailable] = useState(true);
  const createAction = useAction(catalogApi.createBusinessVertical);

  function reset() {
    setName(""); setDescription(""); setDisplayOrder(0);
    setTenantSelectable(true); setCustomerVisible(true); setRegistrationAvailable(true);
  }

  async function submit() {
    const result = await createAction.execute({
      name: name.trim(), description: description.trim() || undefined,
      display_order: displayOrder, tenant_selectable: tenantSelectable,
      is_customer_visible: customerVisible, registration_available: registrationAvailable,
    });
    if (result) { reset(); onCreated(); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Business Vertical">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {createAction.error && (
          <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
            <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{createAction.error}</p>
          </div>
        )}
        <Input label="Name *" placeholder="Home Services" value={name} onChange={setName}/>
        <div>
          <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)}
            placeholder="Short description shown across the platform…" rows={2}
            style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
              background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box",
              outline: "none", resize: "vertical", fontFamily: "inherit" }}/>
        </div>
        <Input label="Display Order" type="number" value={String(displayOrder)}
          onChange={v => setDisplayOrder(parseInt(v, 10) || 0)}/>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={registrationAvailable} onChange={e => setRegistrationAvailable(e.target.checked)} style={{ width: 15, height: 15 }}/>
            Registration Available
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={tenantSelectable} onChange={e => setTenantSelectable(e.target.checked)} style={{ width: 15, height: 15 }}/>
            Tenant Selectable
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={customerVisible} onChange={e => setCustomerVisible(e.target.checked)} style={{ width: 15, height: 15 }}/>
            Customer Visible
          </label>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Brand, Type, Schedule, Address, and pricing requirements vary by service and job type —
          configure them per service after creation, in its Job-Type Blueprint.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" disabled={!name.trim()} loading={createAction.loading} onClick={submit}>
            Create Business Vertical
          </Btn>
        </div>
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
    home_services: "Recommended: Deposit + Credit Wallet · Service Booking",
    coaching: "Recommended: Monthly Subscription · Appointment Booking",
    real_estate: "Recommended: Lead Credit · Lead Capture",
  };
  const hint = form.vertical_type ? verticalHint[form.vertical_type] : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxHeight: "75vh", overflowY: "auto", paddingRight: 4 }}>
      {error && (
        <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Basic */}
      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
        Basic Details
      </div>
      <Input label="Name *" placeholder="Home Repairs" value={form.name} onChange={v => setF("name", v)}/>
      <div>
        <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
        <textarea value={form.description} onChange={e => setF("description", e.target.value)}
          placeholder="Short description shown to customers…" rows={2} style={{ ...inp, resize: "vertical", fontFamily: "inherit" }}/>
      </div>

      {/* Universal classification */}
      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
        Behavior &amp; Finance
      </div>
      {hint && (
        <div style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", background: "rgba(37,99,235,0.06)", border: "1px solid rgba(37,99,235,0.2)", fontSize: 12, color: "var(--brand)" }}>
          {hint}
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Select label="Vertical Type *" value={form.vertical_type} onChange={v => setF("vertical_type", v)}
          options={VERTICAL_OPTIONS} placeholder="Select vertical…"/>
        <Select label="Finance Model *" value={form.finance_model} onChange={v => setF("finance_model", v)}
          options={FINANCE_OPTIONS} placeholder="Select model…"/>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Select label="Customer Flow Type *" value={form.customer_flow_type} onChange={v => setF("customer_flow_type", v)}
          options={FLOW_OPTIONS} placeholder="Select flow…"/>
        <Select label="Provider Business Model" value={form.provider_business_model} onChange={v => setF("provider_business_model", v)}
          options={PROVIDER_BIZ_OPTIONS} placeholder="Select…"/>
      </div>

      {/* Visibility -- Brand/Type/Schedule/Address/pricing requirements
          removed (migration 160): those vary per Master Service and Job
          Type and are configured in each service's Job-Type Blueprint. */}
      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
        Visibility
      </div>
      <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, cursor: "pointer" }}>
        <input type="checkbox" checked={form.tenant_selectable}
          onChange={e => setF("tenant_selectable", e.target.checked)}
          style={{ width: 15, height: 15 }}/>
        Tenant Selectable
      </label>

      {/* Appearance */}
      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
        Appearance
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Input label="Icon URL" placeholder="https://…" value={form.icon_url} onChange={v => setF("icon_url", v)}/>
        <Input label="Image URL" placeholder="https://…" value={form.image_url} onChange={v => setF("image_url", v)}/>
      </div>
      <Input label="Display Order" type="number" placeholder="0"
        value={String(form.display_order)} onChange={v => setF("display_order", Number(v) || 0)}/>
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
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [activeCard, setActiveCard] = useState<string | null>(null);

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
    page, page_size: PAGE_SIZE,
  }), [filters, page]));

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

  const exportAction = useAction(useCallback(async () => {
    const resp = await categoryRuntimeApi.exportCategories({
      status: filters.status || undefined,
      vertical_type: filters.vertical_type || undefined,
    });
    if (!resp.ok) { notify("Export failed", false); return; }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "service_categories.csv"; a.click();
    URL.revokeObjectURL(url);
    notify("Export downloaded.");
  }, [filters]));

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
        title="Service Categories"
        subtitle="Master platform categories that define vertical behavior, finance model, onboarding, pricing, and customer flow."
        icon={<Layers/>}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="ghost" onClick={() => { cats.refetch(); summary.refetch(); }}>
              <RefreshCw size={13}/> Refresh
            </Btn>
            <Btn size="sm" variant="ghost" loading={exportAction.loading} onClick={() => exportAction.execute()}>
              <Download size={13}/> Export
            </Btn>
            <Btn size="sm" variant="primary" onClick={openCreate}>
              <Plus size={14}/> New Business Vertical
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
          <SummaryCard label="Total Categories" value={sum.total} icon={<Layers size={16}/>} color="#6366f1"/>
          <SummaryCard label="Active" value={sum.active} icon={<CheckCircle size={16}/>} color="var(--success)"
            active={activeCard === "active"}
            onClick={() => handleCardClick("active", "status", "active")}/>
          <SummaryCard label="Inactive" value={sum.inactive} icon={<MinusCircle size={16}/>} color="#94a3b8"
            active={activeCard === "inactive"}
            onClick={() => handleCardClick("inactive", "status", "inactive")}/>
          <SummaryCard label="Customer Visible" value={sum.customer_visible} icon={<Eye size={16}/>} color="#0891b2"/>
          <SummaryCard label="Tenant Selectable" value={sum.tenant_selectable} icon={<Users size={16}/>} color="var(--accent)"/>
          <SummaryCard label="Runtime Ready" value={sum.runtime_ready} icon={<Zap size={16}/>} color="var(--success)"
            active={activeCard === "ready"}
            onClick={() => handleCardClick("ready", "readiness_status", "ready")}/>
          <SummaryCard label="Missing Setup" value={sum.missing_required_setup} icon={<AlertCircle size={16}/>} color="var(--danger)"
            active={activeCard === "missing"}
            onClick={() => handleCardClick("missing", "readiness_status", "missing_flow_config")}/>
          <SummaryCard label="With Services" value={sum.with_services} icon={<TrendingUp size={16}/>} color="var(--warning)"/>
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
          <Btn size="xs" variant="ghost" onClick={() => exportAction.execute()}>
            <Download size={11}/> Export Selected
          </Btn>
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
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 14px", width: 32 }}>
                    <button onClick={toggleAll} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
                      {allSelected ? <CheckSquare size={14}/> : <Square size={14}/>}
                    </button>
                  </th>
                  {["Category", "Vertical", "Customer Flow", "Finance Model", "Requirements", "Readiness", "Linked Setup", "Visibility", "Status", "Actions"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 700,
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
                    <td style={{ padding: "12px 14px", minWidth: 180 }}>
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
                    <td style={{ padding: "12px 14px" }}>
                      {cat.vertical_type
                        ? <Badge variant="info" size="sm">{VERTICAL_LABELS[cat.vertical_type] ?? cat.vertical_type}</Badge>
                        : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                    </td>

                    {/* Customer Flow */}
                    <td style={{ padding: "12px 14px" }}>
                      {cat.customer_flow_type
                        ? <Badge variant="muted" size="sm">{FLOW_LABELS[cat.customer_flow_type] ?? cat.customer_flow_type}</Badge>
                        : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                    </td>

                    {/* Finance Model */}
                    <td style={{ padding: "12px 14px", maxWidth: 160 }}>
                      {cat.finance_model
                        ? <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>
                            {FINANCE_LABELS[cat.finance_model] ?? cat.finance_model}
                          </span>
                        : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                    </td>

                    {/* Requirements */}
                    <td style={{ padding: "12px 14px", minWidth: 140 }}>
                      <RequirementsChips cat={cat}/>
                    </td>

                    {/* Readiness */}
                    <td style={{ padding: "12px 14px" }}>
                      <ReadinessBadge status={cat.readiness_status ?? "inactive"}/>
                    </td>

                    {/* Linked Setup */}
                    <td style={{ padding: "12px 14px", minWidth: 160 }}>
                      <LinkedCountsBadges counts={cat.linked_counts}/>
                    </td>

                    {/* Visibility */}
                    <td style={{ padding: "12px 14px" }}>
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
                    <td style={{ padding: "12px 14px" }}>
                      <Badge variant={cat.is_active ? "success" : "muted"} size="sm">
                        {cat.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: "12px 14px" }}>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <Link href={`/admin/categories/${cat.category_id}`}>
                          <Btn size="xs" variant="ghost"><Eye size={11}/> View</Btn>
                        </Link>
                        <ActionMenu
                          cat={cat}
                          onEdit={() => openEdit(cat)}
                          onActivate={() => activateAction.execute(cat.category_id)}
                          onDeactivate={() => deactivateAction.execute(cat.category_id)}
                          onDelete={() => setDeleteId(cat.category_id)}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Page {page} of {totalPages} · {total} total
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <Btn size="xs" variant="ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft size={12}/>
              </Btn>
              <Btn size="xs" variant="ghost" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                <ChevronRight size={12}/>
              </Btn>
            </div>
          </div>
        )}
      </Card>

      </div>{/* end flex column */}

      {/* Edit Modal (existing verticals only -- deprecated Brand/Type/Schedule/
          Address/pricing fields removed; editing other fields never touches
          them, so their existing values are preserved untouched) */}
      <Modal open={modal === "edit"} onClose={() => setModal("none")} title={`Edit: ${editing?.name}`}>
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

      {/* New Business Vertical -- canonical creation (migration 160), a
          focused form, not the full legacy modal. */}
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
