"use client";
import { TableSurface } from "@serviceos/design-system";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  bulkWizardApi,
  serviceSetupTemplatesApi,
  BulkDraftItem,
  BulkWizardSummary,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Btn, Modal, SummaryCard,} from "../../../../components/shared/ui";
import { PageHeader } from "@serviceos/design-system";

// ── Vertical / Module constants ───────────────────────────────────────────────

const VERTICALS = [
  { value: "home_services", label: "Home Services" },
  { value: "coaching_ielts", label: "Coaching / IELTS" },
  { value: "real_estate", label: "Real Estate" },
  { value: "beauty_wellness", label: "Beauty & Wellness" },
  { value: "restaurant_food", label: "Restaurant & Food" },
  { value: "product_marketplace", label: "Product Marketplace" },
  { value: "professional_services", label: "Professional Services" },
];

const VERTICAL_MODULES: Record<string, { key: string; label: string }[]> = {
  universal: [
    { key: "categories", label: "Categories" },
    { key: "display_groups", label: "Display Groups" },
    { key: "documents", label: "Required Documents" },
    { key: "workflow_mapping", label: "Workflow Mapping" },
  ],
  home_services: [
    { key: "service_groups", label: "Service Groups" },
    { key: "master_services", label: "Master Services" },
    { key: "service_types", label: "Service Types" },
    { key: "brands", label: "Brands" },
    { key: "issue_types", label: "Issue Types" },
    { key: "service_options", label: "Service Options / Add-ons" },
    { key: "checklists", label: "Checklists" },
    { key: "provider_setup_rules", label: "Provider Setup Rules" },
    { key: "pricing_defaults", label: "Pricing Defaults" },
    { key: "job_workflow", label: "Job Workflow" },
  ],
  coaching_ielts: [
    { key: "courses", label: "Courses" },
    { key: "course_categories", label: "Course Categories" },
    { key: "batches", label: "Batches" },
    { key: "demo_class_types", label: "Demo Class Types" },
    { key: "fee_plans", label: "Fee Plans" },
    { key: "admission_workflow", label: "Admission Workflow" },
  ],
  real_estate: [
    { key: "property_types", label: "Property Types" },
    { key: "listing_types", label: "Listing Types" },
    { key: "amenities", label: "Amenities" },
    { key: "localities", label: "Localities" },
    { key: "site_visit_workflow", label: "Site Visit Workflow" },
    { key: "lead_forms", label: "Lead Forms" },
  ],
  restaurant_food: [
    { key: "menu_categories", label: "Menu Categories" },
    { key: "menu_items", label: "Menu Items" },
    { key: "variants", label: "Variants" },
    { key: "add_ons", label: "Add-ons" },
    { key: "cuisine_types", label: "Cuisine Types" },
    { key: "order_workflow", label: "Order Workflow" },
  ],
  product_marketplace: [
    { key: "product_categories", label: "Product Categories" },
    { key: "products", label: "Products" },
    { key: "brands", label: "Brands" },
    { key: "attributes", label: "Attributes" },
    { key: "inventory_rules", label: "Inventory Rules" },
    { key: "shipping_rules", label: "Shipping Rules" },
  ],
  professional_services: [
    { key: "service_categories_ps", label: "Service Categories" },
    { key: "consultation_types", label: "Consultation Types" },
    { key: "document_requirements", label: "Document Requirements" },
    { key: "appointment_types", label: "Appointment Types" },
    { key: "subscription_plans", label: "Subscription Plans" },
  ],
  beauty_wellness: [
    { key: "treatment_categories", label: "Treatment Categories" },
    { key: "treatments", label: "Treatments" },
    { key: "staff_roles", label: "Staff Roles" },
    { key: "packages", label: "Packages" },
  ],
};

