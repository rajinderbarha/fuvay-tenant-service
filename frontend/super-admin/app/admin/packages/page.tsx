"use client";
import React, { useCallback, useState, useEffect, useRef } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, SectionHeader, Badge, Btn, DataTable, Modal, Input, Select, Skeleton,
} from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  packageApi, catalogApi,
  type AdminPackage, type PackageFeature, type PackageLimit, type PackageSummary,
} from "../../../lib/api";
import {
  Package, Plus, Pencil, Trash2, Copy, CheckCircle2, XCircle,
  ChevronUp, ChevronDown, Star, Eye, BarChart3,
} from "lucide-react";

// ── helpers ──────────────────────────────────────────────────────────────────
const fmt = (n: number | string) => `₹${Number(n).toLocaleString("en-IN")}`;

const PACKAGE_TYPE_TABS = [
  { value: "onboarding_package",    label: "Onboarding Package",    color: "#7c3aed",
    hint: "One-time provider onboarding. May include security deposit + starting credits.",
    showDeposit: true,  showCredits: true,  showBilling: false, showLeads: false, showTrial: true },
  { value: "security_deposit_rule", label: "Security Deposit Rule", color: "#d97706",
    hint: "Defines deposit requirement — held non-spendable trust deposit, not wallet credit.",
    showDeposit: true,  showCredits: false, showBilling: false, showLeads: false, showTrial: false },
  { value: "credit_topup",          label: "Credit Top-up",         color: "#059669",
    hint: "Provider buys spendable credits for commission wallet. No deposit.",
    showDeposit: false, showCredits: true,  showBilling: false, showLeads: false, showTrial: false },
  { value: "subscription_plan",     label: "Subscription Plan",     color: "#2563eb",
    hint: "Recurring billing for coaching, real estate, restaurant, etc.",
    showDeposit: false, showCredits: false, showBilling: true,  showLeads: false, showTrial: true },
  { value: "lead_credit_package",   label: "Lead Credit Package",   color: "#db2777",
    hint: "Lead credits for lead-based verticals. Separate from commission wallet.",
    showDeposit: false, showCredits: false, showBilling: false, showLeads: true,  showTrial: false },
  { value: "trial_plan",            label: "Trial Plan",            color: "#64748b",
    hint: "Free/limited trial period before committing to full subscription.",
    showDeposit: false, showCredits: false, showBilling: false, showLeads: false, showTrial: true },
  { value: "custom_plan",           label: "Custom Plan",           color: "#94a3b8",
    hint: "Miscellaneous or special plan.",
    showDeposit: true,  showCredits: true,  showBilling: true,  showLeads: true,  showTrial: true },
];
const TYPE_MAP = Object.fromEntries(PACKAGE_TYPE_TABS.map(t => [t.value, t]));

const BILLING_OPTS = [
  { value: "",          label: "Select billing cycle" },
  { value: "one_time",  label: "One Time" },
  { value: "monthly",   label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly",    label: "Yearly" },
];

const VERTICALS = [
  { value: "",                      label: "Platform-wide (no vertical)" },
  { value: "home_services",         label: "Home Services" },
  { value: "salon",                 label: "Salon & Beauty" },
  { value: "coaching",              label: "Coaching & Education" },
  { value: "real_estate",           label: "Real Estate" },
  { value: "restaurant",            label: "Restaurant & Food" },
  { value: "automotive",            label: "Automotive" },
  { value: "professional_services", label: "Professional Services" },
  { value: "pharmacy",              label: "Pharmacy" },
  { value: "hardware",              label: "Hardware & Tools" },
  { value: "repair_services",       label: "Repair Services" },
  { value: "cleaning_services",     label: "Cleaning Services" },
  { value: "laundry",               label: "Laundry" },
];

const LIMIT_KEY_OPTS = [
  { value: "staff_count",       label: "Staff Count" },
  { value: "active_services",   label: "Active Services" },
  { value: "monthly_jobs",      label: "Monthly Jobs" },
  { value: "concurrent_jobs",   label: "Concurrent Jobs" },
  { value: "storage_gb",        label: "Storage (GB)" },
  { value: "service_areas",     label: "Service Areas" },
  { value: "brands_supported",  label: "Brands Supported" },
  { value: "listings",          label: "Property Listings" },
  { value: "courses",           label: "Courses" },
  { value: "appointments",      label: "Appointments" },
  { value: "leads",             label: "Leads" },
  { value: "support_level",     label: "Support Level" },
  { value: "custom",              label: "Custom" },
];

const PKG_TABS = [
  { id: "",                      label: "All" },
  { id: "onboarding_package",    label: "Onboarding" },
  { id: "security_deposit_rule", label: "Deposit" },
  { id: "credit_topup",          label: "Credit Top-up" },
  { id: "subscription_plan",     label: "Subscriptions" },
  { id: "lead_credit_package",   label: "Lead Credits" },
  { id: "trial_plan",            label: "Trials" },
  { id: "__audit__",             label: "Audit Logs" },
];

// ── local feature/limit drafts (before saving) ───────────────────────────────
interface DraftFeature {
  _key: string;
  feature_key: string;
  feature_label: string;
  feature_description: string;
  is_highlighted: boolean;
  is_included: boolean;
  display_order: number;
}

interface DraftLimit {
  _key: string;
  limit_key: string;
  limit_label: string;
  limit_value: string;
  limit_unit: string;
  is_unlimited: boolean;
  display_order: number;
}

const mkKey = () => Math.random().toString(36).slice(2);

const EMPTY_FORM = {
  package_type: "onboarding_package",
  name: "",
  slug: "",
  short_description: "",
  description: "",
  vertical_type: "",
  // pricing
  price: "0",
  billing_cycle: "",
  validity_days: "",
  trial_days: "",
  security_deposit_amount: "0",
  included_credit_amount: "0",
  bonus_credits: "",
  lead_credits: "",
  setup_fee_amount: "",
  renewal_price_amount: "",
  // display
  is_public_signup_visible: false,
  is_popular: false,
  is_featured: false,
  is_recommended: false,
  badge_label: "",
  cta_label: "",
  display_order: "0",
  // terms
  terms_summary: "",
  refund_policy: "",
};

type Tab = "details" | "pricing" | "features" | "limits" | "display" | "preview";

// ── Preview Card ─────────────────────────────────────────────────────────────
function PreviewCard({
  form,
  features,
  limits,
}: {
  form: typeof EMPTY_FORM;
  features: DraftFeature[];
  limits: DraftLimit[];
}) {
  const ti = TYPE_MAP[form.package_type] ?? TYPE_MAP["custom_plan"];
  const priceNum = Number(form.price) || 0;
  const deposit = Number(form.security_deposit_amount) || 0;
  const credits = Number(form.included_credit_amount) || 0;

  return (
    <div style={{
      border: "2px solid var(--border)", borderRadius: 16, padding: 24, maxWidth: 340,
      background: "var(--surface-elevated)", position: "relative",
    }}>
      {(form.is_popular || form.badge_label) && (
        <div style={{
          position: "absolute", top: -12, left: 16,
          background: form.is_popular ? "#7c3aed" : ti.color,
          color: "#fff", fontSize: 11, fontWeight: 700,
          padding: "3px 12px", borderRadius: 100,
        }}>
          {form.badge_label || "Most Popular"}
        </div>
      )}
      <p style={{ margin: "4px 0 4px", fontSize: 13, fontWeight: 700, color: ti.color }}>
        {ti.label}
      </p>
      <h3 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 800, color: "var(--text-primary)" }}>
        {form.name || "Package Name"}
      </h3>
      {form.short_description && (
        <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--text-secondary)" }}>
          {form.short_description}
        </p>
      )}
      <div style={{ margin: "12px 0" }}>
        <span style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)" }}>
          {fmt(priceNum)}
        </span>
        {form.billing_cycle && form.billing_cycle !== "one_time" && (
          <span style={{ fontSize: 13, color: "var(--text-secondary)", marginLeft: 4 }}>
            /{form.billing_cycle}
          </span>
        )}
        {form.validity_days && (
          <span style={{ fontSize: 12, color: "var(--text-tertiary)", display: "block" }}>
            Valid for {form.validity_days} days
          </span>
        )}
      </div>
      {deposit > 0 && (
        <p style={{ margin: "4px 0", fontSize: 12, color: "var(--warning-text)",
          background: "var(--warning-bg)", padding: "4px 8px", borderRadius: 6 }}>
          + {fmt(deposit)} security deposit (refundable)
        </p>
      )}
      {credits > 0 && (
        <p style={{ margin: "4px 0", fontSize: 12, color: "var(--success-text)",
          background: "var(--success-bg)", padding: "4px 8px", borderRadius: 6 }}>
          Includes {fmt(credits)} wallet credits
        </p>
      )}
      {features.length > 0 && (
        <ul style={{ margin: "12px 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
          {features.filter(f => f.is_included).map(f => (
            <li key={f._key} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 13 }}>
              <CheckCircle2 size={14} color={f.is_highlighted ? "#7c3aed" : "#059669"} style={{ flexShrink: 0, marginTop: 2 }}/>
              <span style={{ color: "var(--text-primary)", fontWeight: f.is_highlighted ? 600 : 400 }}>
                {f.feature_label || "Feature"}
              </span>
            </li>
          ))}
        </ul>
      )}
      {limits.length > 0 && (
        <div style={{ margin: "8px 0", display: "flex", flexWrap: "wrap", gap: 6 }}>
          {limits.map(l => (
            <span key={l._key} style={{
              fontSize: 11, padding: "3px 8px", borderRadius: 4,
              background: "var(--surface-sunken)", color: "var(--text-secondary)",
              border: "1px solid var(--border)",
            }}>
              {l.is_unlimited ? "Unlimited" : l.limit_value} {l.limit_unit} {l.limit_label}
            </span>
          ))}
        </div>
      )}
      <button style={{
        width: "100%", marginTop: 16, padding: "10px 0",
        background: `linear-gradient(135deg, ${ti.color}, ${ti.color}cc)`,
        color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 700,
        cursor: "pointer",
      }}>
        {form.cta_label || "Get Started"}
      </button>
      {form.terms_summary && (
        <p style={{ margin: "8px 0 0", fontSize: 10, color: "var(--text-tertiary)", textAlign: "center" }}>
          {form.terms_summary}
        </p>
      )}
    </div>
  );
}

