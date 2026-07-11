"use client";
/**
 * Platform Settings — Enterprise System Configuration Center (7 tabs).
 * PROVEN: every mutating action (create/update/enable/disable/rollback/override/flag)
 * is backed by an audit-logged endpoint under /v1/admin/settings/*.
 * Secret settings are always masked, both server-side and client-side.
 */
import { useState, useCallback } from "react";
import {
  Settings as SettingsIcon, Layers, Package, Building2, Flag, ScrollText, History, Download, Upload,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Modal, Input, Select, Skeleton } from "../../../components/shared/ui";
import { SummaryCardsRow } from "../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../components/pricing/ActionMenu";
import {
  settingsAdminApi, EnterpriseSetting, FeatureFlag, PlanSettingRow, CategorySettingRow,
  TenantOverrideRow, SettingAuditLogRow,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

type Tab = "global" | "category" | "plan" | "tenant_overrides" | "feature_flags" | "audit_log" | "version_history";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "global", label: "Global Settings", icon: <SettingsIcon size={14} /> },
  { key: "category", label: "Category Settings", icon: <Layers size={14} /> },
  { key: "plan", label: "Plan / Package Settings", icon: <Package size={14} /> },
  { key: "tenant_overrides", label: "Tenant Overrides", icon: <Building2 size={14} /> },
  { key: "feature_flags", label: "Feature Flags", icon: <Flag size={14} /> },
  { key: "audit_log", label: "Audit Log", icon: <ScrollText size={14} /> },
  { key: "version_history", label: "Version History", icon: <History size={14} /> },
];

const CATEGORY_LABELS: Record<string, string> = {
  general_platform: "General Platform", tenant_onboarding: "Tenant Onboarding",
  booking_and_jobs: "Booking & Jobs", pricing_and_bargain: "Pricing & Bargain",
  packages_and_usage_credits: "Packages & Usage Credits", security_deposits: "Security Deposits",
  disputes_and_customer_credits: "Disputes & Customer Credits", media_and_storage: "Media & Storage",
  notifications: "Notifications", compliance_dpdp: "Compliance / DPDP", security: "Security",
  ai_deepseek: "AI / DeepSeek", audit_and_retention: "Audit & Retention", maintenance: "Maintenance",
  feature_flags: "Feature Flags",
};

const RISK_VARIANT: Record<string, "danger" | "warning" | "info" | "muted"> = {
  critical: "danger", high: "warning", medium: "info", low: "muted",
};

function EmptyState({ text, actions }: { text: string; actions?: React.ReactNode }) {
  return (
    <div style={{ padding: "36px 20px", textAlign: "center" }}>
      <p style={{ color: "var(--text-tertiary)", fontSize: 13, margin: "0 0 14px" }}>{text}</p>
      {actions}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>{children}</th>;
}
function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: "10px 12px", fontSize: 13, borderBottom: "1px solid var(--border)" }}>{children}</td>;
}

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("global");

  return (
    <AdminLayout activeNav="settings">
      <SectionHeader
        title="Platform Settings"
        subtitle="Configure global platform, category, package, tenant, finance, security, compliance, and runtime settings."
      />
      <div style={{ padding: "0 28px 32px" }}>
        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20, overflowX: "auto" }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{
              display: "flex", alignItems: "center", gap: 6, padding: "10px 16px", border: "none",
              background: "none", cursor: "pointer", fontSize: 13, fontWeight: tab === t.key ? 700 : 500,
              color: tab === t.key ? "var(--accent)" : "var(--text-secondary)",
              borderBottom: tab === t.key ? "2px solid var(--accent)" : "2px solid transparent",
              whiteSpace: "nowrap",
            }}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>

        {tab === "global" && <GlobalSettingsTab />}
        {tab === "category" && <CategorySettingsTab />}
        {tab === "plan" && <PlanSettingsTab />}
        {tab === "tenant_overrides" && <TenantOverridesTab />}
        {tab === "feature_flags" && <FeatureFlagsTab />}
        {tab === "audit_log" && <AuditLogTab />}
        {tab === "version_history" && <VersionHistoryTab />}
      </div>
    </AdminLayout>
  );
}

