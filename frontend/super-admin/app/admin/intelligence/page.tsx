"use client";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select } from "../../../components/shared/ui";
import {
  intelligenceCmdApi, kbApi,
  type IntelligenceSummary, type RagKnowledgeBase, type RiskScore,
  type IntelAnomaly, type ModelRegistryItem, type PredictionJob,
  type DataQualityCheck, type KnowledgeBase, type KBSummary,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

// ── NaN Safety ───────────────────────────────────────────────────────────────
const safeNum = (v: unknown): number => {
  const n = Number(v);
  return isNaN(n) ? 0 : n;
};
const fmtMs = (v: unknown): string => {
  if (v === null || v === undefined) return "No queries yet";
  const n = Number(v);
  return isNaN(n) ? "No queries yet" : `${n}ms`;
};
const fmtNum = (v: unknown): string => safeNum(v).toLocaleString("en-IN");
const fmtCost = (v: unknown): string =>
  `₹${safeNum(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

// ── Tabs ─────────────────────────────────────────────────────────────────────
type TabId =
  | "overview" | "rag" | "events" | "risk" | "anomalies"
  | "models" | "prediction-jobs" | "data-quality" | "ai-usage" | "audit";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview",         label: "Overview" },
  { id: "rag",              label: "RAG & Knowledge Base" },
  { id: "events",           label: "Event Pipeline" },
  { id: "risk",             label: "Churn & Risk" },
  { id: "anomalies",        label: "Anomalies" },
  { id: "models",           label: "Models" },
  { id: "prediction-jobs",  label: "Prediction Jobs" },
  { id: "data-quality",     label: "Data Quality" },
  { id: "ai-usage",         label: "AI Cost & Usage" },
  { id: "audit",            label: "Audit Logs" },
];

// ── Sub-components ────────────────────────────────────────────────────────────
function KpiCard({
  label, value, helpText, loading,
}: { label: string; value: string | number; helpText?: string; loading?: boolean }) {
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius:"var(--radius-lg)", padding: "16px 20px",
    }}>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
        {label}
      </div>
      {loading
        ? <div className="skeleton" style={{ height: 28, width: 60, borderRadius: 4 }} />
        : <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>
            {value}
          </div>
      }
      {helpText && <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>{helpText}</div>}
    </div>
  );
}

function EmptyState({ msg, action }: { msg: string; action?: React.ReactNode }) {
  return (
    <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
      {msg}
      {action && <div style={{ marginTop: 12 }}>{action}</div>}
    </div>
  );
}

function SeverityBadge({ s }: { s: string }) {
  const v = s === "critical" ? "danger" : s === "high" ? "warning" : s === "medium" ? "accent" : "success";
  return <Badge variant={v as "danger"}>{s}</Badge>;
}

function RiskBadge({ level }: { level: string }) {
  const v = level === "critical" ? "danger" : level === "high" ? "warning" : level === "medium" ? "accent" : "muted";
  return <Badge variant={v as "danger"}>{level}</Badge>;
}

function StatusBadge({ status }: { status: string }) {
  const v = status === "running" ? "accent"
    : status === "completed" ? "success"
    : status === "failed" ? "danger"
    : status === "open" ? "warning"
    : status === "resolved" ? "success"
    : "muted";
  return <Badge variant={v as "danger"}>{status}</Badge>;
}

function TableHead({ cols }: { cols: string[] }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols.length}, 1fr)`, gap: 8, padding: "8px 16px", borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      {cols.map(c => (
        <div key={c} style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{c}</div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
// ── KB Wizard ─────────────────────────────────────────────────────────────────
const WIZARD_STEPS = [
  "Basic Details", "Scope & Ownership", "Access & Visibility",
  "Knowledge Sources", "RAG Configuration", "Safety & Guardrails",
  "Indexing Settings", "Review & Create",
];

type KBWizardForm = {
  // Step 1
  name: string; kb_code: string; description: string; status: string; icon: string; tags: string;
  // Step 2
  scope_type: string; vertical_key: string; tenant_id: string; owner_team: string; environment: string; approval_required: boolean;
  // Step 3
  customer_visible: boolean; tenant_visible: boolean; staff_visible: boolean; admin_only: boolean; sensitive_content: boolean;
  allowed_apps_json: string[]; allowed_roles_json: string[];
  // Step 4
  knowledge_type: string; data_sources_json: string[];
  // Step 5
  rag_enabled: boolean; embedding_model: string; chunk_size: number; chunk_overlap: number;
  retrieval_top_k: number; similarity_threshold: number; reranking_enabled: boolean;
  citations_required: boolean; max_context_documents: number; fallback_message: string;
  // Step 6 — safety rules stored as safety_rules_json
  safety_rules_json: Record<string, boolean>;
  // Step 7
  index_immediately: boolean; auto_reindex: boolean; reindex_schedule: string; index_priority: string;
  document_retention_policy: string; archive_old_versions: boolean;
};

const defaultWizardForm = (): KBWizardForm => ({
  name: "", kb_code: "", description: "", status: "draft", icon: "", tags: "",
  scope_type: "platform", vertical_key: "", tenant_id: "", owner_team: "platform", environment: "all", approval_required: false,
  customer_visible: false, tenant_visible: false, staff_visible: false, admin_only: true, sensitive_content: false,
  allowed_apps_json: [], allowed_roles_json: [],
  knowledge_type: "faq", data_sources_json: [],
  rag_enabled: true, embedding_model: "default_platform_embedding", chunk_size: 800, chunk_overlap: 120,
  retrieval_top_k: 5, similarity_threshold: 0.72, reranking_enabled: false,
  citations_required: true, max_context_documents: 5, fallback_message: "",
  safety_rules_json: {
    ai_can_answer: true, ai_must_cite: true, ai_can_answer_customer: false,
    ai_can_answer_admin: true, block_internal_from_customer: true,
    block_tenant_private: true, allow_summarization: true,
    allow_extraction: false, allow_marketing_reuse: false, human_review_for_sensitive: false,
  },
  index_immediately: false, auto_reindex: false, reindex_schedule: "manual_only",
  index_priority: "normal", document_retention_policy: "keep_all", archive_old_versions: true,
});

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 40, height: 22, borderRadius: 11, cursor: "pointer",
          background: checked ? "var(--brand)" : "var(--border)",
          position: "relative", transition: "background 0.2s",
        }}
      >
        <div style={{
          position: "absolute", top: 3, left: checked ? 20 : 3,
          width: 16, height: 16, borderRadius:"var(--radius-md)",
          background: "var(--white, white)", transition: "left 0.2s",
        }} />
      </div>
      <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{label}</span>
    </div>
  );
}