// shared micro styles
const btnSm: React.CSSProperties = {
  width: 26, height: 26, flexShrink: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 5,
  cursor: "pointer", padding: 0, color: "var(--text-secondary)",
};
const chkLbl: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer",
  color: "var(--text-secondary)", userSelect: "none",
};
const fieldLbl: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, color: "var(--text-secondary)",
  marginBottom: 4, display: "block",
};
const textarea: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  resize: "vertical", padding: "8px 10px", borderRadius: 6, fontSize: 13,
  border: "1px solid var(--border)", background: "var(--surface)",
  color: "var(--text-primary)", fontFamily: "inherit",
  outline: "none", lineHeight: 1.5,
  transition: "border-color 0.15s",
};

// ── Feature Builder Row ───────────────────────────────────────────────────────
function FeatureRow({
  feat, onChange, onDelete, onMoveUp, onMoveDown,
}: {
  feat: DraftFeature;
  onChange: (patch: Partial<DraftFeature>) => void;
  onDelete: () => void; onMoveUp: () => void; onMoveDown: () => void;
}) {
  return (
    <div style={{
      border: "1px solid var(--border)", borderRadius: 8,
      background: "var(--surface-elevated)",
      borderLeft: `3px solid ${feat.is_highlighted ? "#7c3aed" : "var(--border)"}`,
      overflow: "hidden",
    }}>
      {/* Row header: toggles + reorder + delete */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
        borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)",
      }}>
        <label style={{ ...chkLbl, flex: 1 }}>
          <input type="checkbox" checked={feat.is_included}
            onChange={e => onChange({ is_included: e.target.checked })}/>
          <span>Included</span>
        </label>
        <label style={{ ...chkLbl, flex: 1 }}>
          <input type="checkbox" checked={feat.is_highlighted}
            onChange={e => onChange({ is_highlighted: e.target.checked })}/>
          <span style={{ color: feat.is_highlighted ? "#7c3aed" : undefined }}>Highlighted</span>
        </label>
        <div style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
          <button type="button" onClick={onMoveUp}   style={btnSm} title="Move up"><ChevronUp   size={12}/></button>
          <button type="button" onClick={onMoveDown} style={btnSm} title="Move down"><ChevronDown size={12}/></button>
          <button type="button" onClick={onDelete}   style={{ ...btnSm, color: "var(--danger-text)" }} title="Remove">
            <Trash2 size={12}/>
          </button>
        </div>
      </div>
      {/* Row body: fields */}
      <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
        <Input
          label="Feature Label *"
          value={feat.feature_label}
          onChange={v => onChange({ feature_label: v })}
          placeholder="e.g. Credit wallet enabled"
        />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <Input
            label="Description (optional)"
            value={feat.feature_description}
            onChange={v => onChange({ feature_description: v })}
            placeholder="Short explanation"
          />
          <Input
            label="Feature Key (optional)"
            value={feat.feature_key}
            onChange={v => onChange({ feature_key: v })}
            placeholder="e.g. credit_wallet"
          />
        </div>
      </div>
    </div>
  );
}