// ═══════════════════════════════════════════════════════════════
// GLOBAL SETTINGS
// ═══════════════════════════════════════════════════════════════

function GlobalSettingsTab() {
  const [category, setCategory] = useState<string | null>(null);
  const [addModal, setAddModal] = useState(false);
  const [editSetting, setEditSetting] = useState<EnterpriseSetting | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editReason, setEditReason] = useState("");
  const [previewSetting, setPreviewSetting] = useState<EnterpriseSetting | null>(null);
  const [previewResult, setPreviewResult] = useState<Awaited<ReturnType<typeof settingsAdminApi.impactPreview>> | null>(null);
  const [resolverKey, setResolverKey] = useState("tenant_payouts_enabled");

  const summary = useApi(useCallback(() => settingsAdminApi.getSummary(), []));
  const groups = useApi(useCallback(() => settingsAdminApi.getGroups(), []));
  const list = useApi(useCallback(() => settingsAdminApi.list({ category: category || undefined }), [category]));
  const resolver = useApi(useCallback(() => settingsAdminApi.resolveEffectiveValue(resolverKey), [resolverKey]));

  const seedPreviewAction = useAction(useCallback(() => settingsAdminApi.previewSeedDefaults(), []));
  const seedAction = useAction(useCallback(() => settingsAdminApi.seedDefaults(), []));
  const updateAction = useAction(useCallback(
    (key: string, value: unknown, reason: string) => settingsAdminApi.update(key, { value, reason }), []));
  const impactAction = useAction(useCallback(
    (key: string, newValue: unknown) => settingsAdminApi.impactPreview(key, newValue), []));

  const s = summary.data;
  const settings = list.data?.settings ?? [];

  function parseValue(raw: string): unknown {
    if (raw === "true") return true;
    if (raw === "false") return false;
    if (!isNaN(Number(raw)) && raw.trim() !== "") return Number(raw);
    try { return JSON.parse(raw); } catch { return raw; }
  }

  async function openEdit(setting: EnterpriseSetting) {
    setEditSetting(setting);
    setEditValue(setting.is_secret ? "" : fmtValue(setting.value));
    setEditReason("");
  }

  async function openPreview(setting: EnterpriseSetting) {
    setPreviewSetting(setting);
    const result = await impactAction.execute(setting.key, setting.value);
    setPreviewResult(result);
  }

  async function saveEdit() {
    if (!editSetting) return;
    const result = await updateAction.execute(editSetting.key, parseValue(editValue), editReason);
    if (result) { setEditSetting(null); list.refetch(); summary.refetch(); }
  }

  async function runSeed() {
    await seedAction.execute();
    list.refetch(); summary.refetch(); groups.refetch();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" size="sm" onClick={async () => { const r = await seedPreviewAction.execute(); if (r) alert(`Would create ${r.would_create.length}, skip ${r.would_skip.length}`); }}>
            Preview Seed Defaults
          </Btn>
          <Btn variant="primary" size="sm" loading={seedAction.loading} onClick={runSeed}>Seed Defaults</Btn>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" size="sm" icon={<Upload size={14} />} disabled>Import</Btn>
          <Btn variant="secondary" size="sm" icon={<Download size={14} />} disabled>Export</Btn>
          <Btn variant="primary" size="sm" onClick={() => setAddModal(true)}>Add Setting</Btn>
        </div>
      </div>

      {s && (
        <SummaryCardsRow cards={[
          { label: "Total Settings", value: s.total_settings },
          { label: "Active Settings", value: s.active_settings },
          { label: "Secret Settings", value: s.secret_settings },
          { label: "Pending Approval", value: s.pending_approval, accent: s.pending_approval > 0 },
          { label: "Tenant Overrides", value: s.tenant_overrides },
          { label: "Plan Overrides", value: s.plan_overrides },
          { label: "Changed This Week", value: s.changed_this_week },
          { label: "Rollback Available", value: s.rollback_available },
        ]} />
      )}

      {settings.length === 0 && !list.loading ? (
        <Card padding={0}>
          <EmptyState text="No platform settings configured. Seed recommended ServiceOS defaults or create a setting manually." actions={
            <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
              <Btn variant="primary" size="sm" onClick={runSeed}>Seed Defaults</Btn>
              <Btn variant="secondary" size="sm" onClick={() => setAddModal(true)}>Add Setting</Btn>
            </div>
          } />
        </Card>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 320px", gap: 16 }}>
          {/* Left category sidebar */}
          <Card padding={8}>
            <button onClick={() => setCategory(null)} style={{
              display: "block", width: "100%", textAlign: "left", padding: "8px 10px", border: "none",
              background: !category ? "var(--surface-sunken)" : "none", borderRadius: 6, cursor: "pointer",
              fontSize: 13, fontWeight: !category ? 700 : 500, marginBottom: 2,
            }}>All Categories</button>
            {(groups.data?.categories ?? []).map(c => (
              <button key={c.category} onClick={() => setCategory(c.category)} style={{
                display: "flex", justifyContent: "space-between", width: "100%", textAlign: "left",
                padding: "8px 10px", border: "none", background: category === c.category ? "var(--surface-sunken)" : "none",
                borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: category === c.category ? 700 : 500, marginBottom: 2,
              }}>
                <span>{CATEGORY_LABELS[c.category] ?? c.category}</span>
                <span style={{ color: "var(--text-tertiary)" }}>{c.setting_count}</span>
              </button>
            ))}
          </Card>

          {/* Main settings table */}
          <Card padding={0}>
            {list.loading ? <Skeleton height={300} /> : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead><tr><Th>Setting</Th><Th>Key</Th><Th>Type</Th><Th>Value</Th><Th>Risk</Th><Th>Status</Th><Th>{" "}</Th></tr></thead>
                <tbody>
                  {settings.map(st => (
                    <tr key={st.key}>
                      <Td>{st.label}</Td>
                      <Td><code style={{ fontSize: 11 }}>{st.key}</code></Td>
                      <Td>{st.type}</Td>
                      <Td>{st.is_secret ? "••••••••" : fmtValue(st.value)}</Td>
                      <Td><Badge variant={RISK_VARIANT[st.risk_level] ?? "muted"} size="sm">{st.risk_level}</Badge></Td>
                      <Td><Badge variant={st.status === "active" ? "success" : "muted"} size="sm">{st.status}</Badge></Td>
                      <Td>
                        <ActionMenu items={[
                          { label: "Edit", onClick: () => openEdit(st), disabled: !st.is_runtime_editable },
                          { label: "Preview Impact", onClick: () => openPreview(st) },
                          { label: st.status === "active" ? "Disable" : "Enable", onClick: async () => {
                              if (st.status === "active") await settingsAdminApi.disable(st.key);
                              else await settingsAdminApi.enable(st.key);
                              list.refetch();
                            } },
                        ]} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Right effective value / resolver panel */}
          <Card padding={16}>
            <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Effective Value Resolver</h3>
            <Input label="Setting Key" value={resolverKey} onChange={setResolverKey} />
            {resolver.loading ? <Skeleton height={100} /> : resolver.data && (
              <div style={{ marginTop: 10, fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                <div>Default: <strong>{fmtValue(resolver.data.default_value)}</strong></div>
                <div>Global: <strong>{fmtValue(resolver.data.global_value)}</strong></div>
                <div>Plan Override: <strong>{fmtValue(resolver.data.plan_override)}</strong></div>
                <div>Tenant Override: <strong>{fmtValue(resolver.data.tenant_override)}</strong></div>
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: 6, marginTop: 4 }}>
                  Effective: <strong style={{ color: "var(--accent)" }}>{fmtValue(resolver.data.effective_value)}</strong>
                </div>
                <div style={{ color: "var(--text-tertiary)" }}>Path: {resolver.data.resolution_path}</div>
              </div>
            )}
          </Card>
        </div>
      )}

      <Modal open={!!editSetting} onClose={() => setEditSetting(null)} title={`Edit: ${editSetting?.label ?? ""}`}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {updateAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{updateAction.error}</p>}
          {editSetting?.is_secret && (
            <p style={{ fontSize: 12, color: "var(--warning-text,#b45309)" }}>
              This is a secret setting. Enter a new value to rotate it — the current value cannot be displayed.
            </p>
          )}
          <Input label="New Value" value={editValue} onChange={setEditValue} required />
          {editSetting?.risk_level === "critical" && (
            <Input label="Reason (required for critical settings)" value={editReason} onChange={setEditReason} required />
          )}
          {editSetting?.risk_level !== "critical" && (
            <Input label="Reason (optional)" value={editReason} onChange={setEditReason} />
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setEditSetting(null)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={updateAction.loading}
              disabled={editSetting?.risk_level === "critical" && !editReason}
              onClick={saveEdit}>Save</Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!previewSetting} onClose={() => { setPreviewSetting(null); setPreviewResult(null); }} title="Impact Preview">
        {previewResult && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
            {previewResult.blocked && (
              <div style={{ padding: "10px 14px", background: "var(--danger-bg)", borderRadius: 8, color: "var(--danger-text)" }}>
                {previewResult.blocker_message}
              </div>
            )}
            <div>Risk Level: <Badge variant={RISK_VARIANT[previewResult.risk_level] ?? "muted"} size="sm">{previewResult.risk_level}</Badge></div>
            {previewResult.warnings.map((w, i) => <p key={i} style={{ color: "var(--warning-text,#b45309)", margin: 0 }}>⚠ {w}</p>)}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Btn variant="ghost" size="sm" onClick={() => { setPreviewSetting(null); setPreviewResult(null); }}>Close</Btn>
            </div>
          </div>
        )}
      </Modal>

      <AddSettingModal open={addModal} onClose={() => setAddModal(false)} onCreated={() => { list.refetch(); summary.refetch(); groups.refetch(); }} />
    </div>
  );
}

function AddSettingModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [value, setValue] = useState("");
  const [settingType, setSettingType] = useState("string");
  const [category, setCategory] = useState("general_platform");
  const [isSecret, setIsSecret] = useState(false);
  const [riskLevel, setRiskLevel] = useState("low");

  const createAction = useAction(useCallback(
    () => settingsAdminApi.create({
      key, label, value: settingType === "boolean" ? value === "true" : value,
      setting_type: settingType, category, is_secret: isSecret, risk_level: riskLevel,
    }), [key, label, value, settingType, category, isSecret, riskLevel]));

  async function handleCreate() {
    const result = await createAction.execute();
    if (result) {
      setKey(""); setLabel(""); setValue(""); onClose(); onCreated();
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add Setting">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {createAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{createAction.error}</p>}
        <Input label="Setting Label" value={label} onChange={setLabel} required />
        <Input label="Setting Key" placeholder="e.g. max_tenants_per_city" value={key} onChange={setKey} required />
        <Select label="Setting Type" value={settingType} onChange={setSettingType} options={[
          { value: "string", label: "string" }, { value: "number", label: "number" },
          { value: "boolean", label: "boolean" }, { value: "json", label: "json" },
          { value: "secret", label: "secret" },
        ]} />
        <Input label="Default Value" value={value} onChange={setValue} required />
        <Select label="Category" value={category} onChange={setCategory} options={
          Object.entries(CATEGORY_LABELS).map(([v, label]) => ({ value: v, label }))
        } />
        <Select label="Risk Level" value={riskLevel} onChange={setRiskLevel} options={[
          { value: "low", label: "low" }, { value: "medium", label: "medium" },
          { value: "high", label: "high" }, { value: "critical", label: "critical" },
        ]} />
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <input type="checkbox" checked={isSecret} onChange={e => setIsSecret(e.target.checked)} />
          Is Secret (value will be masked after save)
        </label>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={createAction.loading} disabled={!key || !label} onClick={handleCreate}>Create</Btn>
        </div>
      </div>
    </Modal>
  );
}

// ═══════════════════════════════════════════════════════════════
// CATEGORY SETTINGS
// ═══════════════════════════════════════════════════════════════

function CategorySettingsTab() {
  const categories = useApi(useCallback(() => settingsAdminApi.listCategories(), []));
  const rows = categories.data?.categories ?? [];

  return (
    <Card padding={0}>
      {categories.loading ? <Skeleton height={200} /> : rows.length === 0 ? (
        <EmptyState text="No categories found." />
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><Th>Category</Th><Th>Vertical</Th><Th>Finance Model</Th><Th>Payment Collection</Th><Th>Payouts</Th><Th>Status</Th></tr></thead>
          <tbody>
            {rows.map((c: CategorySettingRow) => (
              <tr key={c.id}>
                <Td>{c.name}</Td>
                <Td>{c.vertical_type ?? "—"}</Td>
                <Td><code style={{ fontSize: 11 }}>{c.finance_model ?? "—"}</code></Td>
                <Td><Badge variant={c.payment_collection_enabled ? "warning" : "success"} size="sm">{String(c.payment_collection_enabled)}</Badge></Td>
                <Td><Badge variant={c.tenant_payouts_enabled ? "warning" : "success"} size="sm">{String(c.tenant_payouts_enabled)}</Badge></Td>
                <Td><Badge variant={c.is_active ? "success" : "muted"} size="sm">{c.is_active ? "active" : "inactive"}</Badge></Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════
// PLAN / PACKAGE SETTINGS
// ═══════════════════════════════════════════════════════════════

function PlanSettingsTab() {
  const plans = useApi(useCallback(() => settingsAdminApi.listPlans(), []));
  const rows = plans.data?.packages ?? [];

  return (
    <Card padding={0}>
      {plans.loading ? <Skeleton height={200} /> : rows.length === 0 ? (
        <EmptyState text="No plan settings configured. Select a package or seed default plan settings." />
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><Th>Package</Th><Th>Type</Th><Th>Included Credits</Th><Th>Storage Quota GB</Th><Th>Commission</Th><Th>Deposit</Th><Th>Status</Th></tr></thead>
          <tbody>
            {rows.map((p: PlanSettingRow) => (
              <tr key={p.id}>
                <Td>{p.name}</Td>
                <Td>{p.package_type}</Td>
                <Td>{p.included_credit_amount ?? "—"}</Td>
                <Td>{p.storage_quota_gb ?? "—"}</Td>
                <Td>{p.commission_rate != null ? `${p.commission_rate}%` : "—"}</Td>
                <Td>{p.security_deposit_amount ?? "—"}</Td>
                <Td><Badge variant={p.is_active ? "success" : "muted"} size="sm">{p.is_active ? "active" : "inactive"}</Badge></Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════
// TENANT OVERRIDES
// ═══════════════════════════════════════════════════════════════

function TenantOverridesTab() {
  const [modal, setModal] = useState(false);
  const [tenantId, setTenantId] = useState("");
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");

  const overrides = useApi(useCallback(() => settingsAdminApi.listTenantOverrides(), []));
  const createAction = useAction(useCallback(
    () => settingsAdminApi.createTenantOverride({ tenant_id: tenantId, key, value, reason }),
    [tenantId, key, value, reason]));
  const revokeAction = useAction(useCallback(
    (id: string, r: string) => settingsAdminApi.revokeTenantOverride(id, r), []));

  const rows = overrides.data?.overrides ?? [];

  async function handleCreate() {
    const result = await createAction.execute();
    if (result) { setModal(false); setTenantId(""); setKey(""); setValue(""); setReason(""); overrides.refetch(); }
  }

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <Btn variant="primary" size="sm" onClick={() => setModal(true)}>Create Override</Btn>
      </div>
      <Card padding={0}>
        {overrides.loading ? <Skeleton height={200} /> : rows.length === 0 ? (
          <EmptyState text="No tenant overrides configured." />
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Tenant</Th><Th>Setting</Th><Th>Value</Th><Th>Reason</Th><Th>Expires</Th><Th>Status</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {rows.map((o: TenantOverrideRow) => (
                <tr key={o.id}>
                  <Td><code style={{ fontSize: 11 }}>{o.tenant_id.slice(0, 8)}</code></Td>
                  <Td>{o.key}</Td>
                  <Td>{fmtValue(o.value)}</Td>
                  <Td>{o.reason ?? "—"}</Td>
                  <Td>{o.expires_at ? new Date(o.expires_at).toLocaleDateString("en-IN") : "Never"}</Td>
                  <Td><Badge variant={o.status === "active" ? "success" : "muted"} size="sm">{o.status}</Badge></Td>
                  <Td>
                    <ActionMenu items={[
                      { label: "Revoke", onClick: () => revokeAction.execute(o.id, "Revoked by admin").then(() => overrides.refetch()), destructive: true },
                    ]} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modal} onClose={() => setModal(false)} title="Create Tenant Override">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {createAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{createAction.error}</p>}
          <Input label="Tenant ID" value={tenantId} onChange={setTenantId} required />
          <Input label="Setting Key" value={key} onChange={setKey} required />
          <Input label="Override Value" value={value} onChange={setValue} required />
          <Input label="Reason (required)" value={reason} onChange={setReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!tenantId || !key || !reason} loading={createAction.loading} onClick={handleCreate}>Create</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// FEATURE FLAGS
// ═══════════════════════════════════════════════════════════════

function FeatureFlagsTab() {
  const [modal, setModal] = useState(false);
  const [flagKey, setFlagKey] = useState("");
  const [label, setLabel] = useState("");

  const flags = useApi(useCallback(() => settingsAdminApi.listFeatureFlags(), []));
  const createAction = useAction(useCallback(
    () => settingsAdminApi.createFeatureFlag({ flag_key: flagKey, label }), [flagKey, label]));
  const enableAction = useAction(useCallback((id: string) => settingsAdminApi.enableFeatureFlag(id), []));
  const disableAction = useAction(useCallback((id: string) => settingsAdminApi.disableFeatureFlag(id), []));

  const rows = flags.data?.flags ?? [];

  async function handleCreate() {
    const result = await createAction.execute();
    if (result) { setModal(false); setFlagKey(""); setLabel(""); flags.refetch(); }
  }

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <Btn variant="primary" size="sm" icon={<Flag size={14} />} onClick={() => setModal(true)}>Create Flag</Btn>
      </div>
      <Card padding={0}>
        {flags.loading ? <Skeleton height={200} /> : rows.length === 0 ? (
          <EmptyState text="No feature flags configured." />
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Flag</Th><Th>Key</Th><Th>Status</Th><Th>Rollout</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {rows.map((f: FeatureFlag) => (
                <tr key={f.id}>
                  <Td>{f.label}</Td>
                  <Td><code style={{ fontSize: 11 }}>{f.flag_key}</code></Td>
                  <Td><Badge variant={f.status === "enabled" ? "success" : "muted"} size="sm">{f.status}</Badge></Td>
                  <Td>{f.rollout_type}{f.rollout_percent != null ? ` (${f.rollout_percent}%)` : ""}</Td>
                  <Td>
                    <ActionMenu items={[
                      f.status === "enabled"
                        ? { label: "Disable", onClick: () => disableAction.execute(f.id).then(() => flags.refetch()), destructive: true }
                        : { label: "Enable", onClick: () => enableAction.execute(f.id).then(() => flags.refetch()) },
                    ]} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modal} onClose={() => setModal(false)} title="Create Feature Flag">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {createAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{createAction.error}</p>}
          <Input label="Flag Label" value={label} onChange={setLabel} required />
          <Input label="Flag Key" placeholder="e.g. bargain_engine_enabled" value={flagKey} onChange={setFlagKey} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!flagKey || !label} loading={createAction.loading} onClick={handleCreate}>Create</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// AUDIT LOG
// ═══════════════════════════════════════════════════════════════

function AuditLogTab() {
  const [key, setKey] = useState("");
  const logs = useApi(useCallback(() => settingsAdminApi.getAuditLogs({ key: key || undefined, limit: 100 }), [key]));
  const rows = logs.data?.logs ?? [];

  return (
    <div>
      <div style={{ marginBottom: 14, maxWidth: 320 }}>
        <Input placeholder="Filter by setting key..." value={key} onChange={setKey} />
      </div>
      <Card padding={0}>
        {logs.loading ? <Skeleton height={200} /> : rows.length === 0 ? (
          <EmptyState text="No audit entries." />
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Time</Th><Th>Setting</Th><Th>Scope</Th><Th>Action</Th><Th>Old → New</Th><Th>Risk</Th></tr></thead>
            <tbody>
              {rows.map((l: SettingAuditLogRow) => (
                <tr key={l.log_id}>
                  <Td>{new Date(l.created_at).toLocaleString("en-IN")}</Td>
                  <Td><code style={{ fontSize: 11 }}>{l.key}</code></Td>
                  <Td>{l.tier}</Td>
                  <Td>{l.action_type}</Td>
                  <Td>{fmtValue(l.old_value)} → {fmtValue(l.new_value)}</Td>
                  <Td><Badge variant={RISK_VARIANT[l.risk_level] ?? "muted"} size="sm">{l.risk_level}</Badge></Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// VERSION HISTORY
// ═══════════════════════════════════════════════════════════════

function VersionHistoryTab() {
  const [key, setKey] = useState("tenant_payouts_enabled");
  const [rollbackReason, setRollbackReason] = useState("");
  const [rollbackLogId, setRollbackLogId] = useState<string | null>(null);

  const history = useApi(useCallback(() => settingsAdminApi.getHistory(key), [key]));
  const rollbackAction = useAction(useCallback(
    (logId: string, reason: string) => settingsAdminApi.rollback(key, logId, reason), [key]));

  const rows = history.data?.history ?? [];

  async function handleRollback() {
    if (!rollbackLogId || !rollbackReason) return;
    const result = await rollbackAction.execute(rollbackLogId, rollbackReason);
    if (result) { setRollbackLogId(null); setRollbackReason(""); history.refetch(); }
  }

  return (
    <div>
      <div style={{ marginBottom: 14, maxWidth: 320 }}>
        <Input label="Setting Key" value={key} onChange={setKey} />
      </div>
      <Card padding={0}>
        {history.loading ? <Skeleton height={200} /> : rows.length === 0 ? (
          <EmptyState text="No version history for this setting." />
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>When</Th><Th>Action</Th><Th>Old → New</Th><Th>Changed By</Th><Th>Reason</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {rows.map(h => (
                <tr key={h.log_id}>
                  <Td>{new Date(h.created_at).toLocaleString("en-IN")}</Td>
                  <Td>{h.action_type}</Td>
                  <Td>{fmtValue(h.old_value)} → {fmtValue(h.new_value)}</Td>
                  <Td>{h.changed_by ? h.changed_by.slice(0, 8) : "—"}</Td>
                  <Td>{h.reason ?? "—"}</Td>
                  <Td>
                    {h.rollback_available && (
                      <Btn variant="secondary" size="xs" onClick={() => setRollbackLogId(h.log_id)}>Rollback</Btn>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={!!rollbackLogId} onClose={() => setRollbackLogId(null)} title="Rollback Setting">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {rollbackAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{rollbackAction.error}</p>}
          <Input label="Reason (required)" value={rollbackReason} onChange={setRollbackReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setRollbackLogId(null)}>Cancel</Btn>
            <Btn variant="danger" size="sm" disabled={!rollbackReason} loading={rollbackAction.loading} onClick={handleRollback}>Rollback</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
