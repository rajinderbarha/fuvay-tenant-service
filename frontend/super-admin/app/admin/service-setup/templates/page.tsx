"use client";

import React, { useState, useCallback } from "react";
import {
  serviceSetupTemplatesApi,
  SetupTemplateItem,
  SetupTemplatesSummary,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Btn, Modal, Spinner } from "../../../../components/shared/ui";
import {
  Globe, Home, BookOpen, Building2, Sparkles, UtensilsCrossed, ShoppingBag, Briefcase,
  Plus, RefreshCw, LayoutGrid, List as ListIcon, Search, X, ExternalLink, Rocket, Archive,
  ArchiveRestore, Copy, Trash2, FileEdit, CheckCircle2, AlertTriangle, Info, ClipboardList,
  ChevronLeft, ChevronRight, ChevronDown, ChevronUp,
} from "lucide-react";

// ── Constants ─────────────────────────────────────────────────────────────────

const VERTICAL_ICONS: Record<string, React.ReactNode> = {
  universal: <Globe size={22}/>,
  home_services: <Home size={22}/>,
  coaching_ielts: <BookOpen size={22}/>,
  real_estate: <Building2 size={22}/>,
  beauty_wellness: <Sparkles size={22}/>,
  restaurant_food: <UtensilsCrossed size={22}/>,
  product_marketplace: <ShoppingBag size={22}/>,
  professional_services: <Briefcase size={22}/>,
};

function VerticalIcon({ vkey, size = 16 }: { vkey: string; size?: number }) {
  const icon = VERTICAL_ICONS[vkey] ?? <Globe size={size}/>;
  return React.isValidElement(icon)
    ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size })
    : icon;
}

const VERTICAL_LABELS: Record<string, string> = {
  universal: "Universal",
  home_services: "Home Services",
  coaching_ielts: "Coaching / IELTS",
  real_estate: "Real Estate",
  beauty_wellness: "Beauty & Wellness",
  restaurant_food: "Restaurant & Food",
  product_marketplace: "Product Marketplace",
  professional_services: "Professional Services",
};

const VERTICAL_MODULES: Record<string, string[]> = {
  universal: ["categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping"],
  home_services: [
    "categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping",
    "service_groups", "master_services", "service_types", "brands", "issue_types",
    "service_options", "checklists", "provider_setup_rules", "pricing_defaults", "job_workflow",
  ],
  coaching_ielts: [
    "categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping",
    "courses", "course_categories", "batches", "demo_class_types", "study_modes", "fee_plans", "admission_workflow",
  ],
  real_estate: [
    "categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping",
    "property_types", "listing_types", "amenities", "localities", "site_visit_workflow", "lead_forms",
  ],
  restaurant_food: [
    "categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping",
    "menu_categories", "menu_items", "variants", "add_ons", "cuisine_types", "order_workflow",
  ],
  product_marketplace: [
    "categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping",
    "product_categories", "products", "brands", "attributes", "inventory_rules", "shipping_rules",
  ],
  professional_services: [
    "categories", "display_groups", "documents", "media_assets", "visibility_rules", "workflow_mapping",
    "service_categories_ps", "consultation_types", "document_requirements", "appointment_types", "subscription_plans",
  ],
};

const TEMPLATE_TYPES = [
  { value: "starter_pack", label: "Starter Pack" },
  { value: "service_bundle", label: "Service Bundle" },
  { value: "category_launch", label: "Category Launch" },
];

// ── Style helpers ────────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--surface-sunken)",
  color: "var(--text-primary)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "8px 12px",
  fontSize: 14,
  boxSizing: "border-box",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--text-secondary)",
  marginBottom: 4,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const fieldStyle: React.CSSProperties = { marginBottom: 16 };

const STATUS_META: Record<string, { bg: string; color: string; border: string; icon: React.ReactNode }> = {
  draft: {
    bg: "var(--warning-bg)", color: "var(--warning-text)", border: "var(--warning-border)",
    icon: <FileEdit size={11}/>,
  },
  published: {
    bg: "var(--success-bg)", color: "var(--success-text)", border: "var(--success-border)",
    icon: <CheckCircle2 size={11}/>,
  },
  archived: {
    bg: "var(--surface-sunken)", color: "var(--text-tertiary)", border: "var(--border)",
    icon: <Archive size={11}/>,
  },
};