// ── Limit Builder Row ─────────────────────────────────────────────────────────
function LimitRow({
  lim, onChange, onDelete, onMoveUp, onMoveDown,
}: {
  lim: DraftLimit;
  onChange: (patch: Partial<DraftLimit>) => void;
  onDelete: () => void; onMoveUp: () => void; onMoveDown: () => void;
}) {
  return (
    <div style={{
      border: "1px solid var(--border)", borderRadius: 8,
      background: "var(--surface-elevated)", overflow: "hidden",
    }}>
      {/* Row header: type selector + actions */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
        borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)",
      }}>
        <div style={{ flex: 1 }}>
          <Select
            label=""
            value={lim.limit_key}
            onChange={v => {
              const found = LIMIT_KEY_OPTS.find(o => o.value === v);
              onChange({ limit_key: v, limit_label: found?.label || lim.limit_label });
            }}
            options={LIMIT_KEY_OPTS}
          />
        </div>
        <label style={{ ...chkLbl, whiteSpace: "nowrap", paddingTop: 2 }}>
          <input type="checkbox" checked={lim.is_unlimited}
            onChange={e => onChange({ is_unlimited: e.target.checked })}/>
          Unlimited
        </label>
        <div style={{ display: "flex", gap: 4 }}>
          <button type="button" onClick={onMoveUp}   style={btnSm} title="Move up"><ChevronUp   size={12}/></button>
          <button type="button" onClick={onMoveDown} style={btnSm} title="Move down"><ChevronDown size={12}/></button>
          <button type="button" onClick={onDelete}   style={{ ...btnSm, color: "var(--danger-text)" }} title="Remove">
            <Trash2 size={12}/>
          </button>
        </div>
      </div>
      {/* Row body */}
      <div style={{ padding: "10px 12px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 8 }}>
          <Input
            label="Display Label *"
            value={lim.limit_label}
            onChange={v => onChange({ limit_label: v })}
            placeholder="e.g. Up to 10 staff"
          />
          <Input
            label="Value"
            type="number"
            value={lim.is_unlimited ? "" : lim.limit_value}
            onChange={v => onChange({ limit_value: v })}
            placeholder="10"
          />
          <Input
            label="Unit"
            value={lim.limit_unit}
            onChange={v => onChange({ limit_unit: v })}
            placeholder="staff / GB"
          />
        </div>
      </div>
    </div>
  );
}