function getModulesForVertical(vertical: string) {
  const universalMods = VERTICAL_MODULES.universal ?? [];
  const verticalMods = VERTICAL_MODULES[vertical] ?? [];
  return [...universalMods, ...verticalMods];
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface ContentItem {
  name: string;
  code: string;
  [key: string]: string | boolean;
}

interface WizardState {
  step: number;
  name: string;
  code: string;
  description: string;
  vertical: string;
  setup_mode: string;
  template_id: string | null;
  scope: {
    category_name: string;
    category_code: string;
    customer_visible: boolean;
    requires_admin_approval: boolean;
  };
  modules: string[];
  content: Record<string, ContentItem[]>;
  rules: Record<string, boolean>;
  pricing: { enabled: boolean; model: string; city_zip_mapping: boolean };
  draftId: string | null;
}

const STEP_LABELS = [
  "", "Start", "Template", "Scope", "Modules", "Content",
  "Rules", "Pricing", "Preview", "Validate", "Execute",
];

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string }> = {
    draft: { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" },
    ready_to_run: { bg: "var(--success-bg)", color: "var(--success-text)" },
    running: { bg: "var(--accent-muted)", color: "var(--accent)" },
    completed: { bg: "var(--success-bg)", color: "var(--success-text)" },
    failed: { bg: "var(--danger-bg)", color: "var(--danger-text)" },
    validation_failed: { bg: "var(--warning-bg)", color: "var(--warning-text)" },
    partially_completed: { bg: "var(--warning-bg)", color: "var(--warning-text)" },
    archived: { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  };
  const s = map[status] ?? map.draft;
  return (
    <span style={{
      background: s.bg, color: s.color,
      fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
      textTransform: "uppercase", letterSpacing: 0.5,
    }}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

// ── Summary card ──────────────────────────────────────────────────────────────


// ── Input helpers ─────────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  background: "var(--surface-sunken)", color: "var(--text-primary)",
  border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  padding: "8px 12px", fontSize: 13, width: "100%",
  boxSizing: "border-box",
};
const labelStyle: React.CSSProperties = {
  fontSize: 12, color: "var(--text-secondary)", marginBottom: 4, display: "block",
};

// ── Wizard Modal ──────────────────────────────────────────────────────────────

function WizardModal({
  open, onClose, onSaved, initialDraft,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  initialDraft?: BulkDraftItem | null;
}) {
  const [wiz, setWiz] = useState<WizardState>({
    step: 1,
    name: initialDraft?.name ?? "",
    code: initialDraft?.draft_code ?? "",
    description: "",
    vertical: initialDraft?.vertical_key ?? "",
    setup_mode: initialDraft?.setup_mode ?? "manual",
    template_id: initialDraft?.template_id ?? null,
    scope: { category_name: "", category_code: "", customer_visible: true, requires_admin_approval: false },
    modules: [],
    content: {},
    rules: {},
    pricing: { enabled: false, model: "fixed", city_zip_mapping: false },
    draftId: initialDraft?.id ?? null,
  });
  const [saving, setSaving] = useState(false);
  const [validateResult, setValidateResult] = useState<{
    valid: boolean; errors: unknown[]; warnings: unknown[]; blocking_count: number;
  } | null>(null);
  const [previewItems, setPreviewItems] = useState<unknown[]>([]);
  const [previewSummary, setPreviewSummary] = useState<Record<string, number>>({});
  const [executeReason, setExecuteReason] = useState("");
  const [executeConfirm, setExecuteConfirm] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [runResult, setRunResult] = useState<unknown>(null);

  const update = (patch: Partial<WizardState>) => setWiz(w => ({ ...w, ...patch }));

  // ── Step 1 ────────────────────────────────────────────────────────────────

  function renderStep1() {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label style={labelStyle}>Setup Name *</label>
          <input style={inputStyle} value={wiz.name} onChange={e => {
            const name = e.target.value;
            update({ name, code: slugify(name) });
          }} placeholder="e.g. Home Services Full Launch" />
        </div>
        <div>
          <label style={labelStyle}>Draft Code (auto-generated)</label>
          <input style={{ ...inputStyle, color: "var(--text-tertiary)" }} value={wiz.code} readOnly />
        </div>
        <div>
          <label style={labelStyle}>Description</label>
          <textarea style={{ ...inputStyle, minHeight: 70, resize: "vertical" }}
            value={wiz.description} onChange={e => update({ description: e.target.value })} />
        </div>
        <div>
          <label style={labelStyle}>Vertical *</label>
          <select style={inputStyle} value={wiz.vertical} onChange={e => {
            const v = e.target.value;
            update({ vertical: v, modules: getModulesForVertical(v).map(m => m.key) });
          }}>
            <option value="">Select vertical...</option>
            {VERTICALS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Setup Mode</label>
          <select style={inputStyle} value={wiz.setup_mode} onChange={e => update({ setup_mode: e.target.value })}>
            <option value="manual">Manual</option>
            <option value="use_template">Use Template</option>
            <option value="import_json">Import JSON</option>
            <option value="clone">Clone</option>
          </select>
        </div>
      </div>
    );
  }

  // ── Step 2 ────────────────────────────────────────────────────────────────

  function renderStep2() {
    if (wiz.setup_mode !== "use_template") {
      return (
        <div style={{ color: "var(--text-secondary)", padding: 24, textAlign: "center" }}>
          Template selection is only available in "Use Template" mode.<br />
          You selected: <strong>{wiz.setup_mode}</strong>. Continue to next step.
        </div>
      );
    }
    return (
      <div>
        <div style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 16 }}>
          Select a published template to pre-fill module configurations.
        </div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
          Templates for vertical "{wiz.vertical}" will appear here. Feature requires templates to be published.
        </div>
      </div>
    );
  }

  // ── Step 3 ────────────────────────────────────────────────────────────────

  function renderStep3() {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label style={labelStyle}>Category Name</label>
          <input style={inputStyle} value={wiz.scope.category_name}
            onChange={e => {
              const n = e.target.value;
              update({ scope: { ...wiz.scope, category_name: n, category_code: slugify(n) } });
            }} placeholder="e.g. Home Services" />
        </div>
        <div>
          <label style={labelStyle}>Category Code</label>
          <input style={inputStyle} value={wiz.scope.category_code}
            onChange={e => update({ scope: { ...wiz.scope, category_code: e.target.value } })} />
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: "var(--text-primary)" }}>
            <input type="checkbox" checked={wiz.scope.customer_visible}
              onChange={e => update({ scope: { ...wiz.scope, customer_visible: e.target.checked } })} />
            Customer Visible
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: "var(--text-primary)" }}>
            <input type="checkbox" checked={wiz.scope.requires_admin_approval}
              onChange={e => update({ scope: { ...wiz.scope, requires_admin_approval: e.target.checked } })} />
            Requires Admin Approval
          </label>
        </div>
      </div>
    );
  }

  // ── Step 4 ────────────────────────────────────────────────────────────────

  function renderStep4() {
    const allMods = getModulesForVertical(wiz.vertical);
    if (!wiz.vertical) return <div style={{ color: "var(--text-secondary)" }}>Select a vertical in Step 1 first.</div>;
    return (
      <div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
          Select modules to include in this bulk setup. All are pre-selected by default.
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {allMods.map(mod => (
            <label key={mod.key} style={{
              display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
              fontSize: 13, color: "var(--text-primary)",
              background: "var(--surface-sunken)", borderRadius: 6,
              padding: "8px 12px", border: "1px solid var(--border)",
            }}>
              <input type="checkbox"
                checked={wiz.modules.includes(mod.key)}
                onChange={e => {
                  const mods = e.target.checked
                    ? [...wiz.modules, mod.key]
                    : wiz.modules.filter(k => k !== mod.key);
                  update({ modules: mods });
                }} />
              {mod.label}
            </label>
          ))}
        </div>
      </div>
    );
  }

  // ── Step 5 ────────────────────────────────────────────────────────────────

  function renderStep5() {
    const activeMods = getModulesForVertical(wiz.vertical).filter(m => wiz.modules.includes(m.key));
    if (!activeMods.length) return <div style={{ color: "var(--text-secondary)" }}>Enable modules in Step 4 first.</div>;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {activeMods.map(mod => {
          const items = wiz.content[mod.key] ?? [];
          return (
            <div key={mod.key} style={{
              border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
              background: "var(--surface-sunken)",
            }}>
              <div style={{
                padding: "8px 12px", borderBottom: "1px solid var(--border)",
                fontWeight: 600, fontSize: 13, color: "var(--text-primary)",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                {mod.label}
                <Btn size="xs" variant="ghost" onClick={() => {
                  const newItems = [...items, { name: "", code: "" }];
                  update({ content: { ...wiz.content, [mod.key]: newItems } });
                }}>+ Add Row</Btn>
              </div>
              <div style={{ padding: 12 }}>
                {items.length === 0 && (
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)", fontStyle: "italic" }}>No items yet. Click Add Row.</div>
                )}
                {items.map((item, idx) => (
                  <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
                    <input style={{ ...inputStyle, flex: 2 }} placeholder="Name"
                      value={item.name} onChange={e => {
                        const name = e.target.value;
                        const updated = [...items];
                        updated[idx] = { ...updated[idx], name, code: slugify(name) };
                        update({ content: { ...wiz.content, [mod.key]: updated } });
                      }} />
                    <input style={{ ...inputStyle, flex: 1 }} placeholder="Code"
                      value={item.code} onChange={e => {
                        const updated = [...items];
                        updated[idx] = { ...updated[idx], code: e.target.value };
                        update({ content: { ...wiz.content, [mod.key]: updated } });
                      }} />
                    {mod.key === "issue_types" && (
                      <select style={{ ...inputStyle, flex: 1 }}
                        value={String(item.severity ?? "medium")}
                        onChange={e => {
                          const updated = [...items];
                          updated[idx] = { ...updated[idx], severity: e.target.value };
                          update({ content: { ...wiz.content, [mod.key]: updated } });
                        }}>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                      </select>
                    )}
                    {mod.key === "service_options" && (
                      <select style={{ ...inputStyle, flex: 1 }}
                        value={String(item.option_type ?? "addon")}
                        onChange={e => {
                          const updated = [...items];
                          updated[idx] = { ...updated[idx], option_type: e.target.value };
                          update({ content: { ...wiz.content, [mod.key]: updated } });
                        }}>
                        <option value="addon">Add-on</option>
                        <option value="requirement">Requirement</option>
                        <option value="upgrade">Upgrade</option>
                      </select>
                    )}
                    <Btn size="xs" variant="danger" onClick={() => {
                      const updated = items.filter((_, i) => i !== idx);
                      update({ content: { ...wiz.content, [mod.key]: updated } });
                    }}>×</Btn>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // ── Step 6 ────────────────────────────────────────────────────────────────

  function renderStep6() {
    const baseRules = [
      { key: "requires_admin_approval", label: "Requires Admin Approval" },
      { key: "can_tenant_customize", label: "Tenants Can Customize" },
      { key: "create_pricing_defaults", label: "Create Pricing Defaults" },
      { key: "create_workflow_defaults", label: "Create Workflow Defaults" },
      { key: "create_required_documents", label: "Create Required Documents" },
    ];
    const hsRules = wiz.vertical === "home_services" ? [
      { key: "provider_needs_service_area", label: "Provider Needs Service Area" },
      { key: "provider_needs_pricing", label: "Provider Needs Pricing" },
      { key: "provider_needs_staff", label: "Provider Needs Staff" },
    ] : [];
    const allRules = [...baseRules, ...hsRules];
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {allRules.map(rule => (
          <label key={rule.key} style={{
            display: "flex", alignItems: "center", gap: 10, cursor: "pointer",
            background: "var(--surface-sunken)", padding: "10px 14px",
            borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
            fontSize: 13, color: "var(--text-primary)",
          }}>
            <input type="checkbox"
              checked={wiz.rules[rule.key] ?? false}
              onChange={e => update({ rules: { ...wiz.rules, [rule.key]: e.target.checked } })} />
            {rule.label}
          </label>
        ))}
      </div>
    );
  }

  // ── Step 7 ────────────────────────────────────────────────────────────────

  function renderStep7() {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <label style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
          <input type="checkbox" checked={wiz.pricing.enabled}
            onChange={e => update({ pricing: { ...wiz.pricing, enabled: e.target.checked } })} />
          Create Pricing Defaults
        </label>
        {wiz.pricing.enabled && (
          <>
            <div>
              <label style={labelStyle}>Pricing Model</label>
              <select style={inputStyle} value={wiz.pricing.model}
                onChange={e => update({ pricing: { ...wiz.pricing, model: e.target.value } })}>
                <option value="fixed">Fixed</option>
                <option value="range">Range</option>
                <option value="bargain">Bargain</option>
                <option value="platform_controlled">Platform Controlled</option>
              </select>
            </div>
            <label style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
              <input type="checkbox" checked={wiz.pricing.city_zip_mapping}
                onChange={e => update({ pricing: { ...wiz.pricing, city_zip_mapping: e.target.checked } })} />
              Enable City/ZIP Mapping
            </label>
          </>
        )}
      </div>
    );
  }

  // ── Step 8 ────────────────────────────────────────────────────────────────

  async function loadPreview() {
    if (wiz.draftId) {
      const res = await bulkWizardApi.previewDraft(wiz.draftId);
      setPreviewItems(res.items as unknown[]);
      setPreviewSummary(res.summary);
    } else {
      // local preview
      const items: unknown[] = [];
      for (const [mk, mItems] of Object.entries(wiz.content)) {
        for (const it of mItems) {
          if (it.name) items.push({ module_key: mk, record_name: it.name, record_code: it.code, action: "create" });
        }
      }
      setPreviewItems(items);
      setPreviewSummary({ create: items.length });
    }
  }

  function renderStep8() {
    const actionColor = (action: string) => {
      if (action === "create") return "var(--success-text)";
      if (action === "update") return "var(--accent)";
      if (action === "skip") return "var(--text-tertiary)";
      return "var(--danger-text)";
    };
    return (
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", gap: 12 }}>
            {Object.entries(previewSummary).map(([k, v]) => (
              <span key={k} style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                <strong>{v}</strong> {k}
              </span>
            ))}
          </div>
          <Btn size="sm" variant="ghost" onClick={loadPreview}>Refresh Preview</Btn>
        </div>
        {previewItems.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-tertiary)", padding: 24 }}>
            Click "Refresh Preview" to generate preview from current configuration.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Module", "Name", "Code", "Action"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "6px 10px", color: "var(--text-secondary)", fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(previewItems as Array<Record<string, string>>).map((item, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "6px 10px", color: "var(--text-secondary)" }}>{item.module_key}</td>
                    <td style={{ padding: "6px 10px", color: "var(--text-primary)" }}>{item.record_name}</td>
                    <td style={{ padding: "6px 10px", fontFamily: "monospace", color: "var(--text-tertiary)" }}>{item.record_code}</td>
                    <td style={{ padding: "6px 10px", color: actionColor(item.action), fontWeight: 600 }}>{item.action}</td>
                  </tr>
                ))}
              </tbody>
            </TableSurface>
          </div>
        )}
      </div>
    );
  }

  // ── Step 9 ────────────────────────────────────────────────────────────────

  async function runValidation() {
    if (!wiz.draftId) {
      alert("Save draft first (go back to step 1 and save).");
      return;
    }
    const res = await bulkWizardApi.validateDraft(wiz.draftId);
    setValidateResult(res);
  }

  function renderStep9() {
    return (
      <div>
        <Btn variant="primary" onClick={runValidation} style={{ marginBottom: 16 }}>Run Validation</Btn>
        {validateResult && (
          <div>
            <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
              <span style={{ color: "var(--success-text)", fontSize: 13 }}>
                {validateResult.valid ? "✓ Validation Passed" : "✗ Has Blocking Errors"}
              </span>
              <span style={{ color: "var(--warning-text)", fontSize: 13 }}>
                {(validateResult.warnings as unknown[]).length} warnings
              </span>
              <span style={{ color: "var(--danger-text)", fontSize: 13 }}>
                {validateResult.blocking_count} blocking errors
              </span>
            </div>
            {(validateResult.errors as Array<{ message: string; module_key?: string; blocking?: boolean }>).map((e, i) => (
              <div key={i} style={{
                background: "var(--danger-bg)", color: "var(--danger-text)",
                border: "1px solid var(--danger-border)", borderRadius: 6,
                padding: "8px 12px", marginBottom: 8, fontSize: 13,
              }}>
                {e.module_key && <strong>[{e.module_key}] </strong>}{e.message}
              </div>
            ))}
            {(validateResult.warnings as Array<{ message: string; module_key?: string }>).map((w, i) => (
              <div key={i} style={{
                background: "var(--warning-bg)", color: "var(--warning-text)",
                border: "1px solid var(--warning-border)", borderRadius: 6,
                padding: "8px 12px", marginBottom: 8, fontSize: 13,
              }}>
                {w.module_key && <strong>[{w.module_key}] </strong>}{w.message}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Step 10 ───────────────────────────────────────────────────────────────

  async function handleDryRun() {
    if (!wiz.draftId) { alert("Save draft first."); return; }
    setExecuting(true);
    try {
      const res = await bulkWizardApi.dryRun(wiz.draftId);
      setRunResult(res);
    } finally {
      setExecuting(false);
    }
  }

  async function handleExecute() {
    if (!wiz.draftId) { alert("Save draft first."); return; }
    if (!executeReason.trim()) { alert("Execution reason is required."); return; }
    if (!executeConfirm) { alert("Please confirm you understand the action."); return; }
    setExecuting(true);
    try {
      const res = await bulkWizardApi.executeDraft(wiz.draftId, executeReason);
      setRunResult(res);
      onSaved();
    } finally {
      setExecuting(false);
    }
  }

  function renderStep10() {
    const totalItems = Object.values(wiz.content).reduce((acc, arr) => acc + arr.filter(i => i.name).length, 0);
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 16, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>Execution Summary</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{totalItems} items</div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>configured across {wiz.modules.length} modules</div>
        </div>
        <div>
          <label style={labelStyle}>Execution Reason *</label>
          <textarea style={{ ...inputStyle, minHeight: 70, resize: "vertical" }}
            value={executeReason} onChange={e => setExecuteReason(e.target.value)}
            placeholder="Describe why you are running this bulk setup..." />
        </div>
        <label style={{ display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer", fontSize: 13, color: "var(--text-primary)" }}>
          <input type="checkbox" checked={executeConfirm} onChange={e => setExecuteConfirm(e.target.checked)} style={{ marginTop: 2 }} />
          I understand this will create/update platform catalog records and the action cannot be easily undone.
        </label>
        {runResult && (
          <div style={{ background: "var(--success-bg)", color: "var(--success-text)", borderRadius:"var(--radius-md)", padding: 12, border: "1px solid var(--success-border)", fontSize: 13 }}>
            Run completed successfully!
          </div>
        )}
        <div style={{ display: "flex", gap: 12 }}>
          <Btn variant="secondary" onClick={handleDryRun} disabled={executing}>
            {executing ? "Running..." : "Dry Run"}
          </Btn>
          <Btn variant="primary" onClick={handleExecute} disabled={executing || !executeConfirm || !executeReason.trim()}>
            {executing ? "Executing..." : "Execute Now"}
          </Btn>
        </div>
      </div>
    );
  }

  // ── Save draft ────────────────────────────────────────────────────────────

  async function saveDraft() {
    setSaving(true);
    try {
      const payload = {
        name: wiz.name,
        description: wiz.description,
        vertical_key: wiz.vertical,
        setup_mode: wiz.setup_mode,
        template_id: wiz.template_id,
        current_step: wiz.step,
        config_json: {
          scope: wiz.scope,
          modules: wiz.modules,
          content: wiz.content,
          rules: wiz.rules,
          pricing: wiz.pricing,
        },
      };
      if (wiz.draftId) {
        await bulkWizardApi.updateDraft(wiz.draftId, payload);
      } else {
        const res = await bulkWizardApi.createDraft(payload);
        update({ draftId: res.id, code: res.draft_code });
      }
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  const stepRenderers = [
    null, renderStep1, renderStep2, renderStep3, renderStep4,
    renderStep5, renderStep6, renderStep7, renderStep8, renderStep9, renderStep10,
  ];

  return (
    <Modal open={open} onClose={onClose} size="xl" title="Bulk Setup Wizard">
      {/* Step indicator */}
      <div style={{ display: "flex", gap: 0, marginBottom: 24, overflowX: "auto", paddingBottom: 4 }}>
        {STEP_LABELS.slice(1).map((label, i) => {
          const stepNum = i + 1;
          const isActive = wiz.step === stepNum;
          const isDone = wiz.step > stepNum;
          return (
            <div key={stepNum} style={{ display: "flex", alignItems: "center" }}>
              <div
                onClick={() => setWiz(w => ({ ...w, step: stepNum }))}
                style={{
                  cursor: "pointer",
                  padding: "4px 10px",
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: isActive ? 700 : 400,
                  background: isActive ? "var(--accent)" : isDone ? "var(--success-bg)" : "var(--surface-sunken)",
                  color: isActive ? "var(--text-on-brand)" : isDone ? "var(--success-text)" : "var(--text-tertiary)",
                  border: `1px solid ${isActive ? "var(--accent)" : "var(--border)"}`,
                  whiteSpace: "nowrap",
                }}
              >
                {stepNum}. {label}
              </div>
              {i < 9 && <div style={{ width: 8, height: 1, background: "var(--border)" }} />}
            </div>
          );
        })}
      </div>

      {/* Step content */}
      <div style={{ minHeight: 300, padding: "4px 0" }}>
        {stepRenderers[wiz.step]?.()}
      </div>

      {/* Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" size="sm" disabled={wiz.step <= 1} onClick={() => setWiz(w => ({ ...w, step: w.step - 1 }))}>
            ← Back
          </Btn>
          <Btn variant="ghost" size="sm" onClick={saveDraft} disabled={saving}>
            {saving ? "Saving..." : "Save Draft"}
          </Btn>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          Step {wiz.step} / 10
        </div>
        <Btn variant="primary" size="sm" disabled={wiz.step >= 10} onClick={() => setWiz(w => ({ ...w, step: w.step + 1 }))}>
          Next →
        </Btn>
      </div>
    </Modal>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function BulkWizardPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [verticalFilter, setVerticalFilter] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [view, setView] = useState<"drafts" | "runs">("drafts");
  const [wizOpen, setWizOpen] = useState(false);
  const [editDraft, setEditDraft] = useState<BulkDraftItem | null>(null);

  const draftsKey = JSON.stringify({ statusFilter, verticalFilter, searchQ });
  const { data: draftsData, loading: draftsLoading, refetch: refetchDrafts } = useApi(
    () => bulkWizardApi.list({ status: statusFilter || undefined, vertical: verticalFilter || undefined, q: searchQ || undefined }),
    [draftsKey],
  );

  const { data: summaryData } = useApi(() => bulkWizardApi.getSummary(), []);
  const summary = summaryData as BulkWizardSummary | null;

  const { data: runsData, loading: runsLoading } = useApi(
    () => bulkWizardApi.listRuns({}),
    [view],
  );

  const deleteAction = useAction(async (id: string) => {
    await bulkWizardApi.deleteDraft(id);
    refetchDrafts();
  });

  const drafts = (draftsData as { items: BulkDraftItem[]; total: number } | null)?.items ?? [];
  const runsItems = (runsData as { items: unknown[]; total: number } | null)?.items ?? [];

  function openWizard(draft?: BulkDraftItem) {
    setEditDraft(draft ?? null);
    setWizOpen(true);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      {/* Header */}
      <PageHeader
        title="Bulk Setup Wizard"
        description="Launch complete service verticals with guided multi-step configuration."
        eyebrow="Service Setup"
        actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)", flexWrap: "wrap" }}>
          <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/service-setup/bulk-runs")}>
            View Runs
          </Btn>
          <Btn variant="secondary" size="sm" onClick={() => { /* seed from template */ }}>
            Seed From Template
          </Btn>
          <Btn variant="ghost" size="sm" onClick={() => refetchDrafts()}>Refresh</Btn>
          <Btn variant="primary" size="sm" onClick={() => openWizard()}>+ New Bulk Setup</Btn>
        </div>}
      />

      {/* Summary cards */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <SummaryCard label="Total Drafts" value={summary?.total_drafts ?? 0} />
        <SummaryCard label="Ready To Run" value={summary?.ready_to_run ?? 0} accent />
        <SummaryCard label="Running" value={summary?.running ?? 0} />
        <SummaryCard label="Completed Runs" value={summary?.completed_runs ?? 0} />
        <SummaryCard label="Failed Runs" value={summary?.failed_runs ?? 0} />
        <SummaryCard label="Rollback Available" value={summary?.rollback_available ?? 0} />
      </div>

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
        <select style={{ ...inputStyle, width: "auto" }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {["draft", "ready_to_run", "running", "completed", "failed", "validation_failed", "archived"].map(s => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select style={{ ...inputStyle, width: "auto" }} value={verticalFilter} onChange={e => setVerticalFilter(e.target.value)}>
          <option value="">All Verticals</option>
          {VERTICALS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
        </select>
        <input style={{ ...inputStyle, width: 220 }} placeholder="Search drafts..." value={searchQ} onChange={e => setSearchQ(e.target.value)} />
        <div style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
          <Btn variant={view === "drafts" ? "primary" : "ghost"} size="sm" onClick={() => setView("drafts")}>Drafts</Btn>
          <Btn variant={view === "runs" ? "primary" : "ghost"} size="sm" onClick={() => setView("runs")}>Runs</Btn>
        </div>
      </div>

      {/* Drafts table */}
      {view === "drafts" && (
        draftsLoading ? (
          <div style={{ color: "var(--text-secondary)", padding: 24 }}>Loading...</div>
        ) : drafts.length === 0 ? (
          <div style={{
            textAlign: "center", padding: "4rem 2rem",
            background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)",
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
              No bulk setup drafts yet.
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 20 }}>
              Create a new bulk setup to configure an entire service vertical in one go.
            </div>
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <Btn variant="primary" onClick={() => openWizard()}>New Bulk Setup</Btn>
              <Btn variant="secondary" onClick={() => { /* seed from template */ }}>Seed From Template</Btn>
            </div>
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", overflowX: "auto" }}>
            <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Name / Code", "Vertical", "Template", "Status", "Step", "Updated", "Actions"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "10px 14px", color: "var(--text-secondary)", fontWeight: 600, fontSize: 11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {drafts.map(d => (
                  <tr key={d.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{d.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{d.draft_code}</div>
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{d.vertical_key}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-tertiary)", fontSize: 11, fontFamily: "monospace" }}>
                      {d.template_id ? d.template_id.slice(0, 8) + "…" : "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}><StatusBadge status={d.status} /></td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{d.current_step} / 10</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-tertiary)", fontSize: 11 }}>
                      {d.updated_at ? new Date(d.updated_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <Btn size="xs" variant="primary" onClick={() => openWizard(d)}>Continue</Btn>
                        <Btn size="xs" variant="ghost" onClick={async () => {
                          await bulkWizardApi.validateDraft(d.id);
                          refetchDrafts();
                        }}>Validate</Btn>
                        <Btn size="xs" variant="secondary" onClick={async () => {
                          await bulkWizardApi.cloneDraft(d.id);
                          refetchDrafts();
                        }}>Clone</Btn>
                        <Btn size="xs" variant="danger" onClick={() => deleteAction.execute(d.id)}>Delete</Btn>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSurface>
          </div>
        )
      )}

      {/* Runs table */}
      {view === "runs" && (
        runsLoading ? (
          <div style={{ color: "var(--text-secondary)", padding: 24 }}>Loading runs...</div>
        ) : runsItems.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3rem", color: "var(--text-tertiary)" }}>
            No runs yet. Execute a draft to create a run.
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", overflowX: "auto" }}>
            <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Run Code", "Vertical", "Status", "Created", "Skipped", "Failed", "Dry Run", "Started At"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "10px 14px", color: "var(--text-secondary)", fontWeight: 600, fontSize: 11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(runsItems as Array<Record<string, unknown>>).map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px", fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{String(r.run_code)}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{String(r.vertical_key ?? "—")}</td>
                    <td style={{ padding: "10px 14px" }}><StatusBadge status={String(r.status)} /></td>
                    <td style={{ padding: "10px 14px", color: "var(--text-primary)" }}>{String(r.created_count ?? 0)}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{String(r.skipped_count ?? 0)}</td>
                    <td style={{ padding: "10px 14px", color: "var(--danger-text)" }}>{String(r.failed_count ?? 0)}</td>
                    <td style={{ padding: "10px 14px" }}>
                      {r.is_dry_run ? <span style={{ color: "var(--accent)", fontSize: 11 }}>DRY RUN</span> : <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>LIVE</span>}
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-tertiary)", fontSize: 11 }}>
                      {r.started_at ? new Date(String(r.started_at)).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSurface>
          </div>
        )
      )}

      {/* Wizard */}
      {wizOpen && (
        <WizardModal
          open={wizOpen}
          onClose={() => { setWizOpen(false); setEditDraft(null); }}
          onSaved={() => { refetchDrafts(); }}
          initialDraft={editDraft}
        />
      )}
    </div>
  );
}