function StatusBadge({ status }: { status: string }) {
  const m = STATUS_META[status] ?? STATUS_META.draft;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      fontSize: 11, fontWeight: 600, padding: "3px 9px",
      borderRadius: 9999, textTransform: "uppercase", letterSpacing: "0.03em",
      background: m.bg, color: m.color, border: `1px solid ${m.border}`,
    }}>
      {m.icon}
      {status}
    </span>
  );
}

function SummaryCard({
  label, value, onClick, active, icon,
}: {
  label: string; value: number | string; onClick?: () => void; active?: boolean; icon?: React.ReactNode;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: active ? "var(--accent-muted)" : "var(--surface)",
        border: active ? "1px solid var(--accent)" : "1px solid var(--border)",
        borderRadius: 12,
        padding: "16px 20px",
        cursor: onClick ? "pointer" : "default",
        transition: "all 0.15s",
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
      }}
    >
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{label}</div>
      </div>
      {icon && <div style={{ color: "var(--text-tertiary)", opacity: 0.7 }}>{icon}</div>}
    </div>
  );
}

// ── Wizard Step types ─────────────────────────────────────────────────────────

interface WizardState {
  name: string;
  code: string;
  description: string;
  template_type: string;
  is_system: boolean;
  display_order: number;
  vertical_key: string;
  modules: string[];
  items: Record<string, Array<{ item_key: string; item_name: string; extra?: string }>>;
  requires_admin_approval: boolean;
  can_tenant_customize: boolean;
  can_tenant_disable: boolean;
  create_pricing_defaults: boolean;
  create_workflow_defaults: boolean;
  create_required_documents: boolean;
  provider_needs_service_area: boolean;
  provider_needs_pricing: boolean;
  provider_needs_staff: boolean;
}

const EMPTY_WIZARD: WizardState = {
  name: "", code: "", description: "", template_type: "starter_pack",
  is_system: false, display_order: 0,
  vertical_key: "universal", modules: [],
  items: {},
  requires_admin_approval: false, can_tenant_customize: true,
  can_tenant_disable: false, create_pricing_defaults: true,
  create_workflow_defaults: true, create_required_documents: false,
  provider_needs_service_area: false, provider_needs_pricing: false, provider_needs_staff: false,
};