// ── template helpers ──────────────────────────────────────────────────────────
function getFeatureTemplate(pkgType: string): DraftFeature[] {
  const base: Omit<DraftFeature, "_key"> = {
    feature_key: "", feature_description: "",
    is_highlighted: false, is_included: true, display_order: 0,
    feature_label: "",
  };
  const labels: string[] = {
    onboarding_package: ["Service setup wizard","Provider dashboard","Credit wallet enabled","Up to 10 staff","Basic analytics","Email support"],
    subscription_plan:  ["Priority support","Advanced analytics","Customer app visibility","Dedicated account manager","API access"],
    trial_plan:         ["Limited features trial","Basic dashboard","Email support"],
    credit_topup:       ["Credits added to wallet","Use for commission deduction","No expiry"],
  }[pkgType] ?? [];
  return labels.map((label, i) => ({
    ...base, _key: mkKey(), feature_label: label, display_order: i,
    is_highlighted: i === 0,
  }));
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function PackagesPage() {
  const [activeTabId, setActiveTabId] = useState("");
  const [modalOpen,   setModalOpen]   = useState(false);
  const [editingPkg,  setEditingPkg]  = useState<AdminPackage | null>(null);
  const [formTab,     setFormTab]     = useState<Tab>("details");
  const [form,        setForm]        = useState({ ...EMPTY_FORM });
  const [drafFeatures, setDrafFeatures] = useState<DraftFeature[]>([]);
  const [drafLimits,   setDrafLimits]   = useState<DraftLimit[]>([]);
  const [saveError,   setSaveError]   = useState("");
  const [saving,      setSaving]      = useState(false);

  const isSpecialTab = activeTabId === "__audit__";
  const typeFilter   = isSpecialTab ? undefined : (activeTabId || undefined);

  const summary = useApi(useCallback(() => packageApi.summary(), []));
  const summaryData: PackageSummary | null =
    (summary.data as { data?: PackageSummary } | null)?.data ??
    (summary.data as PackageSummary | null);

  const packages = useApi(
    useCallback(() =>
      isSpecialTab ? Promise.resolve(null) :
      packageApi.list({ limit: 200 }),
    [isSpecialTab])
  );
  const auditLogs = useApi(
    useCallback(() =>
      activeTabId === "__audit__" ? packageApi.auditLogs({ limit: 100 }) : Promise.resolve(null),
    [activeTabId])
  );

  const activateAction   = useAction(useCallback((id: string) => packageApi.activate(id), []));
  const deactivateAction = useAction(useCallback((id: string) => packageApi.deactivate(id), []));
  const cloneAction      = useAction(useCallback((id: string) => packageApi.clone(id), []));
  const deleteAction     = useAction(useCallback((id: string) => packageApi.delete(id), []));

  function F(patch: Partial<typeof EMPTY_FORM>) { setForm(p => ({ ...p, ...patch })); }

  const typeInfo = TYPE_MAP[form.package_type] ?? TYPE_MAP["custom_plan"];
  const { showDeposit, showCredits, showBilling, showLeads, showTrial } = typeInfo;

  function openCreate() {
    setEditingPkg(null);
    setForm({ ...EMPTY_FORM });
    setDrafFeatures([]);
    setDrafLimits([]);
    setFormTab("details");
    setSaveError("");
    setModalOpen(true);
  }

  function openEdit(pkg: AdminPackage) {
    setEditingPkg(pkg);
    setForm({
      package_type: pkg.package_type,
      name: pkg.name,
      slug: pkg.slug,
      short_description: pkg.short_description ?? "",
      description: pkg.description ?? "",
      vertical_type: pkg.vertical_type ?? "",
      price: String(pkg.price ?? pkg.package_price ?? 0),
      billing_cycle: pkg.billing_cycle ?? "",
      validity_days: pkg.validity_days != null ? String(pkg.validity_days) : "",
      trial_days: pkg.trial_days != null ? String(pkg.trial_days) : "",
      security_deposit_amount: String(pkg.security_deposit_amount ?? 0),
      included_credit_amount: String(pkg.included_credit_amount ?? 0),
      bonus_credits: pkg.bonus_credits != null ? String(pkg.bonus_credits) : "",
      lead_credits: pkg.lead_credits != null ? String(pkg.lead_credits) : "",
      setup_fee_amount: pkg.setup_fee_amount != null ? String(pkg.setup_fee_amount) : "",
      renewal_price_amount: pkg.renewal_price_amount != null ? String(pkg.renewal_price_amount) : "",
      is_public_signup_visible: pkg.is_public_signup_visible,
      is_popular: pkg.is_popular,
      is_featured: pkg.is_featured,
      is_recommended: pkg.is_recommended,
      badge_label: pkg.badge_label ?? "",
      cta_label: pkg.cta_label ?? "",
      display_order: String(pkg.display_order ?? 0),
      terms_summary: pkg.terms_summary ?? "",
      refund_policy: pkg.refund_policy ?? "",
    });
    // Load existing features/limits into drafts
    const feats = (pkg.package_features ?? []).map(f => ({
      _key: mkKey(),
      feature_key: f.feature_key ?? "",
      feature_label: f.feature_label,
      feature_description: f.feature_description ?? "",
      is_highlighted: f.is_highlighted,
      is_included: f.is_included,
      display_order: f.display_order,
    }));
    const lims = (pkg.package_limits ?? []).map(l => ({
      _key: mkKey(),
      limit_key: l.limit_key,
      limit_label: l.limit_label,
      limit_value: l.limit_value != null ? String(l.limit_value) : "",
      limit_unit: l.limit_unit ?? "",
      is_unlimited: l.is_unlimited,
      display_order: l.display_order,
    }));
    setDrafFeatures(feats);
    setDrafLimits(lims);
    setFormTab("details");
    setSaveError("");
    setModalOpen(true);
  }

  // ── Save ──────────────────────────────────────────────────────────────────
  async function handleSave() {
    if (!form.name.trim()) { setSaveError("Package name is required."); setFormTab("details"); return; }
    if (!form.package_type) { setSaveError("Package type is required."); setFormTab("details"); return; }
    const price = Number(form.price) || 0;
    if (price < 0) { setSaveError("Price cannot be negative."); setFormTab("pricing"); return; }
    setSaving(true);
    setSaveError("");

    const payload: Record<string, unknown> = {
      package_type: form.package_type,
      name: form.name.trim(),
      short_description: form.short_description || undefined,
      description: form.description || undefined,
      vertical_type: form.vertical_type || undefined,
      package_price: price,
      billing_cycle: form.billing_cycle || undefined,
      validity_days: form.validity_days ? Number(form.validity_days) : undefined,
      trial_days: form.trial_days ? Number(form.trial_days) : undefined,
      security_deposit_amount: Number(form.security_deposit_amount) || 0,
      included_credit_amount: Number(form.included_credit_amount) || 0,
      bonus_credits: form.bonus_credits ? Number(form.bonus_credits) : undefined,
      lead_credits: form.lead_credits ? Number(form.lead_credits) : undefined,
      setup_fee_amount: form.setup_fee_amount ? Number(form.setup_fee_amount) : undefined,
      renewal_price_amount: form.renewal_price_amount ? Number(form.renewal_price_amount) : undefined,
      is_public_signup_visible: form.is_public_signup_visible,
      is_popular: form.is_popular,
      is_featured: form.is_featured,
      is_recommended: form.is_recommended,
      badge_label: form.badge_label || undefined,
      cta_label: form.cta_label || undefined,
      display_order: Number(form.display_order) || 0,
      terms_summary: form.terms_summary || undefined,
      refund_policy: form.refund_policy || undefined,
    };

    try {
      let pkgId: string;
      if (editingPkg) {
        const res = await packageApi.update(editingPkg.id, payload);
        pkgId = res.id ?? editingPkg.id;
      } else {
        const autoSlug = form.slug.trim() || form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        payload.slug = autoSlug;
        const res = await packageApi.create(payload);
        pkgId = res.id ?? "";
      }

      if (pkgId) {
        // Sync features: delete existing ones from DB then re-create from drafts
        if (editingPkg) {
          const existingFeats = editingPkg.package_features ?? [];
          for (const ef of existingFeats) {
            await packageApi.deleteFeature(pkgId, ef.feature_id);
          }
        }
        for (let i = 0; i < drafFeatures.length; i++) {
          const f = drafFeatures[i];
          if (f.feature_label.trim()) {
            await packageApi.createFeature(pkgId, {
              feature_key: f.feature_key || undefined,
              feature_label: f.feature_label.trim(),
              feature_description: f.feature_description || undefined,
              is_highlighted: f.is_highlighted,
              is_included: f.is_included,
              display_order: i,
            } as Parameters<typeof packageApi.createFeature>[1]);
          }
        }

        // Sync limits
        if (editingPkg) {
          const existingLims = editingPkg.package_limits ?? [];
          for (const el of existingLims) {
            await packageApi.deleteLimit(pkgId, el.limit_id);
          }
        }
        for (let i = 0; i < drafLimits.length; i++) {
          const l = drafLimits[i];
          if (l.limit_key && l.limit_label.trim()) {
            await packageApi.createLimit(pkgId, {
              limit_key: l.limit_key,
              limit_label: l.limit_label.trim(),
              limit_value: (!l.is_unlimited && l.limit_value) ? Number(l.limit_value) : undefined,
              limit_unit: l.limit_unit || undefined,
              is_unlimited: l.is_unlimited,
              display_order: i,
            } as Parameters<typeof packageApi.createLimit>[1]);
          }
        }
      }

      packages.refetch();
      setModalOpen(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Save failed";
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(pkg: AdminPackage) {
    if (pkg.is_active) await deactivateAction.execute(pkg.id);
    else await activateAction.execute(pkg.id);
    packages.refetch();
  }

  async function handleClone(pkg: AdminPackage) {
    await cloneAction.execute(pkg.id);
    packages.refetch();
  }

  async function handleDelete(pkg: AdminPackage) {
    if (!confirm(`Soft-delete package "${pkg.name}"?`)) return;
    await deleteAction.execute(pkg.id);
    packages.refetch();
  }

  // Feature helpers
  function addFeature() {
    setDrafFeatures(p => [
      ...p,
      { _key: mkKey(), feature_key: "", feature_label: "", feature_description: "",
        is_highlighted: false, is_included: true, display_order: p.length },
    ]);
  }
  function updateFeature(key: string, patch: Partial<DraftFeature>) {
    setDrafFeatures(p => p.map(f => f._key === key ? { ...f, ...patch } : f));
  }
  function removeFeature(key: string) {
    setDrafFeatures(p => p.filter(f => f._key !== key));
  }
  function moveFeature(key: string, dir: -1 | 1) {
    setDrafFeatures(p => {
      const i = p.findIndex(f => f._key === key);
      if (i < 0) return p;
      const ni = i + dir;
      if (ni < 0 || ni >= p.length) return p;
      const next = [...p];
      [next[i], next[ni]] = [next[ni], next[i]];
      return next;
    });
  }
  function applyFeatureTemplate() {
    const tmpl = getFeatureTemplate(form.package_type);
    if (drafFeatures.length > 0 && !confirm("Replace current features with template?")) return;
    setDrafFeatures(tmpl);
  }

  // Limit helpers
  function addLimit() {
    setDrafLimits(p => [
      ...p,
      { _key: mkKey(), limit_key: "staff_count", limit_label: "Staff",
        limit_value: "", limit_unit: "staff", is_unlimited: false, display_order: p.length },
    ]);
  }
  function updateLimit(key: string, patch: Partial<DraftLimit>) {
    setDrafLimits(p => p.map(l => l._key === key ? { ...l, ...patch } : l));
  }
  function removeLimit(key: string) {
    setDrafLimits(p => p.filter(l => l._key !== key));
  }
  function moveLimit(key: string, dir: -1 | 1) {
    setDrafLimits(p => {
      const i = p.findIndex(l => l._key === key);
      if (i < 0) return p;
      const ni = i + dir;
      if (ni < 0 || ni >= p.length) return p;
      const next = [...p];
      [next[i], next[ni]] = [next[ni], next[i]];
      return next;
    });
  }

  // ── Derived list ──────────────────────────────────────────────────────────
  const rawList = packages.data?.packages ?? [];
  const pkgList = typeFilter ? rawList.filter(p => p.package_type === typeFilter) : rawList;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <AdminLayout activeNav="packages">
      <SectionHeader
        title="Package & Plan Management"
        subtitle="Define onboarding packages, security deposits, credit top-ups, subscriptions, and lead credit packages"
        actions={<Btn size="sm" onClick={openCreate} icon={<Plus size={14}/>}>New Package</Btn>}
      />

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 10, marginBottom: 20 }}>
        {[
          { label: "Total Packages",      value: summaryData?.total,              color: "var(--primary)" },
          { label: "Active",              value: summaryData?.active,             color: "#16a34a" },
          { label: "Inactive",            value: summaryData?.inactive,           color: "#9ca3af" },
          { label: "Featured",            value: summaryData?.featured,           color: "#d97706" },
          { label: "Onboarding",          value: summaryData?.onboarding,         color: "#7c3aed" },
          { label: "Subscription",        value: summaryData?.subscription,       color: "#2563eb" },
          { label: "Lead Credits",        value: summaryData?.lead_credit,        color: "#059669" },
          { label: "Active Assignments",  value: summaryData?.active_assignments, color: "#0891b2" },
        ].map(c => (
          <div key={c.label} style={{
            background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10,
            padding: "12px 14px", borderLeft: `3px solid ${c.color}`,
          }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: c.color, fontVariantNumeric: "tabular-nums" }}>
              {summary.loading ? "…" : (c.value ?? 0)}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 3 }}>{c.label}</div>
          </div>
        ))}
      </div>

      {/* Type tabs */}
      <div style={{ display:"flex", gap:0, borderBottom:"2px solid var(--border)", marginBottom:20, overflowX:"auto" }}>
        {PKG_TABS.map(tb => {
          const active = tb.id === activeTabId;
          return (
            <button type="button" key={tb.id} onClick={() => setActiveTabId(tb.id)} style={{
              padding:"10px 16px", fontSize:13, whiteSpace:"nowrap",
              fontWeight: active ? 700 : 400,
              color: active ? "var(--brand)" : "var(--text-secondary)",
              background: "none", border: "none", outline: "none",
              borderBottom: `2px solid ${active ? "var(--brand)" : "transparent"}`,
              marginBottom: -2,
              cursor: "pointer", transition: "color 0.15s",
            }}>{tb.label}</button>
          );
        })}
      </div>

      {/* Package list */}
      {!isSpecialTab && (
        packages.loading ? (
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {[...Array(5)].map((_,i) => <Skeleton key={i} height={56}/>)}
          </div>
        ) : pkgList.length === 0 ? (
          <Card>
            <div style={{ textAlign:"center", padding:"40px 0", color:"var(--text-tertiary)" }}>
              <Package size={32} style={{ marginBottom:8, opacity:0.4 }}/>
              <p style={{ margin:0, fontSize:14 }}>No packages found</p>
              <p style={{ margin:"4px 0 0", fontSize:12 }}>
                {typeFilter
                  ? `No ${TYPE_MAP[typeFilter]?.label ?? typeFilter} packages yet.`
                  : "Click \"New Package\" to create your first package."}
              </p>
            </div>
          </Card>
        ) : (
          <Card padding={0}>
            <DataTable
              columns={[
                { key:"name",     label:"Package" },
                { key:"type",     label:"Type" },
                { key:"pricing",  label:"Price" },
                { key:"features", label:"Features / Limits" },
                { key:"signup",   label:"Signup" },
                { key:"status",   label:"Status" },
                { key:"actions",  label:"" },
              ]}
              rows={pkgList.map(pkg => {
                const ti = TYPE_MAP[pkg.package_type] ?? TYPE_MAP["custom_plan"];
                const featureCount = (pkg.package_features ?? []).length;
                const limitCount   = (pkg.package_limits   ?? []).length;
                return {
                  name: (
                    <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                      <div style={{ width:32, height:32, borderRadius:8,
                        background:`${ti.color}20`, display:"flex", alignItems:"center", justifyContent:"center" }}>
                        <Package size={13} style={{ color:ti.color }}/>
                      </div>
                      <div>
                        <p style={{ margin:0, fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                          {pkg.name}
                          {pkg.is_featured   && <Star   size={10} color="#d97706" style={{ marginLeft:4 }}/>}
                          {pkg.is_recommended && <CheckCircle2 size={10} color="#059669" style={{ marginLeft:4 }}/>}
                        </p>
                        <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                          {pkg.slug}
                          {pkg.vertical_type && ` · ${pkg.vertical_type}`}
                        </p>
                      </div>
                    </div>
                  ),
                  type: (
                    <span style={{ fontSize:11, fontWeight:600, color:ti.color,
                      background:`${ti.color}18`, padding:"3px 8px", borderRadius:4 }}>
                      {ti.label}
                    </span>
                  ),
                  pricing: (
                    <div>
                      <p style={{ margin:0, fontSize:13, fontWeight:600 }}>{fmt(pkg.price ?? pkg.package_price ?? 0)}</p>
                      <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                        {pkg.billing_cycle ?? "one-time"}
                        {Number(pkg.security_deposit_amount) > 0 && ` · ${fmt(pkg.security_deposit_amount)} dep.`}
                        {Number(pkg.included_credit_amount)  > 0 && ` · +${fmt(pkg.included_credit_amount)} cr.`}
                      </p>
                    </div>
                  ),
                  features: (
                    <div style={{ display:"flex", gap:6 }}>
                      {featureCount > 0 && (
                        <span style={{ fontSize:11, color:"var(--brand)",
                          background:"var(--brand-bg)", padding:"2px 7px", borderRadius:4 }}>
                          {featureCount} features
                        </span>
                      )}
                      {limitCount > 0 && (
                        <span style={{ fontSize:11, color:"var(--text-secondary)",
                          background:"var(--surface-sunken)", padding:"2px 7px", borderRadius:4,
                          border:"1px solid var(--border)" }}>
                          {limitCount} limits
                        </span>
                      )}
                      {featureCount === 0 && limitCount === 0 && <span style={{ color:"var(--text-tertiary)", fontSize:11 }}>—</span>}
                    </div>
                  ),
                  signup: pkg.is_public_signup_visible ? (
                    <Badge variant="success">
                      <Eye size={9} style={{ marginRight:3 }}/>Visible
                    </Badge>
                  ) : (
                    <Badge variant="muted">Hidden</Badge>
                  ),
                  status: <Badge variant={pkg.is_active ? "success" : "muted"}>{pkg.is_active ? "Active" : "Inactive"}</Badge>,
                  actions: (
                    <div style={{ display:"flex", gap:4, justifyContent:"flex-end" }}>
                      <Btn size="xs" variant="ghost" onClick={() => openEdit(pkg)} icon={<Pencil size={11}/>}>Edit</Btn>
                      <Btn size="xs" variant="ghost" onClick={() => handleClone(pkg)} icon={<Copy size={11}/>}>Clone</Btn>
                      <Btn size="xs" variant={pkg.is_active ? "ghost" : "success"} onClick={() => handleToggle(pkg)}>
                        {pkg.is_active ? "Deactivate" : "Activate"}
                      </Btn>
                      <Btn size="xs" variant="danger" onClick={() => handleDelete(pkg)} icon={<Trash2 size={11}/>}>Del</Btn>
                    </div>
                  ),
                };
              })}
            />
          </Card>
        )
      )}

      {/* Audit Logs Tab */}
      {activeTabId === "__audit__" && (
        auditLogs.loading ? <Skeleton height={200}/> : (
          <Card padding={0}>
            <DataTable
              columns={[
                { key:"action", label:"Action" },
                { key:"pkg",    label:"Package" },
                { key:"actor",  label:"Actor" },
                { key:"time",   label:"Time" },
                { key:"rid",    label:"Request ID" },
              ]}
              rows={(auditLogs.data?.items ?? []).map(log => ({
                action: <Badge variant="default">{log.action}</Badge>,
                pkg:    <span style={{ fontFamily:"monospace", fontSize:11 }}>{log.package_id?.slice(0,8) ?? "—"}</span>,
                actor:  <span style={{ fontFamily:"monospace", fontSize:11 }}>{log.actor_user_id?.slice(0,8) ?? "sys"}</span>,
                time:   <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{new Date(log.created_at).toLocaleString("en-IN")}</span>,
                rid:    <span style={{ fontSize:10, color:"var(--muted-text)" }}>{log.request_id ?? "—"}</span>,
              }))}
            />
          </Card>
        )
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          CREATE / EDIT MODAL — Tabbed enterprise form
          ═══════════════════════════════════════════════════════════════════ */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingPkg ? `Edit: ${editingPkg.name}` : "New Package"}
        size="lg"
      >
        {/* Form tabs */}
        <div style={{
          display: "flex", borderBottom: "2px solid var(--border)",
          marginBottom: 20, overflowX: "auto", gap: 0,
        }}>
          {(["details","pricing","features","limits","display","preview"] as Tab[]).map(t => {
            const active = formTab === t;
            return (
              <button type="button" key={t} onClick={() => setFormTab(t)} style={{
                padding: "9px 16px", fontSize: 12,
                fontWeight: active ? 700 : 500,
                color: active ? "var(--brand)" : "var(--text-secondary)",
                background: "none", border: "none", outline: "none",
                borderBottom: `2px solid ${active ? "var(--brand)" : "transparent"}`,
                whiteSpace: "nowrap", cursor: "pointer", textTransform: "capitalize",
                marginBottom: -2, transition: "color 0.12s",
              }}>
                {t === "features" ? `Features${drafFeatures.length ? ` (${drafFeatures.length})` : ""}` :
                 t === "limits"   ? `Limits${drafLimits.length     ? ` (${drafLimits.length})`   : ""}` : t}
              </button>
            );
          })}
        </div>

        <div style={{ maxHeight: "60vh", overflowY: "auto", paddingRight: 8, paddingBottom: 4 }}>

          {/* ── TAB: Details ── */}
          {formTab === "details" && (
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <Select label="Package Type *" value={form.package_type}
                onChange={v => F({ package_type: v })}
                options={PACKAGE_TYPE_TABS.map(t => ({ value:t.value, label:t.label }))}/>
              <div style={{ padding:"8px 12px", borderRadius:8, background:"var(--surface-sunken)",
                fontSize:12, color:"var(--text-secondary)", borderLeft:`3px solid ${typeInfo.color}` }}>
                <strong>{typeInfo.label}:</strong> {typeInfo.hint}
              </div>

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                <Input label="Package Name *" value={form.name} onChange={v => {
                    const autoSlug = v.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
                    F({ name: v, slug: autoSlug });
                  }} placeholder="e.g. Home Service Starter"/>
                {!editingPkg ? (
                  <Input label="Slug (auto-generated)" value={form.slug} onChange={v => F({ slug:v })}
                    placeholder="auto-filled from name"/>
                ) : (
                  <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                    <span style={{ fontSize:12, color:"var(--text-secondary)" }}>Slug (read-only)</span>
                    <span style={{ fontSize:13, fontFamily:"monospace", padding:"8px 10px",
                      background:"var(--surface-sunken)", borderRadius:6, color:"var(--text-tertiary)" }}>
                      {editingPkg.slug}
                    </span>
                  </div>
                )}
              </div>

              <Select label="Vertical / Category" value={form.vertical_type}
                onChange={v => F({ vertical_type:v })} options={VERTICALS}/>

              <Input label="Short Description (shown on signup card)"
                value={form.short_description} onChange={v => F({ short_description:v })}
                placeholder="One sentence about what providers get" hint="Appears under name on signup card"/>

              <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                <label style={fieldLbl}>Full Description</label>
                <textarea
                  value={form.description}
                  onChange={e => F({ description: e.target.value })}
                  placeholder="Detailed description of this package..."
                  rows={4}
                  style={textarea}
                />
              </div>

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                  <label style={fieldLbl}>Terms Summary <span style={{ fontWeight:400, color:"var(--text-tertiary)" }}>(shown below CTA on signup)</span></label>
                  <textarea
                    value={form.terms_summary}
                    onChange={e => F({ terms_summary: e.target.value })}
                    placeholder="e.g. No contract. Cancel anytime."
                    rows={2}
                    style={textarea}
                  />
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                  <label style={fieldLbl}>Refund Policy</label>
                  <textarea
                    value={form.refund_policy}
                    onChange={e => F({ refund_policy: e.target.value })}
                    placeholder="Describe refund / cancellation terms..."
                    rows={2}
                    style={textarea}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── TAB: Pricing ── */}
          {formTab === "pricing" && (
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              {form.package_type === "security_deposit_rule" && (
                <div style={{ padding:"8px 12px", borderRadius:8, background:"var(--warning-bg)",
                  border:"1px solid var(--warning-border)", fontSize:12, color:"var(--warning-text)" }}>
                  Security Deposit is <strong>non-spendable</strong> trust/onboarding deposit.
                  It is held and refunded/forfeited per policy — NOT provider wallet credit.
                </div>
              )}

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                <Input
                  label={form.package_type === "security_deposit_rule" ? "Deposit Amount (₹) *" : "Price (₹) *"}
                  type="number" value={form.price} onChange={v => F({ price:v })}/>
                {showBilling ? (
                  <Select label="Billing Cycle" value={form.billing_cycle}
                    onChange={v => F({ billing_cycle:v })} options={BILLING_OPTS}/>
                ) : (
                  <Input label="Validity Days" type="number" value={form.validity_days}
                    onChange={v => F({ validity_days:v })} placeholder="e.g. 365"/>
                )}
              </div>

              {showTrial && (
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                  <Input label="Trial Days" type="number" value={form.trial_days}
                    onChange={v => F({ trial_days:v })} placeholder="0"/>
                  {showBilling && (
                    <Input label="Renewal Price (₹)" type="number" value={form.renewal_price_amount}
                      onChange={v => F({ renewal_price_amount:v })} placeholder="Same as price"/>
                  )}
                </div>
              )}

              {showDeposit && form.package_type !== "security_deposit_rule" && (
                <div style={{
                  borderTop: "1px solid var(--border)", paddingTop: 14, marginTop: 2,
                  display: "flex", flexDirection: "column", gap: 10,
                }}>
                  <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                    letterSpacing: "0.06em", color: "var(--text-tertiary)", margin: 0 }}>
                    Security Deposit <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>— non-spendable trust deposit</span>
                  </p>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                    <Input label="Security Deposit Amount (₹)" type="number"
                      value={form.security_deposit_amount} onChange={v => F({ security_deposit_amount:v })}
                      hint="Held by platform, not spendable wallet credit"/>
                    <Input label="Setup Fee (₹)" type="number" value={form.setup_fee_amount}
                      onChange={v => F({ setup_fee_amount:v })} placeholder="0"/>
                  </div>
                </div>
              )}

              {showCredits && form.package_type !== "security_deposit_rule" && (
                <div style={{
                  borderTop: "1px solid var(--border)", paddingTop: 14, marginTop: 2,
                  display: "flex", flexDirection: "column", gap: 10,
                }}>
                  <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                    letterSpacing: "0.06em", color: "var(--text-tertiary)", margin: 0 }}>
                    {form.package_type === "credit_topup" ? "Wallet Credits" : "Included Credits"}
                    <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}> — spendable commission wallet</span>
                  </p>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                    <Input
                      label={form.package_type === "credit_topup" ? "Wallet Credits Added (₹) *" : "Included Spendable Credits (₹)"}
                      type="number" value={form.included_credit_amount}
                      onChange={v => F({ included_credit_amount:v })}
                      hint="Added to provider spendable commission wallet"/>
                    <Input label="Bonus Credits (₹)" type="number" value={form.bonus_credits}
                      onChange={v => F({ bonus_credits:v })} placeholder="0"/>
                  </div>
                </div>
              )}

              {showLeads && (
                <div style={{
                  borderTop: "1px solid var(--border)", paddingTop: 14, marginTop: 2,
                  display: "flex", flexDirection: "column", gap: 10,
                }}>
                  <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                    letterSpacing: "0.06em", color: "var(--text-tertiary)", margin: 0 }}>
                    Lead Credits <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>— separate from commission wallet</span>
                  </p>
                  <Input label="Included Lead Credits *" type="number" value={form.lead_credits}
                    onChange={v => F({ lead_credits:v })} hint="Consumed per lead unlock"/>
                </div>
              )}
            </div>
          )}

          {/* ── TAB: Features ── */}
          {formTab === "features" && (
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <div>
                  <p style={{ margin:0, fontSize:13, fontWeight:700 }}>Included Benefits</p>
                  <p style={{ margin:"2px 0 0", fontSize:11, color:"var(--text-tertiary)" }}>
                    These appear on the signup card and package detail page.
                  </p>
                </div>
                <div style={{ display:"flex", gap:8 }}>
                  <Btn size="xs" variant="ghost" onClick={applyFeatureTemplate}>
                    Use Template
                  </Btn>
                  <Btn size="xs" variant="primary" onClick={addFeature} icon={<Plus size={11}/>}>
                    Add Feature
                  </Btn>
                </div>
              </div>
              {drafFeatures.length === 0 ? (
                <div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)", fontSize:13 }}>
                  <CheckCircle2 size={28} style={{ opacity:0.3, marginBottom:8 }}/>
                  <p style={{ margin:0 }}>No features yet</p>
                  <p style={{ margin:"4px 0 0", fontSize:11 }}>
                    Click "Add Feature" or "Use Template" to add benefits.
                  </p>
                </div>
              ) : drafFeatures.map(f => (
                <FeatureRow key={f._key} feat={f}
                  onChange={p => updateFeature(f._key, p)}
                  onDelete={() => removeFeature(f._key)}
                  onMoveUp={() => moveFeature(f._key, -1)}
                  onMoveDown={() => moveFeature(f._key, 1)}/>
              ))}
              {drafFeatures.length > 0 && (
                <Btn size="xs" variant="ghost" onClick={addFeature} icon={<Plus size={11}/>}>
                  Add Another Feature
                </Btn>
              )}
            </div>
          )}

          {/* ── TAB: Limits ── */}
          {formTab === "limits" && (
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <div>
                  <p style={{ margin:0, fontSize:13, fontWeight:700 }}>Usage Limits</p>
                  <p style={{ margin:"2px 0 0", fontSize:11, color:"var(--text-tertiary)" }}>
                    Shown on signup card. Displayed as chips.
                  </p>
                </div>
                <Btn size="xs" variant="primary" onClick={addLimit} icon={<Plus size={11}/>}>
                  Add Limit
                </Btn>
              </div>
              {drafLimits.length === 0 ? (
                <div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)", fontSize:13 }}>
                  <BarChart3 size={28} style={{ opacity:0.3, marginBottom:8 }}/>
                  <p style={{ margin:0 }}>No usage limits defined</p>
                  <p style={{ margin:"4px 0 0", fontSize:11 }}>
                    Click "Add Limit" to define limits like staff count, storage, jobs, etc.
                  </p>
                </div>
              ) : drafLimits.map(l => (
                <LimitRow key={l._key} lim={l}
                  onChange={p => updateLimit(l._key, p)}
                  onDelete={() => removeLimit(l._key)}
                  onMoveUp={() => moveLimit(l._key, -1)}
                  onMoveDown={() => moveLimit(l._key, 1)}/>
              ))}
              {drafLimits.length > 0 && (
                <Btn size="xs" variant="ghost" onClick={addLimit} icon={<Plus size={11}/>}>
                  Add Another Limit
                </Btn>
              )}
            </div>
          )}

          {/* ── TAB: Display ── */}
          {formTab === "display" && (
            <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
              {/* Signup visibility — big toggle tile */}
              <label style={{
                display: "flex", alignItems: "flex-start", gap: 14, cursor: "pointer",
                padding: "14px 16px", borderRadius: 10,
                background: form.is_public_signup_visible ? "var(--success-bg)" : "var(--surface-elevated)",
                border: `1.5px solid ${form.is_public_signup_visible ? "var(--success)" : "var(--border)"}`,
              }}>
                <input type="checkbox" checked={form.is_public_signup_visible}
                  style={{ marginTop: 3, width: 16, height: 16, cursor: "pointer" }}
                  onChange={e => F({ is_public_signup_visible: e.target.checked })}/>
                <div>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                    Show on Signup Page
                  </p>
                  <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
                    Package will appear on <code style={{ fontSize: 11 }}>/register</code> for new providers.
                    Only active packages with this enabled are shown.
                  </p>
                </div>
              </label>

              {/* Badge + CTA */}
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                <Input label="Badge Label" value={form.badge_label}
                  onChange={v => F({ badge_label:v })} placeholder="e.g. Most Popular"/>
                <Input label="CTA Button Label" value={form.cta_label}
                  onChange={v => F({ cta_label:v })} placeholder="Get Started"/>
              </div>

              {/* Flags row */}
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
                {([
                  { key:"is_popular",     label:"Most Popular",  desc:"Shows 'Popular' badge" },
                  { key:"is_recommended", label:"Recommended",   desc:"Shows check badge" },
                  { key:"is_featured",    label:"Featured",      desc:"Shows star badge" },
                ] as const).map(({ key, label, desc }) => (
                  <label key={key} style={{
                    display: "flex", flexDirection: "column", gap: 6, cursor: "pointer",
                    padding: "10px 12px", borderRadius: 8,
                    background: form[key] ? "var(--accent-muted)" : "var(--surface-sunken)",
                    border: `1.5px solid ${form[key] ? "var(--brand)" : "var(--border)"}`,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input type="checkbox" checked={form[key]}
                        style={{ width: 14, height: 14 }}
                        onChange={e => F({ [key]: e.target.checked } as Partial<typeof EMPTY_FORM>)}/>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{label}</span>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{desc}</span>
                  </label>
                ))}
              </div>

              <Input label="Display Order" type="number" value={form.display_order}
                onChange={v => F({ display_order:v })} hint="Lower number = shown first on signup"/>
            </div>
          )}

          {/* ── TAB: Preview ── */}
          {formTab === "preview" && (
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:20, padding:"8px 0" }}>
              <p style={{ margin:0, fontSize:12, color:"var(--text-tertiary)" }}>
                Live preview of how this package card appears on the signup page.
              </p>
              <PreviewCard form={form} features={drafFeatures} limits={drafLimits}/>
              <div style={{ fontSize:12, color:"var(--text-tertiary)", textAlign:"center" }}>
                {!form.is_public_signup_visible && (
                  <p style={{ color:"var(--warning-text)", margin:0 }}>
                    ⚠️ Signup visibility is off — this package won&apos;t appear on /register.
                    Enable it in the Display tab.
                  </p>
                )}
                {!form.name && (
                  <p style={{ margin:0 }}>Set a package name in Details tab to see the preview.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Error + Footer */}
        {saveError && (
          <div style={{
            padding: "8px 12px", borderRadius: 6, marginTop: 8,
            background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
            fontSize: 12, color: "var(--danger-text)",
          }}>{saveError}</div>
        )}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)",
        }}>
          {/* Left: Prev tab */}
          <div>
            {(() => {
              const tabOrder: Tab[] = ["details","pricing","features","limits","display","preview"];
              const idx = tabOrder.indexOf(formTab);
              if (idx <= 0) return null;
              const prev = tabOrder[idx - 1];
              return (
                <Btn size="sm" variant="ghost" onClick={() => setFormTab(prev)}>
                  ← {prev.charAt(0).toUpperCase() + prev.slice(1)}
                </Btn>
              );
            })()}
          </div>
          {/* Right: Next + Preview + Save */}
          <div style={{ display:"flex", gap:8, alignItems:"center" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModalOpen(false)}>Cancel</Btn>
            {formTab !== "preview" && (
              <Btn variant="ghost" size="sm" onClick={() => setFormTab("preview")} icon={<Eye size={13}/>}>
                Preview
              </Btn>
            )}
            {(() => {
              const tabOrder: Tab[] = ["details","pricing","features","limits","display","preview"];
              const idx = tabOrder.indexOf(formTab);
              const next = tabOrder[idx + 1];
              if (!next || next === "preview") return null;
              return (
                <Btn size="sm" variant="ghost" onClick={() => setFormTab(next)}>
                  {next.charAt(0).toUpperCase() + next.slice(1)} →
                </Btn>
              );
            })()}
            <Btn size="sm" loading={saving} disabled={!form.name || saving} onClick={handleSave}>
              {editingPkg ? "Save Changes" : "Create Package"}
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