function CheckBox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: "var(--text-primary)", marginBottom: 6 }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} style={{ accentColor: "var(--brand)" }} />
      {label}
    </label>
  );
}

function WizardStep1({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Input label="Name *" value={form.name} onChange={v => setForm(p => ({
        ...p, name: v,
        kb_code: p.kb_code || v.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""),
      }))} placeholder="Home Services FAQ" />
      <Input label="KB Code *" value={form.kb_code} onChange={v => setForm(p => ({ ...p, kb_code: v.toLowerCase().replace(/[^a-z0-9_]/g, "") }))} placeholder="home_services_faq" />
      <div>
        <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Description *</label>
        <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} rows={3}
          style={{ width: "100%", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)", resize: "vertical", boxSizing: "border-box" }}
          placeholder="Describe what this knowledge base contains…" />
      </div>
      <Select label="Initial Status" value={form.status} onChange={v => setForm(p => ({ ...p, status: v }))}
        options={[{ value: "draft", label: "Draft" }, { value: "active", label: "Active" }]} />
      <Input label="Icon (emoji or text)" value={form.icon} onChange={v => setForm(p => ({ ...p, icon: v }))} placeholder="📚" />
      <Input label="Tags (comma-separated)" value={form.tags} onChange={v => setForm(p => ({ ...p, tags: v }))} placeholder="faq, home, services" />
    </div>
  );
}

function WizardStep2({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Select label="Scope Type *" value={form.scope_type} onChange={v => setForm(p => ({ ...p, scope_type: v }))}
        options={[
          { value: "platform", label: "Platform" }, { value: "vertical", label: "Vertical" },
          { value: "category", label: "Category" }, { value: "tenant", label: "Tenant" },
          { value: "support", label: "Support" }, { value: "compliance", label: "Compliance" },
          { value: "marketing", label: "Marketing" },
        ]} />
      {(form.scope_type === "vertical" || form.scope_type === "category") && (
        <Input label="Vertical Key" value={form.vertical_key} onChange={v => setForm(p => ({ ...p, vertical_key: v }))} placeholder="home_services" />
      )}
      {form.scope_type === "tenant" && (
        <Input label="Tenant ID (leave blank for template)" value={form.tenant_id} onChange={v => setForm(p => ({ ...p, tenant_id: v }))} placeholder="UUID or leave blank" />
      )}
      <Input label="Owner Team *" value={form.owner_team} onChange={v => setForm(p => ({ ...p, owner_team: v }))} placeholder="platform" />
      <Select label="Environment" value={form.environment} onChange={v => setForm(p => ({ ...p, environment: v }))}
        options={[{ value: "all", label: "All" }, { value: "production", label: "Production" }, { value: "staging", label: "Staging" }]} />
      <Toggle label="Approval Required" checked={form.approval_required} onChange={v => setForm(p => ({ ...p, approval_required: v }))} />
    </div>
  );
}

const ALL_APPS = ["admin_app", "tenant_app", "staff_app", "customer_app", "marketing_engine", "support_console"];
const ALL_ROLES = ["super_admin", "admin", "compliance_officer", "support_agent", "tenant_owner", "technician", "customer"];

function WizardStep3({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  const toggleApp = (app: string) => setForm(p => ({
    ...p, allowed_apps_json: p.allowed_apps_json.includes(app)
      ? p.allowed_apps_json.filter(a => a !== app)
      : [...p.allowed_apps_json, app],
  }));
  const toggleRole = (role: string) => setForm(p => ({
    ...p, allowed_roles_json: p.allowed_roles_json.includes(role)
      ? p.allowed_roles_json.filter(r => r !== role)
      : [...p.allowed_roles_json, role],
  }));
  const isCompliance = form.scope_type === "compliance";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>Allowed Apps</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
          {ALL_APPS.map(app => (
            <CheckBox key={app} label={app} checked={form.allowed_apps_json.includes(app)} onChange={() => toggleApp(app)} />
          ))}
        </div>
      </div>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>Allowed Roles</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
          {ALL_ROLES.map(role => (
            <CheckBox key={role} label={role} checked={form.allowed_roles_json.includes(role)} onChange={() => toggleRole(role)} />
          ))}
        </div>
      </div>
      <Toggle label="Customer Visible" checked={form.customer_visible && !isCompliance && !form.sensitive_content}
        onChange={v => setForm(p => ({ ...p, customer_visible: v && !isCompliance && !p.sensitive_content }))} />
      {isCompliance && <div style={{ fontSize: 11, color: "var(--danger-text)", background: "var(--danger-bg)", borderRadius: 6, padding: "6px 10px" }}>Compliance KBs cannot be customer-visible</div>}
      <Toggle label="Tenant Visible" checked={form.tenant_visible} onChange={v => setForm(p => ({ ...p, tenant_visible: v }))} />
      <Toggle label="Staff Visible" checked={form.staff_visible} onChange={v => setForm(p => ({ ...p, staff_visible: v }))} />
      <Toggle label="Admin Only" checked={form.admin_only} onChange={v => setForm(p => ({ ...p, admin_only: v }))} />
      <Toggle label="Sensitive Content" checked={form.sensitive_content}
        onChange={v => setForm(p => ({ ...p, sensitive_content: v, customer_visible: v ? false : p.customer_visible }))} />
    </div>
  );
}

function WizardStep4({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Select label="Knowledge Type" value={form.knowledge_type} onChange={v => setForm(p => ({ ...p, knowledge_type: v }))}
        options={[
          { value: "faq", label: "FAQ" }, { value: "policy", label: "Policy" },
          { value: "support", label: "Support" }, { value: "onboarding", label: "Onboarding" },
          { value: "compliance", label: "Compliance" }, { value: "marketing", label: "Marketing" },
        ]} />
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>Data Sources</div>
        {["uploaded_documents", "manual_articles", "external_url", "database_query", "api_feed"].map(src => (
          <CheckBox key={src} label={src.replace(/_/g, " ")}
            checked={(form.data_sources_json ?? []).includes(src)}
            onChange={v => setForm(p => ({
              ...p, data_sources_json: v
                ? [...(p.data_sources_json ?? []), src]
                : (p.data_sources_json ?? []).filter(s => s !== src),
            }))} />
        ))}
      </div>
    </div>
  );
}