function slugify(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ServiceSetupTemplatesPage() {
  const [q, setQ] = useState("");
  const [filterVertical, setFilterVertical] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [page, setPage] = useState(1);

  const [showCreate, setShowCreate] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [wizard, setWizard] = useState<WizardState>(EMPTY_WIZARD);

  const [showSeedConfirm, setShowSeedConfirm] = useState(false);
  const [seedPreview, setSeedPreview] = useState<Array<{ name: string; code: string; vertical_key: string }>>([]);
  const [seedResult, setSeedResult] = useState<string | null>(null);

  const listKey = JSON.stringify({ q, filterVertical, filterType, filterStatus, page });

  const { data: listData, loading, refetch } = useApi(
    () => serviceSetupTemplatesApi.list({
      q: q || undefined, vertical: filterVertical || undefined,
      template_type: filterType || undefined, status: filterStatus || undefined,
      page, page_size: 24,
    }),
    [listKey]
  );

  const { data: summary, refetch: refetchSummary } = useApi(
    () => serviceSetupTemplatesApi.getSummary(),
    []
  );

  const { execute: execPublish } = useAction(serviceSetupTemplatesApi.publish);
  const { execute: execArchive } = useAction(serviceSetupTemplatesApi.archive);
  const { execute: execClone } = useAction(serviceSetupTemplatesApi.clone);
  const { execute: execDelete } = useAction(serviceSetupTemplatesApi.delete);

  const templates: SetupTemplateItem[] = listData?.items ?? [];
  const total = listData?.total ?? 0;
  const sum: SetupTemplatesSummary | null = summary ?? null;

  // Wizard helpers
  const wSet = useCallback((patch: Partial<WizardState>) => setWizard(prev => ({ ...prev, ...patch })), []);

  function autoCode(name: string) {
    if (!wizard.code || wizard.code === slugify(wizard.name)) {
      wSet({ code: slugify(name) });
    }
  }

  const availableModules = VERTICAL_MODULES[wizard.vertical_key] ?? VERTICAL_MODULES.universal;

  async function handleSave(publish: boolean) {
    const itemsPayload: Record<string, Array<{ item_key: string; item_name: string }>> = {};
    for (const [mk, rows] of Object.entries(wizard.items)) {
      const filtered = rows.filter(r => r.item_name.trim());
      if (filtered.length > 0) itemsPayload[mk] = filtered;
    }

    const payload: Record<string, unknown> = {
      name: wizard.name,
      code: wizard.code,
      description: wizard.description,
      vertical_key: wizard.vertical_key,
      template_type: wizard.template_type,
      is_system: wizard.is_system,
      display_order: wizard.display_order,
      status: "draft",
      modules: wizard.modules,
      items: itemsPayload,
    };

    try {
      const created = await serviceSetupTemplatesApi.create(payload);
      if (publish && created?.id) {
        await serviceSetupTemplatesApi.publish(created.id);
      }
      setShowCreate(false);
      setWizard(EMPTY_WIZARD);
      setWizardStep(1);
      refetch();
      refetchSummary();
    } catch (e) {
      alert(String(e));
    }
  }

  async function handleSeedClick() {
    const preview = await serviceSetupTemplatesApi.seedDefaultsPreview();
    setSeedPreview(preview?.templates_to_create ?? []);
    setShowSeedConfirm(true);
  }

  async function handleSeedConfirm() {
    const result = await serviceSetupTemplatesApi.seedDefaults();
    setSeedResult(`Created ${result?.created ?? 0} templates, skipped ${result?.skipped ?? 0} already existing.`);
    setShowSeedConfirm(false);
    refetch();
    refetchSummary();
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Service Setup Templates
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: 14 }}>
            Reusable starter packs for launching categories and services
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" size="sm" icon={<Sparkles size={14}/>} onClick={handleSeedClick}>
            Seed Defaults
          </Btn>
          <Btn variant="primary" size="sm" icon={<Plus size={14}/>} onClick={() => { setShowCreate(true); setWizardStep(1); setWizard(EMPTY_WIZARD); }}>
            New Template
          </Btn>
        </div>
      </div>

      {/* Summary Cards */}
      {sum && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 12, marginBottom: 24 }}>
          <SummaryCard label="Total" value={sum.total} icon={<LayoutGrid size={20}/>} onClick={() => { setFilterStatus(""); setFilterVertical(""); }} />
          <SummaryCard label="Published" value={sum.published} icon={<CheckCircle2 size={20}/>} active={filterStatus === "published"} onClick={() => setFilterStatus(filterStatus === "published" ? "" : "published")} />
          <SummaryCard label="Draft" value={sum.draft} icon={<FileEdit size={20}/>} active={filterStatus === "draft"} onClick={() => setFilterStatus(filterStatus === "draft" ? "" : "draft")} />
          <SummaryCard label="System" value={sum.system_count} icon={<Briefcase size={20}/>} />
          <SummaryCard label="Custom" value={sum.custom_count} icon={<Sparkles size={20}/>} />
          <SummaryCard label="Used" value={sum.recently_used} icon={<RefreshCw size={20}/>} />
          <SummaryCard label="Errors" value={sum.validation_errors} icon={<AlertTriangle size={20}/>} />
        </div>
      )}

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: "1 1 200px", minWidth: 160 }}>
          <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
          <input
            value={q}
            onChange={e => { setQ(e.target.value); setPage(1); }}
            placeholder="Search templates..."
            style={{ ...inputStyle, paddingLeft: 34 }}
          />
        </div>
        <select
          value={filterVertical}
          onChange={e => { setFilterVertical(e.target.value); setPage(1); }}
          style={{ ...inputStyle, width: "auto", flex: "0 0 170px" }}
        >
          <option value="">All Verticals</option>
          {Object.entries(VERTICAL_LABELS).map(([k, l]) => (
            <option key={k} value={k}>{l}</option>
          ))}
        </select>
        <select
          value={filterType}
          onChange={e => { setFilterType(e.target.value); setPage(1); }}
          style={{ ...inputStyle, width: "auto", flex: "0 0 160px" }}
        >
          <option value="">All Types</option>
          {TEMPLATE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <select
          value={filterStatus}
          onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
          style={{ ...inputStyle, width: "auto", flex: "0 0 130px" }}
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
        <div style={{ display: "flex", gap: 4 }}>
          <Btn variant={viewMode === "grid" ? "primary" : "secondary"} size="sm" icon={<LayoutGrid size={14}/>} onClick={() => setViewMode("grid")}>Grid</Btn>
          <Btn variant={viewMode === "table" ? "primary" : "secondary"} size="sm" icon={<ListIcon size={14}/>} onClick={() => setViewMode("table")}>Table</Btn>
        </div>
      </div>

      {seedResult && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--success-bg)", color: "var(--success-text)", border: "1px solid var(--success-border)", borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 14 }}>
          <CheckCircle2 size={16}/>
          <span style={{ flex: 1 }}>{seedResult}</span>
          <button onClick={() => setSeedResult(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", display: "flex" }}><X size={14}/></button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, color: "var(--text-secondary)", padding: 60, textAlign: "center" }}>
          <Spinner size={22}/>
          <span>Loading templates…</span>
        </div>
      ) : templates.length === 0 ? (
        <EmptyState onSeed={handleSeedClick} onCreate={() => { setShowCreate(true); setWizardStep(1); setWizard(EMPTY_WIZARD); }} />
      ) : viewMode === "grid" ? (
        <GridView
          templates={templates}
          onPublish={async (id) => { await execPublish(id); refetch(); refetchSummary(); }}
          onArchive={async (id) => { await execArchive(id); refetch(); refetchSummary(); }}
          onClone={async (id) => { await execClone(id); refetch(); refetchSummary(); }}
          onDelete={async (id) => { if (confirm("Delete this template?")) { await execDelete(id); refetch(); refetchSummary(); } }}
        />
      ) : (
        <TableView
          templates={templates}
          onPublish={async (id) => { await execPublish(id); refetch(); refetchSummary(); }}
          onArchive={async (id) => { await execArchive(id); refetch(); refetchSummary(); }}
          onClone={async (id) => { await execClone(id); refetch(); refetchSummary(); }}
          onDelete={async (id) => { if (confirm("Delete this template?")) { await execDelete(id); refetch(); refetchSummary(); } }}
        />
      )}

      {/* Pagination */}
      {total > 24 && (
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 24 }}>
          <Btn variant="secondary" size="sm" icon={<ChevronLeft size={14}/>} disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</Btn>
          <span style={{ padding: "6px 12px", fontSize: 13, color: "var(--text-secondary)" }}>
            Page {page} of {Math.ceil(total / 24)}
          </span>
          <Btn variant="secondary" size="sm" iconRight={<ChevronRight size={14}/>} disabled={page >= Math.ceil(total / 24)} onClick={() => setPage(p => p + 1)}>Next</Btn>
        </div>
      )}

      {/* Create Wizard Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={`Create Template — Step ${wizardStep} of 6`} size="xl">
        <WizardContent
          step={wizardStep}
          wizard={wizard}
          wSet={wSet}
          autoCode={autoCode}
          availableModules={availableModules}
          onPrev={() => setWizardStep(s => s - 1)}
          onNext={() => setWizardStep(s => s + 1)}
          onSaveDraft={() => handleSave(false)}
          onSavePublish={() => handleSave(true)}
          onCancel={() => setShowCreate(false)}
        />
      </Modal>

      {/* Seed Confirm Modal */}
      <Modal open={showSeedConfirm} onClose={() => setShowSeedConfirm(false)} title="Seed Default Templates" size="md">
        <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 16 }}>
          {seedPreview.length === 0
            ? "All default templates already exist. Nothing to create."
            : `This will create ${seedPreview.length} new template(s):`}
        </p>
        {seedPreview.length > 0 && (
          <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 12, marginBottom: 16, maxHeight: 200, overflowY: "auto" }}>
            {seedPreview.map(t => (
              <div key={t.code} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0", fontSize: 13 }}>
                <span style={{ color: "var(--text-tertiary)", display: "flex" }}><VerticalIcon vkey={t.vertical_key} size={14}/></span>
                <span style={{ color: "var(--text-primary)" }}>{t.name}</span>
                <span style={{ color: "var(--text-tertiary)", fontFamily: "monospace", fontSize: 11 }}>{t.code}</span>
              </div>
            ))}
          </div>
        )}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={() => setShowSeedConfirm(false)}>Cancel</Btn>
          {seedPreview.length > 0 && (
            <Btn variant="primary" size="sm" icon={<Sparkles size={14}/>} onClick={handleSeedConfirm}>Confirm & Seed</Btn>
          )}
        </div>
      </Modal>
    </div>
  );
}

