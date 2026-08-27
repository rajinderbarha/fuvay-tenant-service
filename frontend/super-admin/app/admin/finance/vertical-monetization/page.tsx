"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SummaryCard } from "../../../../components/shared/ui";
import {
  verticalMonetizationApi, type MonetizationPolicyRow, type MonetizationPolicy, type MonetizationImpact,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { useRouter } from "next/navigation";
import {
  FileText, Sparkles, AlertTriangle, Building2, CheckCircle2, Calendar,
  Clock, ShieldCheck, Search, ArrowUpRight,
} from "lucide-react";
import { PageHeader } from "@serviceos/design-system";

// Home Services has its own category-specific monetization workspace at
// /admin/home-services/finance?tab=monetization (reusing this same engine,
// hardcoded server-side to "home_services") -- it is the ONE editable source
// for Home Services policy. This page redirects that row there instead of
// opening the generic editor, so there is never a second editable copy.
const CATEGORY_WORKSPACE_VERTICALS: Record<string, string> = {
  home_services: "/admin/home-services/finance?tab=monetization",
};

// VERTICAL-MONETIZATION: replaces Catalog/Pricing/Category Rates. This page
// edits ONLY the platform's two-sided monetization policy per Business
// Vertical (provider-side charge model + customer-side platform fee).
// Tenant service prices are never read or written here.

const TABS = ["policies", "history", "audit"] as const;
type TabKey = typeof TABS[number];

const PROVIDER_MODELS = ["NONE", "COMPLETION_CREDITS", "PERCENTAGE_COMMISSION", "FIXED_COMPLETION_CHARGE", "SUBSCRIPTION", "LEAD_FEE"];
const CUSTOMER_FEE_MODELS = ["NONE", "PERCENTAGE", "FIXED", "PERCENTAGE_WITH_MIN_MAX"];
const COLLECTION_STAGES = ["before_booking_confirmation", "after_estimate_approval", "before_work_start", "on_completion"];

type DraftForm = Partial<MonetizationPolicy>;

export default function VerticalMonetizationPage() {
  const router = useRouter();
  const [tab, setTab] = useState<TabKey>("policies");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [modelFilter, setModelFilter] = useState("");

  const listApi = useApi(useCallback(() => verticalMonetizationApi.list(), []));
  const rows = listApi.data?.items ?? [];
  const summary = listApi.data?.summary;

  const filtered = rows.filter(r =>
    (!search || r.vertical_label.toLowerCase().includes(search.toLowerCase())) &&
    (!modelFilter || r.revenue_model === modelFilter));

  const selectedRow = (rows.find(r => r.vertical_key === selectedKey) ?? filtered.find(r => !CATEGORY_WORKSPACE_VERTICALS[r.vertical_key]) ?? null);

  return (
    <AdminLayout activeNav="vertical-monetization">
      <div style={{ padding: "0 4px" }}>
        <PageHeader
          title="Category Rates"
          description="Configure platform monetization by business vertical. Tenant service prices remain tenant-owned."
          eyebrow="Finance"
          context="Business Categories"
          actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)" }}>
            <Btn variant="ghost" size="sm" onClick={() => setTab("audit")}><FileText size={14} style={{ marginRight: 4 }}/>View Audit</Btn>
            <Btn variant="primary" size="sm" onClick={() => { setTab("policies"); setSelectedKey(rows.find(r => !r.has_draft)?.vertical_key ?? selectedKey); }}>
              <Sparkles size={14} style={{ marginRight: 4 }}/>Create Draft Policy
            </Btn>
          </div>}
        />

        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 16px", borderRadius: "var(--radius-lg)",
          background: "var(--info-bg, rgba(59,130,246,0.08))", border: "1px solid var(--info-border, rgba(59,130,246,0.3))", marginBottom: 16 }}>
          <AlertTriangle size={16} style={{ color: "var(--info-text, var(--brand))", flexShrink: 0, marginTop: 1 }}/>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Runtime enablement is managed in Business Verticals. Catalog structure is managed inside each vertical. Changes here affect monetization only.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(110px, 1fr))", gap: 10, marginBottom: 18 }}>
          <Metric icon={<Building2 size={16}/>} value={summary?.active_verticals} label="Total Verticals"/>
          <Metric icon={<CheckCircle2 size={16}/>} value={summary?.configured} label="Configured"/>
          <Metric icon={<ShieldCheck size={16}/>} value={rows.filter(r => r.status === "Active").length} label="Active Policies"/>
          <Metric icon={<Calendar size={16}/>} value={summary?.subscription_based} label="Subscription Based"/>
          <Metric icon={<Clock size={16}/>} value={summary?.needs_review} label="Need Review"/>
          <Metric icon={<AlertTriangle size={16}/>} value={summary?.invalid_mappings} label="Invalid Mappings"/>
        </div>

        <div style={{ display: "flex", gap: 4, marginBottom: 14, borderBottom: "1px solid var(--border)" }} role="tablist">
          {TABS.map(t => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, border: "none", background: "none",
                borderBottom: `2px solid ${tab === t ? "var(--brand)" : "transparent"}`,
                color: tab === t ? "var(--text-primary)" : "var(--text-secondary)", cursor: "pointer" }}>
              {t === "policies" ? "Policies" : t === "history" ? "Change History" : "Audit"}
            </button>
          ))}
        </div>

        {tab === "policies" && (
          <div style={{ display: "flex", gap: 16 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <Card style={{ padding: 0 }}>
                <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <p style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)", flex: "1 1 200px" }}>Monetization policies</p>
                  <div style={{ position: "relative", flex: "1 1 200px" }}>
                    <Search size={13} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
                    <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search Verticals…"
                      style={{ width: "100%", padding: "6px 10px 6px 28px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                        background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
                  </div>
                  <select value={modelFilter} onChange={e => setModelFilter(e.target.value)}
                    style={{ padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                      background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
                    <option value="">All monetization models</option>
                    {PROVIDER_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>

                {listApi.loading ? (
                  <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading policies…</div>
                ) : filtered.length === 0 ? (
                  <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No verticals match this filter.</div>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                      <thead>
                        <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                          {["Vertical", "Revenue Model", "Provider Charge", "Customer Fee", "Policy Source", "Status", ""].map(h => (
                            <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map(row => {
                          const categoryHref = CATEGORY_WORKSPACE_VERTICALS[row.vertical_key];
                          return (
                          <tr key={row.vertical_key}
                            onClick={() => categoryHref ? router.push(categoryHref) : setSelectedKey(row.vertical_key)}
                            style={{ borderBottom: "1px solid var(--border)", cursor: "pointer",
                              background: selectedRow?.vertical_key === row.vertical_key ? "var(--surface-sunken)" : "transparent",
                              borderLeft: selectedRow?.vertical_key === row.vertical_key ? "3px solid var(--brand)" : "3px solid transparent" }}>
                            <td style={{ padding: "10px 14px", fontWeight: 600 }}>{row.vertical_label}</td>
                            <td style={{ padding: "10px 14px" }}>{row.revenue_model === "NOT_CONFIGURED" ? "Not configured" : row.revenue_model}</td>
                            <td style={{ padding: "10px 14px" }}>{row.provider_charge}</td>
                            <td style={{ padding: "10px 14px" }}>{row.customer_fee}</td>
                            <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{row.policy_source}</td>
                            <td style={{ padding: "10px 14px", display: "flex", gap: 4, alignItems: "center" }}>
                              <Badge variant={row.status === "Active" ? "success" : row.status === "Draft" ? "warning" : "muted"} size="sm">{row.status}</Badge>
                              {row.mapping_invalid && (
                                <span title="Vertical.finance_model tag disagrees with the published policy's revenue model">
                                  <Badge variant="danger" size="sm">Invalid mapping</Badge>
                                </span>
                              )}
                            </td>
                            <td style={{ padding: "10px 14px", textAlign: "right", color: "var(--text-tertiary)" }}>
                              {categoryHref ? <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, color: "var(--brand)" }}>Manage <ArrowUpRight size={12}/></span> : "⋮"}
                            </td>
                          </tr>
                          );
                        })}
                      </tbody>
                    </TableSurface>
                  </div>
                )}
                <div style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-tertiary)" }}>Showing 1 to {filtered.length} of {rows.length} verticals</div>
              </Card>
            </div>

            {selectedRow && (
              <div style={{ width: 380, flexShrink: 0 }}>
                <PolicyDetailPanel row={selectedRow} onChanged={() => listApi.refetch()}/>
              </div>
            )}
          </div>
        )}

        {tab === "history" && <ChangeHistoryTab verticalKey={selectedRow?.vertical_key ?? rows[0]?.vertical_key}/>}
        {tab === "audit" && <AuditTab verticalKey={selectedRow?.vertical_key ?? rows[0]?.vertical_key}/>}
      </div>
    </AdminLayout>
  );
}

function Metric({ icon, value, label }: { icon: React.ReactNode; value: number | undefined; label: string }) {
  return <SummaryCard label={label} value={value ?? "—"} icon={icon} />;
}

function PolicyDetailPanel({ row, onChanged }: { row: MonetizationPolicyRow; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [showPublish, setShowPublish] = useState(false);
  const [reason, setReason] = useState("");
  const [form, setForm] = useState<DraftForm>({});
  const [previewResult, setPreviewResult] = useState<Record<string, unknown> | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  const detailApi = useApi(useCallback(() => verticalMonetizationApi.getDetail(row.vertical_key), [row.vertical_key]), [row.vertical_key]);
  const impactApi = useApi(useCallback(() => verticalMonetizationApi.getImpact(row.vertical_key), [row.vertical_key]), [row.vertical_key]);
  const impact: MonetizationImpact | undefined = impactApi.data;
  const saveDraftAction = useAction((k: string, p: DraftForm) => verticalMonetizationApi.saveDraft(k, p));
  const publishAction = useAction((k: string, r: string) => verticalMonetizationApi.publish(k, r));

  const current = detailApi.data?.current;
  const draft = detailApi.data?.draft;
  const activePolicy = draft ?? current;

  function startEdit() {
    setForm(activePolicy ?? { provider_model: "NONE", customer_fee_model: "NONE", collection_stage: "after_estimate_approval", currency: "INR" });
    setEditing(true);
    setErrors([]);
    setPreviewResult(null);
  }

  async function validateAndPreview() {
    const v = await verticalMonetizationApi.validate(form);
    setErrors(v.errors);
    if (v.errors.length === 0) {
      const p = await verticalMonetizationApi.preview(form, "500");
      setPreviewResult(p);
    }
  }

  async function saveDraft() {
    const result = await saveDraftAction.execute(row.vertical_key, form);
    if (result) { detailApi.refetch(); onChanged(); }
  }

  async function confirmPublish() {
    if (!reason.trim()) return;
    const result = await publishAction.execute(row.vertical_key, reason.trim());
    if (result) { setShowPublish(false); setReason(""); setEditing(false); detailApi.refetch(); onChanged(); }
  }

  return (
    <Card style={{ padding: 16, position: "sticky", top: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{row.vertical_label}</h2>
        <Badge variant={row.is_enabled ? "success" : "muted"} size="sm">{row.is_enabled ? "Active" : "Disabled"}</Badge>
      </div>

      {!editing ? (
        <>
          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "14px 0 8px" }}>Policy summary</p>
          <SummaryRow label="Revenue model" value={current?.provider_model ?? "Not configured"}/>
          <SummaryRow label="Provider settlement" value={row.provider_charge}/>
          <SummaryRow label="Customer fee" value={row.customer_fee}/>
          <SummaryRow label="Pricing ownership" value="Tenant business"/>

          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Catalog impact</p>
          {impactApi.loading ? (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading impact…</p>
          ) : impact ? (
            <>
              <SummaryRow label="Affected service groups" value={String(impact.affected_service_groups)}/>
              <SummaryRow label="Affected master services" value={String(impact.affected_master_services)}/>
              <SummaryRow label="Active providers" value={String(impact.active_providers)}/>
              <SummaryRow label="Active / in-progress jobs"
                value={impact.active_or_in_progress_jobs_available ? String(impact.active_or_in_progress_jobs) : "Not available"}/>
              <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                Existing jobs retain their snapshotted policy version.
              </p>
            </>
          ) : null}

          {current && (
            <>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Safety &amp; scope</p>
              {["Vertical-isolated policy", "No admin service price", "No tier/city/zipcode pricing", "No package onboarding gate", "Audited policy changes"].map(t => (
                <div key={t} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
                  <CheckCircle2 size={12} style={{ color: "var(--success-text)" }}/> {t}
                </div>
              ))}
            </>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
            <Btn variant="primary" size="sm" onClick={startEdit}>Create Draft</Btn>
            <Btn variant="ghost" size="sm" onClick={() => impactApi.refetch()}>Review Impact</Btn>
          </div>
        </>
      ) : (
        <>
          <PolicyEditorForm form={form} setForm={setForm}/>
          {errors.length > 0 && (
            <div style={{ marginTop: 10, padding: "8px 10px", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              {errors.map(e => <p key={e} style={{ fontSize: 11, color: "var(--danger-text)", margin: "2px 0" }}>{e}</p>)}
            </div>
          )}
          {previewResult && (
            <div style={{ marginTop: 10, padding: "10px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "0 0 6px" }}>Policy Preview (₹500 example)</p>
              <SummaryRow label="Customer platform fee" value={`₹${previewResult.customer_platform_fee}`}/>
              <SummaryRow label="Total payable" value={`₹${previewResult.total_payable}`}/>
              <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "6px 0 0" }}>{String(previewResult.note ?? "")}</p>
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <Btn variant="ghost" size="sm" onClick={() => setEditing(false)}>Cancel</Btn>
            <Btn variant="secondary" size="sm" onClick={validateAndPreview}>Validate &amp; Preview</Btn>
            <Btn variant="secondary" size="sm" onClick={saveDraft} disabled={saveDraftAction.loading}>Save Draft</Btn>
            <Btn variant="primary" size="sm" onClick={() => setShowPublish(true)} disabled={errors.length > 0}>Review &amp; Publish</Btn>
          </div>
        </>
      )}

      {showPublish && (
        <div role="dialog" aria-modal="true" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <Card style={{ padding: 20, width: 400 }}>
            <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
              <ShieldCheck size={16}/> Publish {row.vertical_label} policy
            </p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              This creates a new immutable policy version. Existing bookings/quotes keep their snapshotted version.
            </p>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Reason (required)</label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, marginBottom: 14, boxSizing: "border-box" }}/>
            {publishAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "0 0 10px" }}>{publishAction.error}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Btn variant="ghost" size="sm" onClick={() => setShowPublish(false)}>Cancel</Btn>
              <Btn variant="primary" size="sm" disabled={!reason.trim() || publishAction.loading} onClick={confirmPublish}>
                {publishAction.loading ? "Publishing…" : "Confirm Publish"}
              </Btn>
            </div>
          </Card>
        </div>
      )}
    </Card>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function PolicyEditorForm({ form, setForm }: { form: DraftForm; setForm: (f: DraftForm) => void }) {
  const set = (k: keyof MonetizationPolicy, v: unknown) => setForm({ ...form, [k]: v });
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <Field label="Provider charge model">
        <select value={form.provider_model ?? "NONE"} onChange={e => set("provider_model", e.target.value)} style={selectStyle}>
          {PROVIDER_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </Field>
      {form.provider_model === "PERCENTAGE_COMMISSION" && (
        <Field label="Provider percentage"><input type="number" value={form.provider_percentage ?? ""} onChange={e => set("provider_percentage", e.target.value)} style={inputStyle}/></Field>
      )}
      {form.provider_model === "FIXED_COMPLETION_CHARGE" && (
        <Field label="Fixed charge (minor units)"><input type="number" value={form.provider_fixed_amount_minor ?? ""} onChange={e => set("provider_fixed_amount_minor", Number(e.target.value))} style={inputStyle}/></Field>
      )}
      {form.provider_model === "COMPLETION_CREDITS" && (
        <Field label="Credit units per job"><input type="number" value={form.provider_credit_units ?? ""} onChange={e => set("provider_credit_units", Number(e.target.value))} style={inputStyle}/></Field>
      )}

      <Field label="Customer fee model">
        <select value={form.customer_fee_model ?? "NONE"} onChange={e => set("customer_fee_model", e.target.value)} style={selectStyle}>
          {CUSTOMER_FEE_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </Field>
      {(form.customer_fee_model === "PERCENTAGE" || form.customer_fee_model === "PERCENTAGE_WITH_MIN_MAX") && (
        <Field label="Customer fee percentage"><input type="number" value={form.customer_fee_percentage ?? ""} onChange={e => set("customer_fee_percentage", e.target.value)} style={inputStyle}/></Field>
      )}
      {form.customer_fee_model === "FIXED" && (
        <Field label="Fixed fee (minor units)"><input type="number" value={form.customer_fee_fixed_amount_minor ?? ""} onChange={e => set("customer_fee_fixed_amount_minor", Number(e.target.value))} style={inputStyle}/></Field>
      )}
      {form.customer_fee_model === "PERCENTAGE_WITH_MIN_MAX" && (
        <>
          <Field label="Minimum fee (minor units)"><input type="number" value={form.customer_fee_min_minor ?? ""} onChange={e => set("customer_fee_min_minor", Number(e.target.value))} style={inputStyle}/></Field>
          <Field label="Maximum fee (minor units)"><input type="number" value={form.customer_fee_max_minor ?? ""} onChange={e => set("customer_fee_max_minor", Number(e.target.value))} style={inputStyle}/></Field>
        </>
      )}
      {form.customer_fee_model !== "NONE" && (
        <Field label="Collection stage">
          <select value={form.collection_stage ?? "after_estimate_approval"} onChange={e => set("collection_stage", e.target.value)} style={selectStyle}>
            {COLLECTION_STAGES.map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </Field>
      )}
      <Field label="Change summary"><textarea value={form.change_summary ?? ""} onChange={e => set("change_summary", e.target.value)} rows={2} style={{ ...inputStyle, resize: "vertical" }}/></Field>
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: "100%", padding: "7px 9px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box" };
const selectStyle: React.CSSProperties = { ...inputStyle };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
      {label}
      <div style={{ marginTop: 4 }}>{children}</div>
    </label>
  );
}

function ChangeHistoryTab({ verticalKey }: { verticalKey?: string }) {
  const historyApi = useApi(useCallback(() => verticalKey ? verticalMonetizationApi.getHistory(verticalKey) : Promise.resolve({ items: [] }), [verticalKey]), [verticalKey]);
  const items = historyApi.data?.items ?? [];
  return (
    <Card style={{ padding: 0 }}>
      {items.length === 0 ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No policy versions yet for this vertical.</div>
      ) : (
        <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Version", "Status", "Provider Model", "Customer Fee Model", "Published", ""].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(v => (
              <tr key={v.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "9px 14px" }}>v{v.version_number}</td>
                <td style={{ padding: "9px 14px" }}><Badge variant={v.is_current ? "success" : "muted"} size="sm">{v.status}</Badge></td>
                <td style={{ padding: "9px 14px" }}>{v.provider_model}</td>
                <td style={{ padding: "9px 14px" }}>{v.customer_fee_model}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{v.published_at ? new Date(v.published_at).toLocaleString() : "—"}</td>
                <td style={{ padding: "9px 14px" }}></td>
              </tr>
            ))}
          </tbody>
        </TableSurface>
      )}
    </Card>
  );
}

function AuditTab({ verticalKey }: { verticalKey?: string }) {
  const auditApi = useApi(useCallback(() => verticalKey ? verticalMonetizationApi.getAudit(verticalKey) : Promise.resolve({ items: [] }), [verticalKey]), [verticalKey]);
  const items = auditApi.data?.items ?? [];
  return (
    <Card style={{ padding: 0 }}>
      {items.length === 0 ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No monetization policy changes recorded yet.</div>
      ) : (
        <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Action", "Notes", "When"].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(a => (
              <tr key={a.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "9px 14px" }}>{a.action_type}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-secondary)" }}>{a.notes ?? "—"}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{a.created_at ? new Date(a.created_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </TableSurface>
      )}
    </Card>
  );
}