function WizardStep5({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Toggle label="Enable RAG" checked={form.rag_enabled} onChange={v => setForm(p => ({ ...p, rag_enabled: v }))} />
      <Select label="Embedding Model" value={form.embedding_model} onChange={v => setForm(p => ({ ...p, embedding_model: v }))}
        options={[
          { value: "default_platform_embedding", label: "Default Platform Embedding" },
          { value: "text-embedding-3-small", label: "text-embedding-3-small" },
          { value: "text-embedding-3-large", label: "text-embedding-3-large" },
        ]} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Chunk Size</label>
          <input type="number" value={form.chunk_size} onChange={e => setForm(p => ({ ...p, chunk_size: parseInt(e.target.value) || 800 }))}
            style={{ width: "100%", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)", boxSizing: "border-box" }} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Chunk Overlap</label>
          <input type="number" value={form.chunk_overlap} onChange={e => setForm(p => ({ ...p, chunk_overlap: parseInt(e.target.value) || 120 }))}
            style={{ width: "100%", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)", boxSizing: "border-box" }} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Retrieval Top K</label>
          <input type="number" value={form.retrieval_top_k} onChange={e => setForm(p => ({ ...p, retrieval_top_k: parseInt(e.target.value) || 5 }))}
            style={{ width: "100%", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)", boxSizing: "border-box" }} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Similarity Threshold (0–1)</label>
          <input type="number" step="0.01" min="0" max="1" value={form.similarity_threshold}
            onChange={e => setForm(p => ({ ...p, similarity_threshold: parseFloat(e.target.value) || 0.72 }))}
            style={{ width: "100%", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)", boxSizing: "border-box" }} />
        </div>
      </div>
      <Toggle label="Reranking Enabled" checked={form.reranking_enabled} onChange={v => setForm(p => ({ ...p, reranking_enabled: v }))} />
      <Toggle label="Citations Required" checked={form.citations_required} onChange={v => setForm(p => ({ ...p, citations_required: v }))} />
      <div>
        <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Fallback Message</label>
        <textarea value={form.fallback_message} onChange={e => setForm(p => ({ ...p, fallback_message: e.target.value }))} rows={2}
          style={{ width: "100%", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)", resize: "vertical", boxSizing: "border-box" }}
          placeholder="I'm sorry, I couldn't find an answer to your question." />
      </div>
    </div>
  );
}

function WizardStep6({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  const toggleRule = (key: string) => setForm(p => ({
    ...p, safety_rules_json: { ...p.safety_rules_json, [key]: !p.safety_rules_json[key] },
  }));
  const MANDATORY_BLOCKS = [
    "AI cannot decide price.", "AI cannot assign provider.",
    "AI cannot create booking by itself.", "AI cannot apply ServiceOS credit.",
    "AI cannot approve tenant.", "AI cannot change security deposit.",
    "AI cannot expose internal risk score to customer.",
    "AI cannot expose tenant private documents to other tenants.",
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ background: "var(--brand-bg, var(--surface-sunken))", border: "2px solid var(--brand)", borderRadius: 10, padding: "12px 16px" }}>
        <div style={{ fontSize: 15, fontWeight: 800, color: "var(--brand)", marginBottom: 4 }}>AI can explain. Backend decides.</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>All KB AI responses are informational only. Decisions, payments, and assignments are always executed by the backend engine — never by the AI.</div>
      </div>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>AI Capabilities for this KB</div>
        {[
          ["ai_can_answer", "AI Can Answer From This KB"],
          ["ai_must_cite", "AI Must Cite Source"],
          ["ai_can_answer_customer", "AI Can Answer Customer Questions"],
          ["ai_can_answer_admin", "AI Can Answer Admin Questions"],
          ["block_internal_from_customer", "Block Internal Content From Customer"],
          ["block_tenant_private", "Block Tenant Private Data From Other Tenants"],
          ["allow_summarization", "Allow Summarization"],
          ["allow_extraction", "Allow Document Extraction"],
          ["allow_marketing_reuse", "Allow Marketing Reuse"],
          ["human_review_for_sensitive", "Human Review Required For Sensitive Answers"],
        ].map(([key, label]) => (
          <Toggle key={key} label={label} checked={!!form.safety_rules_json[key]} onChange={() => toggleRule(key)} />
        ))}
      </div>
      <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: "12px 16px" }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>Mandatory Guardrails (always enforced)</div>
        {MANDATORY_BLOCKS.map(rule => (
          <div key={rule} style={{ fontSize: 11, color: "var(--text-secondary)", padding: "3px 0", borderBottom: "1px solid var(--border)" }}>{rule}</div>
        ))}
      </div>
    </div>
  );
}

function WizardStep7({ form, setForm }: { form: KBWizardForm; setForm: React.Dispatch<React.SetStateAction<KBWizardForm>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Toggle label="Index Immediately After Create" checked={form.index_immediately} onChange={v => setForm(p => ({ ...p, index_immediately: v }))} />
      <Toggle label="Auto Reindex" checked={form.auto_reindex} onChange={v => setForm(p => ({ ...p, auto_reindex: v }))} />
      <Select label="Reindex Schedule" value={form.reindex_schedule} onChange={v => setForm(p => ({ ...p, reindex_schedule: v }))}
        options={[
          { value: "manual_only", label: "Manual Only" }, { value: "hourly", label: "Hourly" },
          { value: "daily", label: "Daily" }, { value: "weekly", label: "Weekly" },
          { value: "monthly", label: "Monthly" }, { value: "on_document_change", label: "On Document Change" },
        ]} />
      <Select label="Index Priority" value={form.index_priority} onChange={v => setForm(p => ({ ...p, index_priority: v }))}
        options={[
          { value: "low", label: "Low" }, { value: "normal", label: "Normal" },
          { value: "high", label: "High" }, { value: "critical", label: "Critical" },
        ]} />
      <Select label="Document Retention Policy" value={form.document_retention_policy} onChange={v => setForm(p => ({ ...p, document_retention_policy: v }))}
        options={[
          { value: "keep_all", label: "Keep All" }, { value: "last_30_days", label: "Last 30 Days" },
          { value: "last_90_days", label: "Last 90 Days" }, { value: "last_version_only", label: "Last Version Only" },
        ]} />
      <Toggle label="Archive Old Versions" checked={form.archive_old_versions} onChange={v => setForm(p => ({ ...p, archive_old_versions: v }))} />
    </div>
  );
}

function WizardStep8({ form }: { form: KBWizardForm }) {
  const warnings: string[] = [];
  const errors: string[] = [];

  if (form.customer_visible && form.sensitive_content) warnings.push("Customer Visible + Sensitive Content: customers may see sensitive data.");
  if (form.scope_type === "tenant" && !form.tenant_id) warnings.push("Scope is tenant but no tenant ID provided (template mode).");
  if (form.rag_enabled && (form.data_sources_json ?? []).length === 0) warnings.push("RAG enabled but no data sources configured.");
  if (form.chunk_overlap >= form.chunk_size) errors.push("chunk_overlap must be less than chunk_size.");
  if (form.scope_type === "compliance" && form.customer_visible) errors.push("Compliance KB cannot be customer_visible.");
  if (!form.name) errors.push("Name is required.");
  if (!form.kb_code) errors.push("KB Code is required.");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: "var(--text-primary)" }}>Review Summary</div>
        {[
          ["Name", form.name || "—"], ["KB Code", form.kb_code || "—"],
          ["Scope", form.scope_type], ["Knowledge Type", form.knowledge_type],
          ["Status", form.status], ["Owner Team", form.owner_team],
          ["Customer Visible", form.customer_visible ? "Yes" : "No"],
          ["Admin Only", form.admin_only ? "Yes" : "No"],
          ["RAG Enabled", form.rag_enabled ? "Yes" : "No"],
          ["Chunk Size / Overlap", `${form.chunk_size} / ${form.chunk_overlap}`],
          ["Similarity Threshold", String(form.similarity_threshold)],
          ["Auto Reindex", form.auto_reindex ? "Yes" : "No"],
        ].map(([label, val]) => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>{label}</span>
            <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{val}</span>
          </div>
        ))}
      </div>
      {errors.length > 0 && (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--danger-text)", marginBottom: 6 }}>Errors (must fix)</div>
          {errors.map(e => <div key={e} style={{ fontSize: 11, color: "var(--danger-text)" }}>• {e}</div>)}
        </div>
      )}
      {warnings.length > 0 && (
        <div style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--warning-text)", marginBottom: 6 }}>Warnings</div>
          {warnings.map(w => <div key={w} style={{ fontSize: 11, color: "var(--warning-text)" }}>• {w}</div>)}
        </div>
      )}
    </div>
  );
}

function KBWizardModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<KBWizardForm>(defaultWizardForm());
  const [toast, setToast] = useState("");
  const [createError, setCreateError] = useState("");

  const doCreate = async (indexAfter = false) => {
    setCreateError("");
    // Frontend validation
    if (!form.name.trim()) { setCreateError("Name is required."); return; }
    if (!form.kb_code.trim()) { setCreateError("KB Code is required."); return; }
    if (!form.description.trim()) { setCreateError("Description is required."); return; }

    const payload = {
      ...form,
      kb_code: form.kb_code.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_"),
      index_immediately: indexAfter,
      tags_json: form.tags ? form.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
    };
    try {
      const created = await kbApi.create(payload);
      if (!created) { setCreateError("Failed to create KB. Check required fields."); return; }
      setToast("Knowledge base created!");
      setTimeout(() => { setToast(""); onCreated(); onClose(); setForm(defaultWizardForm()); setStep(0); }, 1500);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create knowledge base.";
      setCreateError(msg);
    }
  };

  if (!open) return null;

  const stepComponents = [
    <WizardStep1 key="1" form={form} setForm={setForm} />,
    <WizardStep2 key="2" form={form} setForm={setForm} />,
    <WizardStep3 key="3" form={form} setForm={setForm} />,
    <WizardStep4 key="4" form={form} setForm={setForm} />,
    <WizardStep5 key="5" form={form} setForm={setForm} />,
    <WizardStep6 key="6" form={form} setForm={setForm} />,
    <WizardStep7 key="7" form={form} setForm={setForm} />,
    <WizardStep8 key="8" form={form} />,
  ];

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "var(--surface)", borderRadius:"var(--radius-xl, 1rem)", width: "min(92vw, 680px)",
        maxHeight: "90vh", display: "flex", flexDirection: "column", overflow: "hidden",
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
      }}>
        {/* Header */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>Create Knowledge Base</div>
            <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>Step {step + 1} of {WIZARD_STEPS.length}: {WIZARD_STEPS[step]}</div>
          </div>
          <Btn variant="ghost" size="sm" onClick={onClose}>✕</Btn>
        </div>

        {/* Step indicators */}
        <div style={{ display: "flex", padding: "10px 20px", gap: 6, background: "var(--surface-sunken)", overflowX: "auto" }}>
          {WIZARD_STEPS.map((s, i) => (
            <div key={s} onClick={() => setStep(i)}
              style={{
                padding: "4px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, cursor: "pointer",
                whiteSpace: "nowrap",
                background: i === step ? "var(--brand)" : i < step ? "var(--success-bg)" : "var(--border)",
                color: i === step ? "white" : i < step ? "var(--success-text)" : "var(--text-tertiary)",
              }}>
              {i + 1}. {s}
            </div>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: "20px", overflowY: "auto", flex: 1 }}>
          {toast && <div style={{ padding: "8px 12px", background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius:"var(--radius-md)", color: "var(--success-text)", fontSize: 12, marginBottom: 12 }}>✓ {toast}</div>}
          {createError && <div style={{ padding: "8px 12px", background: "var(--error-bg, #fee)", border: "1px solid var(--error-border, #f88)", borderRadius:"var(--radius-md)", color: "var(--error-text, #c00)", fontSize: 12, marginBottom: 12 }}>⚠ {createError}</div>}
          {stepComponents[step]}
        </div>

        {/* Footer */}
        <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--surface-sunken)" }}>
          <Btn variant="ghost" size="sm" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>← Back</Btn>
          <div style={{ display: "flex", gap: 8 }}>
            {step < WIZARD_STEPS.length - 1 ? (
              <Btn variant="primary" size="sm" onClick={() => { setCreateError(""); setStep(step + 1); }}>Next →</Btn>
            ) : (
              <>
                <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
                <Btn variant="secondary" size="sm" onClick={() => doCreate(false)}>Save Draft</Btn>
                <Btn variant="primary" size="sm" onClick={() => doCreate(false)}>Create KB</Btn>
                <Btn variant="success" size="sm" onClick={() => doCreate(true)}>Create & Index</Btn>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── RAG Tab ───────────────────────────────────────────────────────────────────
function RagTab({ onKBCreated }: { onKBCreated: () => void }) {
  const router = useRouter();
  const [showWizard, setShowWizard] = useState(false);
  const [filters, setFilters] = useState({ q: "", scope_type: "", status: "" });
  const [toast, setToast] = useState("");
  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const { data: kbSummary, loading: sumLoading } = useApi(() => kbApi.getSummary(), []);
  const { data: kbList, loading: kbLoading, refetch: refetchKBs } = useApi(() => {
    const params: Record<string, string> = {};
    if (filters.q) params.q = filters.q;
    if (filters.scope_type) params.scope_type = filters.scope_type;
    if (filters.status) params.status = filters.status;
    return kbApi.list(Object.keys(params).length ? params : undefined);
  }, [filters.q, filters.scope_type, filters.status]);

  const { execute: doActivate } = useAction(async (id: string) => { await kbApi.activate(id); refetchKBs(); notify("KB activated"); });
  const { execute: doDisable } = useAction(async (id: string) => { await kbApi.disable(id); refetchKBs(); notify("KB disabled"); });
  const { execute: doDelete } = useAction(async (id: string) => { if (!confirm("Delete this KB?")) return; await kbApi.delete(id); refetchKBs(); notify("KB deleted"); });
  const { execute: doSeed, loading: seeding, error: seedError } = useAction(async () => {
    const result = await kbApi.seedDefaults();
    refetchKBs();
    const r = result as { created?: number; skipped?: number } | null;
    notify(r ? `Seeded: ${r.created ?? 0} created, ${r.skipped ?? 0} skipped` : "Seed defaults applied");
  });

  const s = kbSummary as KBSummary | null;
  const kbs = (kbList as { items: KnowledgeBase[] } | null)?.items ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {toast && <div style={{ padding: "8px 14px", background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius:"var(--radius-md)", color: "var(--success-text)", fontSize: 12 }}>✓ {toast}</div>}
      {seedError && <div style={{ padding: "8px 14px", background: "var(--error-bg, #fee)", border: "1px solid var(--error-border, #f88)", borderRadius:"var(--radius-md)", color: "var(--error-text, #c00)", fontSize: 12 }}>⚠ Seed failed: {seedError}</div>}

      {/* Summary cards */}
      {s && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
          <KpiCard label="Total KBs" value={safeNum(s.total)} loading={sumLoading} />
          <KpiCard label="Active" value={safeNum(s.active)} loading={sumLoading} />
          <KpiCard label="Draft" value={safeNum(s.draft)} loading={sumLoading} />
          <KpiCard label="Indexed" value={safeNum(s.by_indexing_status?.indexed)} loading={sumLoading} helpText="fully indexed" />
          <KpiCard label="Not Indexed" value={safeNum(s.by_indexing_status?.not_indexed)} loading={sumLoading} />
        </div>
      )}

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input value={filters.q} onChange={e => setFilters(p => ({ ...p, q: e.target.value }))}
          placeholder="Search knowledge bases…"
          style={{ flex: 1, minWidth: 200, padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--text-primary)" }} />
        <Select label="" value={filters.scope_type} onChange={v => setFilters(p => ({ ...p, scope_type: v }))}
          options={[{ value: "", label: "All Scopes" }, { value: "platform", label: "Platform" }, { value: "vertical", label: "Vertical" }, { value: "compliance", label: "Compliance" }, { value: "support", label: "Support" }]} />
        <Select label="" value={filters.status} onChange={v => setFilters(p => ({ ...p, status: v }))}
          options={[{ value: "", label: "All Statuses" }, { value: "active", label: "Active" }, { value: "draft", label: "Draft" }, { value: "disabled", label: "Disabled" }]} />
        <Btn variant="secondary" size="sm" loading={seeding} onClick={() => doSeed()}>Seed Defaults</Btn>
        <Btn variant="primary" size="sm" onClick={() => setShowWizard(true)}>+ Create KB</Btn>
      </div>

      {/* KBs Table */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Knowledge Bases</h3>
        </div>
        {kbLoading ? (
          <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 200, borderRadius: 6 }} /></div>
        ) : kbs.length === 0 ? (
          <EmptyState msg="No knowledge bases found." action={<Btn variant="primary" size="sm" onClick={() => setShowWizard(true)}>Create Knowledge Base</Btn>} />
        ) : (
          <>
            <TableHead cols={["Name", "Code", "Scope", "Status", "Indexing", "Customer Visible", "RAG", "Created", "Actions"]} />
            {kbs.map((kb: KnowledgeBase) => (
              <div key={kb.id} style={{ display: "grid", gridTemplateColumns: "repeat(9, 1fr)", gap: 6, padding: "10px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                <div
                  style={{ fontSize: 13, fontWeight: 600, color: "var(--brand)", cursor: "pointer" }}
                  onClick={() => router.push(`/admin/intelligence/knowledge-bases/${kb.id}`)}
                >{kb.name}</div>
                <div style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-tertiary)" }}>{kb.kb_code ?? "—"}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{kb.scope_type}</div>
                <Badge variant={kb.status === "active" ? "success" : kb.status === "draft" ? "muted" : "warning"} size="sm">{kb.status}</Badge>
                <Badge variant={kb.indexing_status === "indexed" ? "success" : "muted"} size="sm">{kb.indexing_status}</Badge>
                <div style={{ fontSize: 11 }}>{kb.customer_visible ? "Yes" : "No"}</div>
                <div style={{ fontSize: 11 }}>{kb.rag_enabled ? "On" : "Off"}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{kb.created_at ? new Date(kb.created_at).toLocaleDateString("en-IN") : "—"}</div>
                <div style={{ display: "flex", gap: 4 }}>
                  <Btn size="xs" variant="ghost" onClick={() => router.push(`/admin/intelligence/knowledge-bases/${kb.id}`)}>View</Btn>
                  {kb.status !== "active" && <Btn size="xs" variant="secondary" onClick={() => doActivate(kb.id)}>Activate</Btn>}
                  {kb.status === "active" && <Btn size="xs" variant="ghost" onClick={() => doDisable(kb.id)}>Disable</Btn>}
                  <Btn size="xs" variant="danger" onClick={() => doDelete(kb.id)}>Delete</Btn>
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      <KBWizardModal open={showWizard} onClose={() => setShowWizard(false)} onCreated={() => { refetchKBs(); onKBCreated(); }} />
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function IntelligencePage() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [toast, setToast] = useState("");
  const [showCreateKB, setShowCreateKB] = useState(false);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  // ── Data fetching ────────────────────────────────────────────────────────
  const { data: summary, loading: sumLoading, refetch } = useApi(
    () => intelligenceCmdApi.getSummary(), []
  );
  const { data: eventData } = useApi(
    () => activeTab === "events" ? intelligenceCmdApi.getEventSources() : Promise.resolve(null),
    [activeTab]
  );
  const { data: riskSum } = useApi(
    () => activeTab === "risk" ? intelligenceCmdApi.getRiskSummary() : Promise.resolve(null),
    [activeTab]
  );
  const { data: riskEntities, loading: riskLoading } = useApi(
    () => activeTab === "risk" ? intelligenceCmdApi.getRiskEntities() : Promise.resolve(null),
    [activeTab]
  );
  const { data: anomalyData, loading: anomalyLoading, refetch: refetchAnomalies } = useApi(
    () => activeTab === "anomalies" ? intelligenceCmdApi.getAnomalies() : Promise.resolve(null),
    [activeTab]
  );
  const { data: modelData, loading: modelLoading } = useApi(
    () => activeTab === "models" ? intelligenceCmdApi.getModels() : Promise.resolve(null),
    [activeTab]
  );
  const { data: jobData, loading: jobLoading, refetch: refetchJobs } = useApi(
    () => activeTab === "prediction-jobs" ? intelligenceCmdApi.getPredictionJobs() : Promise.resolve(null),
    [activeTab]
  );
  const { data: dqSummary } = useApi(
    () => activeTab === "data-quality" ? intelligenceCmdApi.getDQSummary() : Promise.resolve(null),
    [activeTab]
  );
  const { data: dqChecks, loading: dqLoading, refetch: refetchDQ } = useApi(
    () => activeTab === "data-quality" ? intelligenceCmdApi.getDQChecks() : Promise.resolve(null),
    [activeTab]
  );
  const { data: aiUsageSummary } = useApi(
    () => activeTab === "ai-usage" ? intelligenceCmdApi.getAiUsageSummary() : Promise.resolve(null),
    [activeTab]
  );
  const { data: aiLogs } = useApi(
    () => activeTab === "ai-usage" ? intelligenceCmdApi.getAiUsageLogs() : Promise.resolve(null),
    [activeTab]
  );
  const { data: auditData } = useApi(
    () => activeTab === "audit" ? intelligenceCmdApi.getAuditLogs() : Promise.resolve(null),
    [activeTab]
  );

  // ── Actions ──────────────────────────────────────────────────────────────
  const { execute: runPredictions, loading: predRunning } = useAction(async () => {
    const res = await intelligenceCmdApi.createPredictionJob({ job_type: "daily_tenant_risk" });
    refetchJobs();
    refetch();
    notify(`Prediction job completed — ${safeNum(res.total_processed)} tenants scored`);
  });

  const { execute: runScan, loading: scanRunning } = useAction(async () => {
    const res = await intelligenceCmdApi.runAnomalyScan();
    refetchAnomalies();
    refetch();
    notify(`Scan complete — ${safeNum(res.new_anomalies)} new anomalies, ${safeNum(res.updated)} updated`);
  });

  const { execute: runDQ } = useAction(async (key: string) => {
    await intelligenceCmdApi.runDQCheck(key);
    refetchDQ();
    notify(`Check "${key}" completed`);
  });

  const { execute: resolveAnomaly } = useAction(async (id: string) => {
    await intelligenceCmdApi.resolveAnomaly(id);
    refetchAnomalies();
    notify("Anomaly resolved");
  });

  const s = summary as IntelligenceSummary | null;

  return (
    <AdminLayout activeNav="intelligence">
      {toast && (
        <div style={{ padding: "10px 16px", background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius: 10, color: "var(--success-text)", fontSize: 13, marginBottom: 16, display: "flex", gap: 8 }}>
          <span>✓</span> {toast}
        </div>
      )}

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 4 }}>Intelligence / Overview</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Intelligence & Analytics</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>AI, RAG, risk scoring, anomaly detection and data quality command center</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn variant="secondary" size="sm" loading={predRunning} onClick={() => runPredictions()}>Run Predictions</Btn>
          <Btn variant="secondary" size="sm" loading={scanRunning} onClick={() => runScan()}>Run Anomaly Scan</Btn>
          <Btn variant="primary" size="sm" onClick={() => setShowCreateKB(true)}>+ Knowledge Base</Btn>
          <Btn variant="ghost" size="sm" onClick={refetch}>↻ Refresh</Btn>
        </div>
      </div>

      {/* KPI Grid — 5 × 2 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 24 }}>
        <KpiCard label="Tenants At Risk" value={fmtNum(s?.tenants_at_risk)} loading={sumLoading} helpText="high + critical" />
        <KpiCard label="Open Anomalies" value={fmtNum(s?.open_anomalies)} loading={sumLoading} helpText="pending investigation" />
        <KpiCard label="Predictions Computed" value={fmtNum(s?.predictions_computed)} loading={sumLoading} helpText="total records scored" />
        <KpiCard label="Events Today" value={fmtNum(s?.events_today)} loading={sumLoading} helpText="ingested events" />
        <KpiCard label="RAG Queries" value={fmtNum(s?.rag_queries)} loading={sumLoading} helpText="total queries" />
        <KpiCard label="Indexed Documents" value={fmtNum(s?.indexed_documents)} loading={sumLoading} helpText="across all KBs" />
        <KpiCard label="Avg AI Latency" value={fmtMs(s?.avg_ai_latency_ms)} loading={sumLoading} helpText="response time" />
        <KpiCard label="AI Cost Today" value={fmtCost(s?.ai_cost_today)} loading={sumLoading} helpText="spend today" />
        <KpiCard label="Active Tenants" value={fmtNum(s?.active_tenants)} loading={sumLoading} helpText="on platform" />
        <KpiCard label="Failed Jobs" value={fmtNum(s?.failed_jobs)} loading={sumLoading} helpText="prediction failures" />
      </div>

      {/* Tab Navigation */}
      <div style={{ display: "flex", gap: 2, borderBottom: "2px solid var(--border)", marginBottom: 20, overflowX: "auto" }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "10px 16px", border: "none", background: "none", cursor: "pointer",
              fontSize: 13, fontWeight: activeTab === tab.id ? 700 : 500,
              color: activeTab === tab.id ? "var(--brand)" : "var(--text-secondary)",
              borderBottom: activeTab === tab.id ? "2px solid var(--brand)" : "2px solid transparent",
              marginBottom: -2, whiteSpace: "nowrap",
            }}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ─────────────────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "65% 1fr", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Engine Health */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 16px" }}>Intelligence Engine Health</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                {[
                  { label: "RAG Engine", status: safeNum(s?.rag_queries) >= 0 ? "operational" : "no_data" },
                  { label: "Event Pipeline", status: safeNum(s?.events_today) >= 0 ? "operational" : "no_data" },
                  { label: "Prediction Engine", status: safeNum(s?.predictions_computed) >= 0 ? "operational" : "no_data" },
                  { label: "Anomaly Engine", status: safeNum(s?.open_anomalies) >= 0 ? "operational" : "no_data" },
                  { label: "Model Registry", status: "operational" },
                  { label: "Indexing Queue", status: safeNum(s?.indexed_documents) >= 0 ? "operational" : "no_data" },
                ].map(item => (
                  <div key={item.label} style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{item.label}</span>
                    <Badge variant={item.status === "operational" ? "success" : "muted"} size="sm">{item.status}</Badge>
                  </div>
                ))}
              </div>
            </div>

            {/* Analytics Snapshot */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 12px" }}>Analytics Snapshot</h3>
              {[
                ["Active Tenants", fmtNum(s?.active_tenants)],
                ["Tenants At Risk", fmtNum(s?.tenants_at_risk)],
                ["Predictions Computed", fmtNum(s?.predictions_computed)],
                ["RAG Queries", fmtNum(s?.rag_queries)],
                ["Indexed Documents", fmtNum(s?.indexed_documents)],
                ["AI Cost Today", fmtCost(s?.ai_cost_today)],
                ["Avg AI Latency", fmtMs(s?.avg_ai_latency_ms)],
                ["Failed Jobs", fmtNum(s?.failed_jobs)],
              ].map(([label, val]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{val}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Quick Stats */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, margin: "0 0 12px" }}>Quick Actions</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <Btn variant="secondary" size="sm" loading={predRunning} onClick={() => runPredictions()}>Run Tenant Risk Predictions</Btn>
                <Btn variant="secondary" size="sm" loading={scanRunning} onClick={() => runScan()}>Run Anomaly Scan</Btn>
                <Btn variant="ghost" size="sm" onClick={() => setActiveTab("data-quality")}>View Data Quality →</Btn>
                <Btn variant="ghost" size="sm" onClick={() => setActiveTab("rag")}>Manage Knowledge Bases →</Btn>
              </div>
            </div>

            {/* Anomaly Overview */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, margin: "0 0 12px" }}>Open Anomalies</h3>
              <div style={{ fontSize: 36, fontWeight: 800, color: safeNum(s?.open_anomalies) > 0 ? "var(--warning-text)" : "var(--success-text)", textAlign: "center", padding: "8px 0" }}>
                {fmtNum(s?.open_anomalies)}
              </div>
              <Btn variant="ghost" size="sm" style={{ width: "100%" }} onClick={() => setActiveTab("anomalies")}>View All →</Btn>
            </div>
          </div>
        </div>
      )}

      {/* ── RAG & KNOWLEDGE BASE ─────────────────────────────────────────────── */}
      {activeTab === "rag" && <RagTab onKBCreated={refetch} />}

      {/* ── EVENT PIPELINE ───────────────────────────────────────────────────── */}
      {activeTab === "events" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Event Sources</h3>
            </div>
            {(eventData?.items ?? []).length === 0 ? (
              <EmptyState msg="No event sources configured. Events will appear here once the pipeline is active." />
            ) : (
              <>
                <TableHead cols={["Source", "Events Today", "Success Rate", "Status"]} />
                {((eventData?.items ?? []) as Array<Record<string, unknown>>).map((src, i: number) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{String(src.source ?? "")}</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{fmtNum(src.events_today)}</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{fmtNum(src.success_rate)}%</div>
                    <Badge variant={(src.status === "healthy" ? "success" : src.status === "no_data" ? "muted" : "warning") as "success"}>{String(src.status ?? "")}</Badge>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── CHURN & RISK ─────────────────────────────────────────────────────── */}
      {activeTab === "risk" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Risk Summary Cards */}
          {riskSum && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              <KpiCard label="Critical" value={fmtNum(riskSum.critical)} />
              <KpiCard label="High" value={fmtNum(riskSum.high)} />
              <KpiCard label="Medium" value={fmtNum(riskSum.medium)} />
              <KpiCard label="Low" value={fmtNum(riskSum.low)} />
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
            <Btn variant="secondary" size="sm" loading={predRunning} onClick={() => runPredictions()}>Run Predictions</Btn>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Risk Entities</h3>
            </div>
            {riskLoading ? (
              <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 200, borderRadius: 6 }} /></div>
            ) : (riskEntities?.items ?? []).length === 0 ? (
              <EmptyState msg="No risk scores computed yet. Run predictions to generate risk data." />
            ) : (
              <>
                <TableHead cols={["Entity Type", "Entity ID", "Risk Score", "Risk Level", "Reasons", "Computed At"]} />
                {(riskEntities?.items ?? []).map((rs: RiskScore) => (
                  <div key={rs.id} style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", textTransform: "capitalize" }}>{rs.entity_type}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{rs.entity_id.slice(0, 8)}…</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{safeNum(rs.risk_score).toFixed(1)}</div>
                    <RiskBadge level={rs.risk_level} />
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{(rs.top_reasons_json ?? []).slice(0, 2).join(", ") || "—"}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{rs.computed_at ? new Date(rs.computed_at).toLocaleDateString("en-IN") : "—"}</div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── ANOMALIES ────────────────────────────────────────────────────────── */}
      {activeTab === "anomalies" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" loading={scanRunning} onClick={() => runScan()}>Run Anomaly Scan</Btn>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Detected Anomalies</h3>
              <Badge variant="warning">{fmtNum(anomalyData?.total)} total</Badge>
            </div>
            {anomalyLoading ? (
              <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 200, borderRadius: 6 }} /></div>
            ) : (anomalyData?.items ?? []).length === 0 ? (
              <EmptyState msg="No anomalies detected. Run an anomaly scan or wait for event pipeline monitoring." />
            ) : (
              <>
                <TableHead cols={["Type", "Severity", "Entity", "Status", "Detected", "Actions"]} />
                {(anomalyData?.items ?? []).map((a: IntelAnomaly) => (
                  <div key={a.id} style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{(a.anomaly_type ?? "").replace(/_/g, " ")}</div>
                    <SeverityBadge s={a.severity} />
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{a.entity_type ?? "system"}</div>
                    <StatusBadge status={a.status} />
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{a.detected_at ? new Date(a.detected_at).toLocaleDateString("en-IN") : "—"}</div>
                    {a.status === "open" && (
                      <Btn size="xs" variant="secondary" onClick={() => resolveAnomaly(a.id)}>Resolve</Btn>
                    )}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── MODELS ───────────────────────────────────────────────────────────── */}
      {activeTab === "models" && (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Model Registry</h3>
          </div>
          {modelLoading ? (
            <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 200, borderRadius: 6 }} /></div>
          ) : (modelData?.items ?? []).length === 0 ? (
            <EmptyState msg="No models registered. Create model entries to track your ML registry." />
          ) : (
            <>
              <TableHead cols={["Name", "Type", "Version", "Status", "Accuracy", "Last Trained", "Actions"]} />
              {(modelData?.items ?? []).map((m: ModelRegistryItem) => (
                <div key={m.id} style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{m.name}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{(m.model_type ?? "").replace(/_/g, " ")}</div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>v{m.version}</div>
                  <StatusBadge status={m.status} />
                  <div style={{ fontSize: 12, color: "var(--text-primary)" }}>{m.accuracy_score != null ? `${safeNum(m.accuracy_score).toFixed(1)}%` : "—"}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{m.last_trained_at ? new Date(m.last_trained_at).toLocaleDateString("en-IN") : "Never"}</div>
                  <div style={{ display: "flex", gap: 4 }}>
                    {m.status !== "active" && (
                      <Btn size="xs" variant="secondary" onClick={async () => { await intelligenceCmdApi.activateModel(m.id); notify("Model activated"); }}>Activate</Btn>
                    )}
                    {m.status === "active" && (
                      <Btn size="xs" variant="ghost" onClick={async () => { await intelligenceCmdApi.deactivateModel(m.id); notify("Model deactivated"); }}>Disable</Btn>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* ── PREDICTION JOBS ──────────────────────────────────────────────────── */}
      {activeTab === "prediction-jobs" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Btn variant="primary" size="sm" loading={predRunning} onClick={() => runPredictions()}>Run Now</Btn>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Prediction Jobs</h3>
              <Badge variant="muted">{fmtNum(jobData?.total)} total</Badge>
            </div>
            {jobLoading ? (
              <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 200, borderRadius: 6 }} /></div>
            ) : (jobData?.items ?? []).length === 0 ? (
              <EmptyState msg="No prediction jobs run yet. Click 'Run Now' to start a prediction job." />
            ) : (
              <>
                <TableHead cols={["Job Type", "Status", "Processed", "Failed", "Started", "Completed"]} />
                {(jobData?.items ?? []).map((j: PredictionJob) => (
                  <div key={j.id} style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{(j.job_type ?? "").replace(/_/g, " ")}</div>
                    <StatusBadge status={j.status} />
                    <div style={{ fontSize: 12, color: "var(--text-primary)" }}>{fmtNum(j.total_processed)}</div>
                    <div style={{ fontSize: 12, color: safeNum(j.total_failed) > 0 ? "var(--danger-text)" : "var(--text-tertiary)" }}>{fmtNum(j.total_failed)}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{j.started_at ? new Date(j.started_at).toLocaleString("en-IN") : "—"}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{j.completed_at ? new Date(j.completed_at).toLocaleString("en-IN") : "—"}</div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── DATA QUALITY ─────────────────────────────────────────────────────── */}
      {activeTab === "data-quality" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {dqSummary && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              <KpiCard label="Passed" value={fmtNum(dqSummary.passed)} />
              <KpiCard label="Failed" value={fmtNum(dqSummary.failed)} />
              <KpiCard label="Warning" value={fmtNum(dqSummary.warning)} />
              <KpiCard label="Not Run" value={fmtNum(dqSummary.not_run)} />
            </div>
          )}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Data Quality Checks</h3>
            </div>
            {dqLoading ? (
              <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 200, borderRadius: 6 }} /></div>
            ) : (dqChecks?.items ?? []).length === 0 ? (
              <EmptyState msg="No data quality checks configured." />
            ) : (
              <>
                <TableHead cols={["Check Name", "Severity", "Failures", "Last Run", "Status", "Action"]} />
                {(dqChecks?.items ?? []).map((c: DataQualityCheck) => (
                  <div key={c.id} style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{c.check_name}</div>
                    <SeverityBadge s={c.severity} />
                    <div style={{ fontSize: 12, color: safeNum(c.failure_count) > 0 ? "var(--danger-text)" : "var(--text-tertiary)" }}>{fmtNum(c.failure_count)}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{c.last_run_at ? new Date(c.last_run_at).toLocaleDateString("en-IN") : "Never"}</div>
                    <StatusBadge status={c.last_status} />
                    <Btn size="xs" variant="secondary" onClick={() => runDQ(c.check_key)}>Run Check</Btn>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── AI COST & USAGE ──────────────────────────────────────────────────── */}
      {activeTab === "ai-usage" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {aiUsageSummary && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
              <KpiCard label="Cost Today" value={fmtCost((aiUsageSummary as Record<string, unknown>).total_cost_today)} />
              <KpiCard label="Monthly Cost" value={fmtCost((aiUsageSummary as Record<string, unknown>).monthly_cost)} />
              <KpiCard label="Total Queries" value={fmtNum((aiUsageSummary as Record<string, unknown>).total_queries)} />
              <KpiCard label="Avg Latency" value={fmtMs((aiUsageSummary as Record<string, unknown>).avg_latency_ms)} />
              <KpiCard label="Failed Calls" value={fmtNum((aiUsageSummary as Record<string, unknown>).failed_calls)} />
            </div>
          )}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>AI Usage Logs</h3>
            </div>
            {(aiLogs?.items ?? []).length === 0 ? (
              <EmptyState msg="No AI usage recorded yet." />
            ) : (
              <>
                <TableHead cols={["Feature", "Model", "Tokens In", "Tokens Out", "Cost", "Latency", "Status"]} />
                {((aiLogs?.items ?? []) as Array<Record<string, unknown>>).map((log, i: number) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{String(log.feature_key ?? "—")}</div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{String(log.model_name ?? "—")}</div>
                    <div style={{ fontSize: 12 }}>{fmtNum(log.tokens_in)}</div>
                    <div style={{ fontSize: 12 }}>{fmtNum(log.tokens_out)}</div>
                    <div style={{ fontSize: 12 }}>{fmtCost(log.cost_amount)}</div>
                    <div style={{ fontSize: 12 }}>{fmtMs(log.latency_ms)}</div>
                    <Badge variant={(log.status === "success" ? "success" : "danger") as "success"}>{String(log.status ?? "")}</Badge>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── AUDIT LOGS ───────────────────────────────────────────────────────── */}
      {activeTab === "audit" && (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Audit Logs</h3>
          </div>
          {(auditData?.items ?? []).length === 0 ? (
            <EmptyState msg="No audit events recorded yet." />
          ) : (
            <>
              <TableHead cols={["Time", "Actor", "Action", "Target", "Request ID"]} />
              {((auditData?.items ?? []) as Array<Record<string, unknown>>).map((log, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8, padding: "10px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{log.time ? new Date(String(log.time)).toLocaleString("en-IN") : "—"}</div>
                  <div style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-secondary)" }}>{String(log.actor ?? "—").slice(0, 10)}</div>
                  <div style={{ fontSize: 12, color: "var(--text-primary)" }}>{String(log.action ?? "—")}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{String(log.target ?? "—")}</div>
                  <div style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-tertiary)" }}>{String(log.request_id ?? "—").slice(0, 12)}</div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

    </AdminLayout>
  );
}