// ── Grid View ─────────────────────────────────────────────────────────────────

function GridView({ templates, onPublish, onArchive, onClone, onDelete }: {
  templates: SetupTemplateItem[];
  onPublish: (id: string) => void;
  onArchive: (id: string) => void;
  onClone: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
      {templates.map(t => (
        <div key={t.id} style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 12, padding: 20, display: "flex", flexDirection: "column", gap: 12,
          transition: "border-color 0.15s, box-shadow 0.15s",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10, background: "var(--accent-muted)",
                color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
              }}>
                <VerticalIcon vkey={t.vertical_key} size={20}/>
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>{t.name}</div>
                <div style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{t.code}</div>
              </div>
            </div>
            <StatusBadge status={t.status} />
          </div>

          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 9999, background: "var(--surface-sunken)", color: "var(--text-secondary)" }}>
              {VERTICAL_LABELS[t.vertical_key] ?? t.vertical_key}
            </span>
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 9999, background: "var(--surface-sunken)", color: "var(--text-secondary)" }}>
              {t.template_type}
            </span>
            {t.is_system && (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, padding: "2px 8px", borderRadius: 9999, background: "var(--accent-muted)", color: "var(--accent)" }}>
                <Briefcase size={10}/> System
              </span>
            )}
            {t.modules_count != null && (
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 9999, background: "var(--surface-sunken)", color: "var(--text-tertiary)" }}>
                {t.modules_count} modules
              </span>
            )}
          </div>

          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: "auto", paddingTop: 4 }}>
            <a href={`/admin/service-setup/templates/${t.id}`} style={{ textDecoration: "none" }}>
              <Btn variant="secondary" size="xs" icon={<ExternalLink size={12}/>}>Open</Btn>
            </a>
            {t.status === "draft" && (
              <Btn variant="success" size="xs" icon={<Rocket size={12}/>} onClick={() => onPublish(t.id)}>Publish</Btn>
            )}
            {t.status === "published" && (
              <Btn variant="secondary" size="xs" icon={<Archive size={12}/>} onClick={() => onArchive(t.id)}>Archive</Btn>
            )}
            {t.status === "archived" && (
              <Btn variant="success" size="xs" icon={<ArchiveRestore size={12}/>} onClick={() => onPublish(t.id)}>Republish</Btn>
            )}
            <Btn variant="ghost" size="xs" icon={<Copy size={12}/>} onClick={() => onClone(t.id)}>Clone</Btn>
            {(t.status === "draft" || t.status === "archived") && (
              <Btn variant="danger" size="xs" icon={<Trash2 size={12}/>} onClick={() => onDelete(t.id)}>Delete</Btn>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Table View ────────────────────────────────────────────────────────────────

function TableView({ templates, onPublish, onArchive, onClone, onDelete }: {
  templates: SetupTemplateItem[];
  onPublish: (id: string) => void;
  onArchive: (id: string) => void;
  onClone: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {["Template", "Vertical", "Type", "Status", "System", "Version", "Updated", "Actions"].map(h => (
              <th key={h} style={{ padding: "10px 12px", textAlign: "left", color: "var(--text-secondary)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {templates.map(t => (
            <tr key={t.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "10px 12px" }}>
                <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{t.name}</div>
                <div style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{t.code}</div>
              </td>
              <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>
                <div style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <VerticalIcon vkey={t.vertical_key} size={14}/>
                  {VERTICAL_LABELS[t.vertical_key] ?? t.vertical_key}
                </div>
              </td>
              <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{t.template_type}</td>
              <td style={{ padding: "10px 12px" }}><StatusBadge status={t.status} /></td>
              <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{t.is_system ? "Yes" : "No"}</td>
              <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>v{t.version}</td>
              <td style={{ padding: "10px 12px", color: "var(--text-tertiary)", fontSize: 11 }}>
                {t.updated_at ? new Date(t.updated_at).toLocaleDateString() : "—"}
              </td>
              <td style={{ padding: "10px 12px" }}>
                <div style={{ display: "flex", gap: 4 }}>
                  <a href={`/admin/service-setup/templates/${t.id}`} style={{ textDecoration: "none" }}>
                    <Btn variant="ghost" size="xs" icon={<ExternalLink size={12}/>}>Open</Btn>
                  </a>
                  {t.status === "draft" && <Btn variant="success" size="xs" icon={<Rocket size={12}/>} onClick={() => onPublish(t.id)}>Publish</Btn>}
                  {t.status === "published" && <Btn variant="secondary" size="xs" icon={<Archive size={12}/>} onClick={() => onArchive(t.id)}>Archive</Btn>}
                  {t.status === "archived" && <Btn variant="success" size="xs" icon={<ArchiveRestore size={12}/>} onClick={() => onPublish(t.id)}>Republish</Btn>}
                  <Btn variant="ghost" size="xs" icon={<Copy size={12}/>} onClick={() => onClone(t.id)}>Clone</Btn>
                  {(t.status === "draft" || t.status === "archived") && <Btn variant="danger" size="xs" icon={<Trash2 size={12}/>} onClick={() => onDelete(t.id)}>Delete</Btn>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────

function EmptyState({ onSeed, onCreate }: { onSeed: () => void; onCreate: () => void }) {
  return (
    <div style={{ textAlign: "center", padding: "80px 20px" }}>
      <div style={{
        width: 72, height: 72, borderRadius: 18, background: "var(--surface-sunken)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "var(--text-tertiary)", margin: "0 auto 16px",
      }}>
        <ClipboardList size={32}/>
      </div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
        No service setup templates found.
      </h2>
      <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 32, maxWidth: 400, margin: "0 auto 32px" }}>
        Templates help you quickly launch new categories and services with pre-configured modules, items, and workflows.
      </p>
      <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
        <Btn variant="primary" icon={<Sparkles size={14}/>} onClick={onSeed}>Seed Default Templates</Btn>
        <Btn variant="secondary" icon={<Plus size={14}/>} onClick={onCreate}>Create New Template</Btn>
      </div>
    </div>
  );
}

// ── Wizard Content ────────────────────────────────────────────────────────────

function WizardContent({
  step, wizard, wSet, autoCode, availableModules,
  onPrev, onNext, onSaveDraft, onSavePublish, onCancel,
}: {
  step: number;
  wizard: WizardState;
  wSet: (p: Partial<WizardState>) => void;
  autoCode: (name: string) => void;
  availableModules: string[];
  onPrev: () => void;
  onNext: () => void;
  onSaveDraft: () => void;
  onSavePublish: () => void;
  onCancel: () => void;
}) {
  const canNext = step < 6;
  const canPrev = step > 1;

  return (
    <div>
      {/* Progress */}
      <div style={{ display: "flex", gap: 4, marginBottom: 24 }}>
        {[1,2,3,4,5,6].map(s => (
          <div key={s} style={{
            flex: 1, height: 4, borderRadius: 2,
            background: s <= step ? "var(--accent)" : "var(--border)",
            transition: "background 0.2s",
          }} />
        ))}
      </div>

      {/* Steps */}
      {step === 1 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>Basic Details</h3>
          <div style={fieldStyle}>
            <label style={labelStyle}>Template Name *</label>
            <input
              value={wizard.name}
              onChange={e => { wSet({ name: e.target.value }); autoCode(e.target.value); }}
              placeholder="e.g. Home Services Starter Pack"
              style={inputStyle}
            />
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle}>Code (slug) *</label>
            <input
              value={wizard.code}
              onChange={e => wSet({ code: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_") })}
              placeholder="e.g. home_services_starter_pack"
              style={{ ...inputStyle, fontFamily: "monospace" }}
            />
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle}>Description</label>
            <textarea
              value={wizard.description}
              onChange={e => wSet({ description: e.target.value })}
              rows={3}
              placeholder="Briefly describe what this template sets up..."
              style={{ ...inputStyle, resize: "vertical" }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div style={fieldStyle}>
              <label style={labelStyle}>Template Type</label>
              <select value={wizard.template_type} onChange={e => wSet({ template_type: e.target.value })} style={inputStyle}>
                {TEMPLATE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Display Order</label>
              <input
                type="number"
                value={wizard.display_order}
                onChange={e => wSet({ display_order: parseInt(e.target.value) || 0 })}
                style={inputStyle}
              />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <input
              type="checkbox"
              id="is_system"
              checked={wizard.is_system}
              onChange={e => wSet({ is_system: e.target.checked })}
            />
            <label htmlFor="is_system" style={{ fontSize: 14, color: "var(--text-secondary)" }}>System Template (cannot be deleted by tenants)</label>
          </div>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>Vertical & Scope</h3>
          <div style={fieldStyle}>
            <label style={labelStyle}>Vertical</label>
            <select
              value={wizard.vertical_key}
              onChange={e => wSet({ vertical_key: e.target.value, modules: [] })}
              style={inputStyle}
            >
              {Object.entries(VERTICAL_LABELS).map(([k, l]) => (
                <option key={k} value={k}>{VERTICAL_ICONS[k]} {l}</option>
              ))}
            </select>
          </div>
          <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 16, marginTop: 8 }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>Available modules for this vertical:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {(VERTICAL_MODULES[wizard.vertical_key] ?? []).map(m => (
                <span key={m} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 9999, background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  {m}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>Modules</h3>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
            Select which modules to include in this template.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
            {availableModules.map(m => (
              <label key={m} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: "var(--surface-sunken)", borderRadius: 8, cursor: "pointer", border: wizard.modules.includes(m) ? "1px solid var(--accent)" : "1px solid var(--border)" }}>
                <input
                  type="checkbox"
                  checked={wizard.modules.includes(m)}
                  onChange={e => {
                    if (e.target.checked) {
                      wSet({ modules: [...wizard.modules, m] });
                    } else {
                      wSet({ modules: wizard.modules.filter(x => x !== m) });
                    }
                  }}
                />
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{m}</span>
              </label>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
            {wizard.modules.length} module(s) selected
          </div>
        </div>
      )}

      {step === 4 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>Content Builder</h3>
          {wizard.modules.length === 0 ? (
            <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>No modules selected. Go back to Step 3 to select modules.</p>
          ) : (
            wizard.modules.map(mk => (
              <ModuleItemBuilder
                key={mk}
                moduleKey={mk}
                items={wizard.items[mk] ?? []}
                onChange={rows => wSet({ items: { ...wizard.items, [mk]: rows } })}
              />
            ))
          )}
        </div>
      )}

      {step === 5 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>Defaults & Rules</h3>
          {[
            { key: "requires_admin_approval" as const, label: "Requires Admin Approval" },
            { key: "can_tenant_customize" as const, label: "Tenant Can Customize" },
            { key: "can_tenant_disable" as const, label: "Tenant Can Disable" },
            { key: "create_pricing_defaults" as const, label: "Create Pricing Defaults" },
            { key: "create_workflow_defaults" as const, label: "Create Workflow Defaults" },
            { key: "create_required_documents" as const, label: "Create Required Documents" },
          ].map(({ key, label }) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <input
                type="checkbox"
                id={key}
                checked={wizard[key] as boolean}
                onChange={e => wSet({ [key]: e.target.checked })}
              />
              <label htmlFor={key} style={{ fontSize: 14, color: "var(--text-secondary)" }}>{label}</label>
            </div>
          ))}
          {wizard.vertical_key === "home_services" && (
            <div style={{ marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>Provider Requirements</div>
              {[
                { key: "provider_needs_service_area" as const, label: "Provider Needs Service Area" },
                { key: "provider_needs_pricing" as const, label: "Provider Needs Pricing" },
                { key: "provider_needs_staff" as const, label: "Provider Needs Staff" },
              ].map(({ key, label }) => (
                <div key={key} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                  <input
                    type="checkbox"
                    id={key}
                    checked={wizard[key] as boolean}
                    onChange={e => wSet({ [key]: e.target.checked })}
                  />
                  <label htmlFor={key} style={{ fontSize: 14, color: "var(--text-secondary)" }}>{label}</label>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {step === 6 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>Preview & Validate</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
            <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>Template</div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>{wizard.name || "—"}</div>
              <div style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-tertiary)" }}>{wizard.code}</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{VERTICAL_ICONS[wizard.vertical_key]} {VERTICAL_LABELS[wizard.vertical_key]}</div>
            </div>
            <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>Summary</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Modules: {wizard.modules.length}</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                Items: {Object.values(wizard.items).reduce((s, rows) => s + rows.filter(r => r.item_name.trim()).length, 0)}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Type: {wizard.template_type}</div>
            </div>
          </div>

          {/* Local validation */}
          {(() => {
            const errors: string[] = [];
            const warnings: string[] = [];
            if (!wizard.name.trim()) errors.push("Template name is required.");
            if (!wizard.code.trim()) errors.push("Code is required.");
            if (wizard.vertical_key === "coaching_ielts" && wizard.modules.includes("issue_types")) {
              errors.push("Coaching templates cannot include issue_types module.");
            }
            if (wizard.modules.length === 0) warnings.push("No modules selected.");
            return (
              <div>
                {errors.length > 0 && (
                  <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 8, padding: 12, marginBottom: 12 }}>
                    {errors.map((e, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--danger-text)" }}>
                        <AlertTriangle size={14}/> {e}
                      </div>
                    ))}
                  </div>
                )}
                {warnings.length > 0 && (
                  <div style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius: 8, padding: 12, marginBottom: 12 }}>
                    {warnings.map((w, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--warning-text)" }}>
                        <Info size={14}/> {w}
                      </div>
                    ))}
                  </div>
                )}
                {errors.length === 0 && warnings.length === 0 && (
                  <div style={{ background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius: 8, padding: 12, marginBottom: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--success-text)" }}>
                      <CheckCircle2 size={14}/> Template looks valid and ready to save.
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
        <Btn variant="ghost" size="sm" onClick={onCancel}>Cancel</Btn>
        <div style={{ display: "flex", gap: 8 }}>
          {canPrev && <Btn variant="secondary" size="sm" icon={<ChevronLeft size={14}/>} onClick={onPrev}>Back</Btn>}
          {canNext && <Btn variant="primary" size="sm" iconRight={<ChevronRight size={14}/>} onClick={onNext}>Next</Btn>}
          {step === 6 && (
            <>
              <Btn variant="secondary" size="sm" icon={<FileEdit size={14}/>} onClick={onSaveDraft}>Save Draft</Btn>
              <Btn variant="primary" size="sm" icon={<Rocket size={14}/>} onClick={onSavePublish}>Save & Publish</Btn>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Module Item Builder ───────────────────────────────────────────────────────

function ModuleItemBuilder({
  moduleKey,
  items,
  onChange,
}: {
  moduleKey: string;
  items: Array<{ item_key: string; item_name: string; extra?: string }>;
  onChange: (rows: Array<{ item_key: string; item_name: string; extra?: string }>) => void;
}) {
  const [open, setOpen] = useState(true);

  function addRow() {
    onChange([...items, { item_key: "", item_name: "" }]);
  }

  function removeRow(i: number) {
    onChange(items.filter((_, idx) => idx !== i));
  }

  function updateRow(i: number, patch: Partial<{ item_key: string; item_name: string; extra?: string }>) {
    const next = [...items];
    next[i] = { ...next[i], ...patch };
    if (patch.item_name !== undefined && !next[i].item_key) {
      next[i].item_key = patch.item_name.toLowerCase().replace(/[^a-z0-9]+/g, "_");
    }
    onChange(next);
  }

  return (
    <div style={{ marginBottom: 16, border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          padding: "10px 16px", background: "var(--surface-sunken)", cursor: "pointer",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>
          {moduleKey.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
          <span style={{ fontWeight: 400, color: "var(--text-tertiary)", marginLeft: 8 }}>({items.length} items)</span>
        </span>
        <span style={{ color: "var(--text-tertiary)", display: "flex" }}>{open ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}</span>
      </div>
      {open && (
        <div style={{ padding: 16 }}>
          {items.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              {items.map((row, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
                  <input
                    value={row.item_name}
                    onChange={e => updateRow(i, { item_name: e.target.value })}
                    placeholder="Item name"
                    style={{ ...inputStyle, flex: 2 }}
                  />
                  <input
                    value={row.item_key}
                    onChange={e => updateRow(i, { item_key: e.target.value })}
                    placeholder="key"
                    style={{ ...inputStyle, flex: 1, fontFamily: "monospace", fontSize: 12 }}
                  />
                  <button
                    onClick={() => removeRow(i)}
                    style={{ display: "flex", alignItems: "center", background: "none", border: "1px solid var(--danger-border)", color: "var(--danger-text)", borderRadius: 6, padding: "5px 8px", cursor: "pointer" }}
                  >
                    <X size={13}/>
                  </button>
                </div>
              ))}
            </div>
          )}
          <Btn variant="ghost" size="xs" icon={<Plus size={12}/>} onClick={addRow}>Add Row</Btn>
        </div>
      )}
    </div>
  );
}
