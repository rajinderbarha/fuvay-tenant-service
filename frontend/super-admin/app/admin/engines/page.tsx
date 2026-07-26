"use client";
import { useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, CardHeader, SectionHeader, Badge, Btn, Skeleton, Modal, DataTable,
} from "../../../components/shared/ui";
import { SummaryCardsRow } from "../../../components/pricing/SummaryCard";
import { useApi } from "../../../hooks/useApi";
import { engineMgmtApi, catalogApi, ServiceOSError } from "../../../lib/api";
import type {
  PlatformEngine,
  EngineSummary,
  EngineImpactPreview,
  EngineHealthOverview,
  EngineHealthCheckItem,
  EnterpriseEnginePermission,
  EnterpriseEngineAuditLog,
  EnterpriseCategoryEngineEntry,
  EnterprisePackageEntitlement,
  EnterpriseTenantOverride,
  EngineDependencyItem,
  CategoryOption,
  CategoryMatrixRow,
  CategoryMatrixSummary,
  CategorySeedPreview,
  CategoryEngineActionPreview,
  CategoryEnginePackageUsageRow,
  CategoryEngineTenantImpactRow,
  CategoryMatrixTemplateOption,
} from "../../../lib/api";
import {
  Cpu, CheckCircle2, XCircle, Activity, ClipboardList, Package,
  Shield, Key, Layers, ChevronRight, Search, Lock, Zap, Eye,
  ToggleLeft, ToggleRight, RefreshCw, Sparkles, Users, AlertTriangle,
} from "lucide-react";

type Tab =
  | "all"
  | "category-matrix"
  | "dependencies"
  | "package-entitlements"
  | "tenant-overrides"
  | "health"
  | "permissions"
  | "audit-logs";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "all",                  label: "All Engines",          icon: <Cpu size={13} /> },
  { id: "category-matrix",      label: "Category Matrix",      icon: <Layers size={13} /> },
  { id: "dependencies",         label: "Dependencies",         icon: <ChevronRight size={13} /> },
  { id: "package-entitlements", label: "Package Entitlements", icon: <Package size={13} /> },
  { id: "tenant-overrides",     label: "Tenant Overrides",     icon: <Shield size={13} /> },
  { id: "health",               label: "Health",               icon: <Activity size={13} /> },
  { id: "permissions",          label: "Permissions",          icon: <Key size={13} /> },
  { id: "audit-logs",           label: "Audit Logs",           icon: <ClipboardList size={13} /> },
];

// ── CSS helpers — all variables from globals.css ───────────────────────────
const TH: React.CSSProperties = {
  padding: "11px 12px", textAlign: "left", fontSize: 11, fontWeight: 700,
  color: "var(--text-tertiary)", letterSpacing: "0.07em", textTransform: "uppercase",
  background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)",
  whiteSpace: "nowrap",
};
const TD: React.CSSProperties = {
  padding: "10px 12px", fontSize: 13, color: "var(--text-primary)",
  borderBottom: "1px solid var(--border)",
};
const filterInput: React.CSSProperties = {
  height: 36, border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13,
  padding: "0 10px", background: "var(--surface)", color: "var(--text-primary)",
  fontFamily: "inherit", outline: "none",
};

function StatusBadge({ status }: { status: string }) {
  const v = status === "enabled" ? "success" : status === "disabled" ? "danger" : "warning";
  return <Badge variant={v}>{status}</Badge>;
}

function HealthDot({ status }: { status: string }) {
  const c = status === "healthy" ? "var(--success)" : status === "degraded" ? "var(--warning)" : "var(--danger)";
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: c, flexShrink: 0 }} />;
}

function SkeletonBlock({ n = 5 }: { n?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: "8px 0" }}>
      {[...Array(n)].map((_, i) => <Skeleton key={i} height={32} />)}
    </div>
  );
}

// ── Impact Preview Modal ────────────────────────────────────────────────────
function ImpactModal({
  open, preview, engineKey, action, onConfirm, onClose, loading,
}: {
  open: boolean; preview: EngineImpactPreview | null; engineKey: string;
  action: "enable" | "disable"; onConfirm: (reason: string) => void;
  onClose: () => void; loading: boolean;
}) {
  const [reason, setReason] = useState("");
  if (!preview) return null;
  const riskColor = preview.risk_level === "high" ? "danger" : preview.risk_level === "medium" ? "warning" : "default";
  return (
    <Modal open={open} onClose={onClose} title={`${action === "enable" ? "Enable" : "Disable"} Engine — ${engineKey}`}>
      {!preview.can_proceed && (
        <div style={{ padding: "12px 14px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", marginBottom: 14 }}>
          <p style={{ color: "var(--danger-text)", fontSize: 13, fontWeight: 600, margin: "0 0 6px" }}>Cannot Proceed</p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--danger-text)" }}>
            {(preview.blockers || []).map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
      )}
      {(preview.warnings || []).length > 0 && (
        <div style={{ padding: "12px 14px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)", marginBottom: 14 }}>
          <p style={{ color: "var(--warning-text)", fontSize: 13, fontWeight: 600, margin: "0 0 6px" }}>Warnings</p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--warning-text)" }}>
            {(preview.warnings || []).map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 14, fontSize: 13, color: "var(--text-secondary)" }}>
        <span>Impact: <strong style={{ color: "var(--text-primary)" }}>{preview.categories_affected}</strong> categories, <strong style={{ color: "var(--text-primary)" }}>{preview.packages_affected}</strong> packages</span>
        <Badge variant={riskColor as "default" | "warning" | "danger"}>{preview.risk_level} risk</Badge>
      </div>
      <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
        Reason {action === "disable" ? <span style={{ color: "var(--danger)" }}>*</span> : "(optional)"}
      </label>
      <textarea
        value={reason}
        onChange={e => setReason(e.target.value)}
        rows={2}
        placeholder={`Reason for ${action}…`}
        style={{ width: "100%", fontSize: 13, padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", resize: "vertical", boxSizing: "border-box" }}
      />
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn
          variant={action === "enable" ? "success" : "danger"}
          onClick={() => onConfirm(reason)}
          disabled={!preview.can_proceed || loading || (action === "disable" && !reason.trim())}
          loading={loading}
        >
          Confirm {action}
        </Btn>
      </div>
    </Modal>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: ALL ENGINES
// ══════════════════════════════════════════════════════════════════════════════
function EngineCard({ eng, onEnable, onDisable }: {
  eng: PlatformEngine; onEnable: () => void; onDisable: () => void;
}) {
  return (
    <div style={{
      border: "1px solid var(--border)", borderRadius: 10, padding: 14,
      background: "var(--surface)", display: "flex", flexDirection: "column", gap: 10,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {eng.is_locked && <Lock size={12} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />}
            <Link href={`/admin/engines/${eng.engine_key}`} style={{
              fontWeight: 600, fontSize: 14, textDecoration: "none", color: "var(--text-link)",
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>
              {eng.display_name}
            </Link>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
            {eng.engine_key}
          </div>
        </div>
        <StatusBadge status={eng.global_status} />
      </div>

      {eng.description && (
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const }}>
          {eng.description}
        </p>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        <Badge variant="muted">{eng.engine_type}</Badge>
        {eng.is_core && <Badge variant="default">Core</Badge>}
      </div>

      <div style={{ display: "flex", gap: 14, fontSize: 11, color: "var(--text-secondary)", paddingTop: 8, borderTop: "1px solid var(--border)" }}>
        <span>Deps <strong style={{ color: "var(--text-primary)" }}>{eng.dependencies?.length ?? 0}</strong></span>
        <span>Categories <strong style={{ color: "var(--text-primary)" }}>{eng.category_usage_count ?? 0}</strong></span>
        <span>Overrides <strong style={{ color: "var(--text-primary)" }}>{eng.active_overrides ?? 0}</strong></span>
      </div>

      <div style={{ display: "flex", gap: 6 }}>
        <Link href={`/admin/engines/${eng.engine_key}`} style={{ flex: 1 }}>
          <Btn size="xs" variant="secondary" style={{ width: "100%" }}><Eye size={11} style={{ marginRight: 4 }} />View</Btn>
        </Link>
        {!eng.is_locked && (
          eng.global_status !== "enabled" ? (
            <Btn size="xs" variant="success" onClick={onEnable} style={{ flex: 1 }}>
              <ToggleRight size={11} style={{ marginRight: 4 }} />Enable
            </Btn>
          ) : (
            <Btn size="xs" variant="danger" onClick={onDisable} style={{ flex: 1 }}>
              <ToggleLeft size={11} style={{ marginRight: 4 }} />Disable
            </Btn>
          )
        )}
      </div>
    </div>
  );
}

function AllEnginesTab({ summary }: { summary: EngineSummary | null }) {
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [view, setView] = useState<"table" | "cards">("table");

  const engines = useApi(useCallback(() =>
    engineMgmtApi.list({ q: q || undefined, engine_type: typeFilter || undefined, global_status: statusFilter || undefined, page, limit: 50 }),
    [q, typeFilter, statusFilter, page]), [q, typeFilter, statusFilter, page]);

  const [impactModal, setImpactModal] = useState<{ engineKey: string; action: "enable" | "disable" } | null>(null);
  const [impactPreview, setImpactPreview] = useState<EngineImpactPreview | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  async function openImpact(engineKey: string, action: "enable" | "disable") {
    setImpactLoading(true);
    setImpactModal({ engineKey, action });
    try {
      const res = await engineMgmtApi.impactPreview(engineKey, action);
      setImpactPreview(res as unknown as EngineImpactPreview);
    } finally {
      setImpactLoading(false);
    }
  }

  async function confirmAction(reason: string) {
    if (!impactModal) return;
    setActionLoading(true);
    try {
      if (impactModal.action === "enable") await engineMgmtApi.enableGlobally(impactModal.engineKey, reason);
      else await engineMgmtApi.disableGlobally(impactModal.engineKey, reason);
      engines.refetch();
      setImpactModal(null);
      setImpactPreview(null);
    } finally {
      setActionLoading(false);
    }
  }

  const rows = engines.data?.engines ?? [];
  const meta = engines.data?.meta;

  return (
    <div>
      {summary && (
        <SummaryCardsRow cards={[
          { label: "Total", value: summary.total_engines },
          { label: "Enabled", value: summary.enabled_globally, accent: true },
          { label: "Disabled", value: summary.disabled },
          { label: "Core / Locked", value: summary.core_locked },
          { label: "Beta", value: summary.beta_engines },
        ]} />
      )}

      <Card>
        {/* Filters */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }} />
            <input
              value={q}
              onChange={e => { setQ(e.target.value); setPage(1); }}
              placeholder="Search engines…"
              style={{ ...filterInput, width: "100%", paddingLeft: 32, boxSizing: "border-box" }}
            />
          </div>
          <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }} style={filterInput}>
            <option value="">All Types</option>
            <option value="core">Core</option>
            <option value="plugin">Plugin</option>
            <option value="finance">Finance</option>
            <option value="ops">Ops</option>
            <option value="vertical">Vertical</option>
            <option value="ai">AI</option>
            <option value="compliance">Compliance</option>
          </select>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} style={filterInput}>
            <option value="">All Statuses</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
            <option value="locked">Locked</option>
          </select>
          <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", overflow: "hidden" }}>
            <button onClick={() => setView("table")} style={{
              padding: "0 12px", height: 36, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
              background: view === "table" ? "var(--accent)" : "var(--surface)",
              color: view === "table" ? "#fff" : "var(--text-secondary)",
            }}>Table</button>
            <button onClick={() => setView("cards")} style={{
              padding: "0 12px", height: 36, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
              background: view === "cards" ? "var(--accent)" : "var(--surface)",
              color: view === "cards" ? "#fff" : "var(--text-secondary)",
              borderLeft: "1px solid var(--border)",
            }}>Cards</button>
          </div>
        </div>

        {engines.loading && <SkeletonBlock />}
        {engines.error && (
          <div style={{ padding: "16px", background: "var(--danger-bg)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--danger-text)" }}>
            Failed to load engines.
          </div>
        )}
        {!engines.loading && !engines.error && view === "cards" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
            {rows.map(eng => (
              <EngineCard
                key={eng.id} eng={eng}
                onEnable={() => openImpact(eng.engine_key, "enable")}
                onDisable={() => openImpact(eng.engine_key, "disable")}
              />
            ))}
            {rows.length === 0 && (
              <div style={{ gridColumn: "1 / -1", padding: "48px 16px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
                No engines found.
              </div>
            )}
          </div>
        )}
        {!engines.loading && !engines.error && view === "table" && (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Engine", "Type", "Status", "Core", "Deps", "Categories", "Overrides", "Actions"].map(h => (
                    <th key={h} style={TH}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map(eng => (
                  <tr key={eng.id} style={{ background: "transparent", transition: "background 0.1s" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                    <td style={TD}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {eng.is_locked && <Lock size={12} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />}
                        <div>
                          <Link href={`/admin/engines/${eng.engine_key}`} style={{ fontWeight: 600, textDecoration: "none", color: "var(--text-link)", fontSize: 13 }}>
                            {eng.display_name}
                          </Link>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "JetBrains Mono, monospace", marginTop: 1 }}>{eng.engine_key}</div>
                        </div>
                      </div>
                    </td>
                    <td style={TD}><Badge variant="muted">{eng.engine_type}</Badge></td>
                    <td style={TD}><StatusBadge status={eng.global_status} /></td>
                    <td style={TD}>
                      {eng.is_core ? <CheckCircle2 size={15} style={{ color: "var(--success)" }} /> : <span style={{ color: "var(--text-tertiary)" }}>—</span>}
                    </td>
                    <td style={{ ...TD, color: "var(--text-secondary)", textAlign: "center" }}>{eng.dependencies?.length ?? 0}</td>
                    <td style={{ ...TD, color: "var(--text-secondary)", textAlign: "center" }}>{eng.category_usage_count ?? 0}</td>
                    <td style={{ ...TD, color: "var(--text-secondary)", textAlign: "center" }}>{eng.active_overrides ?? 0}</td>
                    <td style={{ ...TD, borderBottom: TD.borderBottom }}>
                      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <Link href={`/admin/engines/${eng.engine_key}`}>
                          <Btn size="xs" variant="ghost"><Eye size={11} /></Btn>
                        </Link>
                        {!eng.is_locked && (
                          eng.global_status !== "enabled" ? (
                            <Btn size="xs" variant="success" onClick={() => openImpact(eng.engine_key, "enable")}>
                              <ToggleRight size={11} style={{ marginRight: 3 }} />Enable
                            </Btn>
                          ) : (
                            <Btn size="xs" variant="danger" onClick={() => openImpact(eng.engine_key, "disable")}>
                              <ToggleLeft size={11} style={{ marginRight: 3 }} />Disable
                            </Btn>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ padding: "48px 16px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
                      No engines found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {meta && meta.total_pages > 1 && (
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center", marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <Btn size="xs" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</Btn>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page} of {meta.total_pages}</span>
            <Btn size="xs" variant="secondary" disabled={page >= meta.total_pages} onClick={() => setPage(p => p + 1)}>Next →</Btn>
          </div>
        )}
      </Card>

      <ImpactModal
        open={!!impactModal}
        preview={impactPreview}
        engineKey={impactModal?.engineKey ?? ""}
        action={impactModal?.action ?? "disable"}
        onConfirm={confirmAction}
        onClose={() => { setImpactModal(null); setImpactPreview(null); }}
        loading={actionLoading || impactLoading}
      />
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: CATEGORY MATRIX
// ══════════════════════════════════════════════════════════════════════════════

function RecommendationBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; variant: "default" | "muted" | "warning" }> = {
    required: { label: "Required", variant: "default" },
    optional: { label: "Optional", variant: "muted" },
    not_recommended: { label: "Not Recommended", variant: "warning" },
    not_applicable: { label: "Not Applicable", variant: "muted" },
  };
  const m = map[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={m.variant}>{m.label}</Badge>;
}

function RiskBadge({ risk }: { risk: string }) {
  const variant = risk === "blocked" ? "danger" : risk === "high" ? "danger" : risk === "medium" ? "warning" : "success";
  return <Badge variant={variant}>{risk}</Badge>;
}

// Category Selector — searchable, no raw UUID entry
function CategorySelector({ value, onChange }: { value: CategoryOption | null; onChange: (c: CategoryOption) => void }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const opts = useApi(useCallback(() => catalogApi.getCategoryOptions({ q: q || undefined }), [q]), [q]);

  return (
    <div style={{ position: "relative", width: 320 }}>
      <div style={{ position: "relative" }}>
        <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }} />
        <input
          value={open ? q : (value ? `${value.name} · ${value.vertical_type ?? "—"} · ${value.status}` : q)}
          onChange={e => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder="Search category by name, slug, or vertical…"
          style={{ ...filterInput, width: "100%", paddingLeft: 32, boxSizing: "border-box" }}
        />
      </div>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 20,
          background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
          boxShadow: "var(--shadow-md)", maxHeight: 280, overflowY: "auto",
        }}>
          {opts.loading && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Searching…</div>}
          {!opts.loading && (opts.data ?? []).map(c => (
            <div key={c.id}
              onClick={() => { onChange(c); setOpen(false); setQ(""); }}
              style={{ padding: "9px 12px", cursor: "pointer", fontSize: 13, borderBottom: "1px solid var(--border)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{c.name}</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                {c.slug} · {c.vertical_type ?? "no vertical"} · {c.status}
              </div>
            </div>
          ))}
          {!opts.loading && (opts.data ?? []).length === 0 && (
            <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>No categories match.</div>
          )}
        </div>
      )}
    </div>
  );
}

function SeedPreviewModal({
  open, preview, loading, onClose, onConfirm, confirmLoading,
  needsTemplatePick, templates, templatesLoading, selectedTemplate, onSelectTemplate, onLoadPreview,
}: {
  open: boolean; preview: CategorySeedPreview | null; loading: boolean;
  onClose: () => void; onConfirm: () => void; confirmLoading: boolean;
  needsTemplatePick: boolean; templates: CategoryMatrixTemplateOption[]; templatesLoading: boolean;
  selectedTemplate: string; onSelectTemplate: (key: string) => void; onLoadPreview: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title="Seed Recommended Engine Matrix">
      {needsTemplatePick && (
        <div>
          <div style={{ padding: "10px 12px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)", marginBottom: 14 }}>
            <p style={{ fontSize: 13, color: "var(--warning-text)", margin: 0 }}>
              No recommended template is mapped to this category's vertical automatically. Pick one of the
              available templates below, or create mappings manually from the matrix table.
            </p>
          </div>
          {templatesLoading && <SkeletonBlock n={3} />}
          {!templatesLoading && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
              {templates.map(t => (
                <label key={t.key} style={{
                  display: "flex", alignItems: "center", gap: 10, padding: "10px 12px",
                  border: `1px solid ${selectedTemplate === t.key ? "var(--accent)" : "var(--border)"}`,
                  borderRadius:"var(--radius-md)", cursor: "pointer",
                  background: selectedTemplate === t.key ? "var(--surface-sunken)" : "transparent",
                }}>
                  <input type="radio" name="seed-template" checked={selectedTemplate === t.key} onChange={() => onSelectTemplate(t.key)} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{t.key}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                      vertical: {t.vertical_type} · {t.required_count} required · {t.optional_count} optional
                    </div>
                  </div>
                </label>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
            <Btn variant="success" onClick={onLoadPreview} disabled={!selectedTemplate}>Load Preview</Btn>
          </div>
        </div>
      )}
      {!needsTemplatePick && loading && <SkeletonBlock n={4} />}
      {!needsTemplatePick && !loading && preview && (
        <div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
            Template <Badge variant="muted">{preview.template}</Badge> will create{" "}
            <strong>{preview.will_create}</strong> new category engine mapping(s) for <strong>{preview.category}</strong>.
          </p>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 6 }}>Required Engines</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {preview.required_engines.map(k => <Badge key={k} variant="default">{k}</Badge>)}
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 6 }}>Optional Engines</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {preview.optional_engines.map(k => <Badge key={k} variant="muted">{k}</Badge>)}
            </div>
          </div>
          {preview.warnings.length > 0 && (
            <div style={{ padding: "10px 12px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)", marginBottom: 12 }}>
              {preview.warnings.map((w, i) => <div key={i} style={{ fontSize: 12, color: "var(--warning-text)" }}>{w}</div>)}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
            <Btn variant="success" onClick={onConfirm} loading={confirmLoading} disabled={preview.will_create === 0}>
              Confirm Seed Defaults
            </Btn>
          </div>
        </div>
      )}
    </Modal>
  );
}

function ActionPreviewModal({
  open, preview, action, loading, onClose, onConfirm, confirmLoading,
}: {
  open: boolean; preview: CategoryEngineActionPreview | null; action: "enable" | "disable";
  loading: boolean; onClose: () => void; onConfirm: (reason: string, force: boolean) => void;
  confirmLoading: boolean;
}) {
  const [reason, setReason] = useState("");
  return (
    <Modal open={open} onClose={onClose} title={`${action === "enable" ? "Enable" : "Disable"} Engine For Category`}>
      {loading && <SkeletonBlock n={3} />}
      {!loading && preview && (
        <div>
          {preview.blocked && (
            <div style={{ padding: "10px 12px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <AlertTriangle size={14} style={{ color: "var(--danger)" }} />
                <strong style={{ fontSize: 13, color: "var(--danger-text)" }}>Blocked</strong>
              </div>
              {preview.blockers.map((b, i) => <div key={i} style={{ fontSize: 12, color: "var(--danger-text)" }}>{b}</div>)}
            </div>
          )}
          {preview.missing_dependencies.length > 0 && (
            <div style={{ padding: "10px 12px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)", marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "var(--warning-text)" }}>Missing dependencies: {preview.missing_dependencies.join(", ")}</div>
            </div>
          )}
          <div style={{ display: "flex", gap: 12, marginBottom: 10, fontSize: 13, color: "var(--text-secondary)" }}>
            <span>Packages affected: <strong style={{ color: "var(--text-primary)" }}>{preview.affected_packages}</strong></span>
            <span>Tenants affected: <strong style={{ color: "var(--text-primary)" }}>{preview.affected_tenants}</strong></span>
            <RiskBadge risk={preview.risk_level} />
          </div>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 10 }}>{preview.recommendation}</p>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
            Reason {action === "disable" ? <span style={{ color: "var(--danger)" }}>*</span> : "(optional)"}
          </label>
          <textarea
            value={reason} onChange={e => setReason(e.target.value)} rows={2}
            placeholder={`Reason to ${action} this engine for the category…`}
            style={{ width: "100%", fontSize: 13, padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", boxSizing: "border-box" }}
          />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 14 }}>
            <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
            <Btn
              variant={action === "enable" ? "success" : "danger"}
              onClick={() => onConfirm(reason, preview.blocked)}
              disabled={confirmLoading || (preview.blocked ? false : (action === "disable" && !reason.trim()))}
              loading={confirmLoading}
            >
              {preview.blocked ? `Force ${action}` : `Confirm ${action}`}
            </Btn>
          </div>
        </div>
      )}
    </Modal>
  );
}

function PackageUsageDrawer({ open, categoryId, engineKey, onClose }: { open: boolean; categoryId: string | null; engineKey: string | null; onClose: () => void }) {
  const data = useApi(useCallback(() =>
    categoryId && engineKey ? engineMgmtApi.getCategoryEnginePackageUsage(categoryId, engineKey) : Promise.resolve({ packages: [], total: 0 }),
    [categoryId, engineKey]), [categoryId, engineKey]);
  const rows = data.data?.packages ?? [];
  return (
    <Modal open={open} onClose={onClose} title={`Packages Using ${engineKey ?? ""}`}>
      {data.loading && <SkeletonBlock n={3} />}
      {!data.loading && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>{["Package", "Type", "Status", "Tenants", "Included", "Required"].map(h => <th key={h} style={TH}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((p: CategoryEnginePackageUsageRow) => (
                <tr key={p.package_id}>
                  <td style={TD}>{p.package_name}</td>
                  <td style={TD}><Badge variant="muted">{p.package_type}</Badge></td>
                  <td style={TD}><Badge variant={p.status === "active" ? "success" : "muted"}>{p.status}</Badge></td>
                  <td style={TD}>{p.tenant_count}</td>
                  <td style={TD}>{p.engine_included ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} /> : <XCircle size={14} style={{ color: "var(--text-tertiary)" }} />}</td>
                  <td style={TD}>{p.required ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} /> : "—"}</td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No packages use this engine for this category's vertical.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

function TenantImpactDrawer({ open, categoryId, engineKey, onClose }: { open: boolean; categoryId: string | null; engineKey: string | null; onClose: () => void }) {
  const data = useApi(useCallback(() =>
    categoryId && engineKey ? engineMgmtApi.getCategoryEngineTenantImpact(categoryId, engineKey) : Promise.resolve({ tenants: [], total: 0 }),
    [categoryId, engineKey]), [categoryId, engineKey]);
  const rows = data.data?.tenants ?? [];
  return (
    <Modal open={open} onClose={onClose} title={`Tenant Impact — ${engineKey ?? ""}`}>
      {data.loading && <SkeletonBlock n={3} />}
      {!data.loading && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>{["Tenant", "Plan", "Status", "Runtime Access", "Override", "Risk"].map(h => <th key={h} style={TH}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((t: CategoryEngineTenantImpactRow) => (
                <tr key={t.tenant_id}>
                  <td style={TD}>{t.tenant_name}</td>
                  <td style={TD}><Badge variant="muted">{t.plan_type}</Badge></td>
                  <td style={TD}><Badge variant={t.status === "active" ? "success" : "muted"}>{t.status}</Badge></td>
                  <td style={TD}>{t.runtime_access === null ? "—" : t.runtime_access ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} /> : <XCircle size={14} style={{ color: "var(--danger)" }} />}</td>
                  <td style={TD}>{t.override ?? "—"}</td>
                  <td style={TD}><Badge variant={t.risk === "low" ? "success" : "muted"}>{t.risk}</Badge></td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No tenants are on this category.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

function CategoryMatrixTab() {
  const [category, setCategory] = useState<CategoryOption | null>(null);
  const [requiredOnly, setRequiredOnly] = useState(false);
  const [missingDepsOnly, setMissingDepsOnly] = useState(false);

  const detail = useApi(useCallback(() =>
    category ? engineMgmtApi.getCategoryMatrixDetail(category.id) : Promise.resolve(null),
    [category]), [category]);
  const summary = useApi(useCallback(() =>
    category ? engineMgmtApi.getCategoryMatrixSummary(category.id) : Promise.resolve(null),
    [category]), [category]);
  const engines = useApi(useCallback(() => engineMgmtApi.list({ limit: 200 }), []), []);
  const engineLookup = useMemo(() => {
    const m: Record<string, PlatformEngine> = {};
    (engines.data?.engines ?? []).forEach(e => { m[e.engine_key] = e; });
    return m;
  }, [engines.data]);

  const [seedModal, setSeedModal] = useState(false);
  const [seedPreview, setSeedPreview] = useState<CategorySeedPreview | null>(null);
  const [seedLoading, setSeedLoading] = useState(false);
  const [seedConfirming, setSeedConfirming] = useState(false);
  const [seedNeedsPick, setSeedNeedsPick] = useState(false);
  const [seedTemplates, setSeedTemplates] = useState<CategoryMatrixTemplateOption[]>([]);
  const [seedTemplatesLoading, setSeedTemplatesLoading] = useState(false);
  const [seedSelectedTemplate, setSeedSelectedTemplate] = useState("");

  const [actionModal, setActionModal] = useState<{ engineKey: string; action: "enable" | "disable" } | null>(null);
  const [actionPreview, setActionPreview] = useState<CategoryEngineActionPreview | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionConfirming, setActionConfirming] = useState(false);

  const [packageDrawer, setPackageDrawer] = useState<string | null>(null);
  const [tenantDrawer, setTenantDrawer] = useState<string | null>(null);

  async function openSeedPreview() {
    if (!category) return;
    setSeedModal(true); setSeedLoading(true); setSeedNeedsPick(false);
    try {
      const p = await engineMgmtApi.seedCategoryDefaultsPreview(category.id);
      setSeedPreview(p);
    } catch (e) {
      if (e instanceof ServiceOSError && e.code === "VALIDATION_ERROR") {
        setSeedNeedsPick(true);
        setSeedTemplatesLoading(true);
        try {
          const t = await engineMgmtApi.getCategoryMatrixTemplates();
          setSeedTemplates(t.templates);
        } finally { setSeedTemplatesLoading(false); }
      } else {
        setSeedModal(false);
        throw e;
      }
    } finally { setSeedLoading(false); }
  }

  async function loadPreviewForSelectedTemplate() {
    if (!category || !seedSelectedTemplate) return;
    setSeedLoading(true);
    try {
      const p = await engineMgmtApi.seedCategoryDefaultsPreview(category.id, seedSelectedTemplate);
      setSeedPreview(p);
      setSeedNeedsPick(false);
    } finally { setSeedLoading(false); }
  }

  async function confirmSeed() {
    if (!category || !seedPreview) return;
    setSeedConfirming(true);
    try {
      await engineMgmtApi.seedCategoryDefaults(category.id, seedPreview.template);
      setSeedModal(false); setSeedPreview(null); setSeedNeedsPick(false); setSeedSelectedTemplate("");
      detail.refetch(); summary.refetch();
    } finally { setSeedConfirming(false); }
  }

  async function openActionPreview(engineKey: string, action: "enable" | "disable") {
    if (!category) return;
    setActionModal({ engineKey, action }); setActionLoading(true);
    try {
      const p = action === "enable"
        ? await engineMgmtApi.categoryEngineEnablePreview(category.id, engineKey)
        : await engineMgmtApi.categoryEngineDisablePreview(category.id, engineKey);
      setActionPreview(p);
    } finally { setActionLoading(false); }
  }

  async function confirmAction(reason: string, force: boolean) {
    if (!category || !actionModal) return;
    setActionConfirming(true);
    try {
      if (actionModal.action === "enable") {
        await engineMgmtApi.enableCategoryEngine(category.id, actionModal.engineKey, reason, force);
      } else {
        await engineMgmtApi.disableCategoryEngine(category.id, actionModal.engineKey, reason, force);
      }
      setActionModal(null); setActionPreview(null);
      detail.refetch(); summary.refetch();
    } finally { setActionConfirming(false); }
  }

  async function markRequired(engineKey: string) {
    if (!category) return;
    await engineMgmtApi.markCategoryEngineRequired(category.id, engineKey, "Marked required from Category Matrix");
    detail.refetch(); summary.refetch();
  }
  async function markOptional(engineKey: string) {
    if (!category) return;
    await engineMgmtApi.markCategoryEngineOptional(category.id, engineKey, "Marked optional from Category Matrix");
    detail.refetch(); summary.refetch();
  }

  const allRows = detail.data?.rows ?? [];
  const rows = allRows.filter(r => {
    if (requiredOnly && !r.is_required) return false;
    if (missingDepsOnly && r.dependency_status !== "missing") return false;
    return true;
  });
  const s = summary.data;

  return (
    <div>
      <Card>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Category</label>
            <CategorySelector value={category} onChange={setCategory} />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", paddingBottom: 9 }}>
            <input type="checkbox" checked={requiredOnly} onChange={e => setRequiredOnly(e.target.checked)} />
            Show required only
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", paddingBottom: 9 }}>
            <input type="checkbox" checked={missingDepsOnly} onChange={e => setMissingDepsOnly(e.target.checked)} />
            Show missing dependencies only
          </label>
          <div style={{ flex: 1 }} />
          <Btn variant="secondary" size="sm" onClick={() => { detail.refetch(); summary.refetch(); }}>
            <RefreshCw size={13} style={{ marginRight: 6 }} />Refresh
          </Btn>
        </div>

        {!category && (
          <div style={{ padding: "48px 0", textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
            Select a category to view its engine matrix.
          </div>
        )}

        {category && (
          <>
            {s && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>
                  <strong style={{ color: "var(--text-primary)" }}>{s.category.name}</strong>
                  {" · "}{s.category.vertical_type ?? "no vertical"}
                  {" · "}{s.category.customer_flow_type ?? "no flow"}
                  {" · "}{s.category.finance_model ?? "no finance model"}
                  {" · "}<Badge variant={s.category.status === "active" ? "success" : "muted"}>{s.category.status}</Badge>
                </div>
                <SummaryCardsRow cards={[
                  { label: "Total Engines", value: s.total_engines },
                  { label: "Enabled", value: s.enabled_engines, accent: true },
                  { label: "Required", value: s.required_engines },
                  { label: "Optional", value: s.optional_engines },
                  { label: "Missing Deps", value: s.missing_dependencies },
                  { label: "Used By Packages", value: s.used_by_packages },
                  { label: "Used By Tenants", value: s.used_by_tenants },
                  { label: "Blocked Actions", value: s.blocked_actions },
                ]} />
              </div>
            )}

            {detail.loading && <SkeletonBlock />}

            {!detail.loading && allRows.length === 0 && (
              <div style={{ padding: "40px 20px", textAlign: "center", border: "1px dashed var(--border)", borderRadius: 10 }}>
                <Sparkles size={22} style={{ color: "var(--accent)", marginBottom: 8 }} />
                <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
                  No engine mappings found for {category.name}.
                </p>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 14px" }}>
                  Seed the recommended engine matrix to make this category runtime-ready.
                </p>
                <Btn variant="success" onClick={openSeedPreview}>
                  <Zap size={13} style={{ marginRight: 6 }} />Seed Recommended Defaults
                </Btn>
              </div>
            )}

            {!detail.loading && allRows.length > 0 && (
              <>
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
                  <Btn variant="secondary" size="sm" onClick={openSeedPreview}>
                    <Zap size={12} style={{ marginRight: 6 }} />Seed Missing Defaults
                  </Btn>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr>
                        {["Engine", "Required", "Enabled", "Dependencies", "Package Usage", "Tenant Impact", "Runtime Risk", "Actions"].map(h => (
                          <th key={h} style={TH}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row: CategoryMatrixRow) => {
                        const eng = engineLookup[row.engine_key];
                        return (
                          <tr key={row.id}>
                            <td style={TD}>
                              <div style={{ fontWeight: 600, fontSize: 13 }} title={eng?.description ?? ""}>
                                {eng?.display_name ?? row.engine_key}
                              </div>
                              <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{row.engine_key}</div>
                            </td>
                            <td style={TD}><RecommendationBadge status={row.recommendation_status} /></td>
                            <td style={TD}>
                              {row.is_enabled
                                ? <Badge variant="success">Enabled</Badge>
                                : <Badge variant="muted">Disabled</Badge>}
                            </td>
                            <td style={TD}>
                              {row.dependency_status === "met" && <Badge variant="success">Met</Badge>}
                              {row.dependency_status === "missing" && (
                                <Badge variant="danger">Missing: {row.missing_dependencies.join(", ")}</Badge>
                              )}
                              {row.dependency_status === "not_checked" && <Badge variant="muted">Not required</Badge>}
                            </td>
                            <td style={TD}>
                              <button onClick={() => setPackageDrawer(row.engine_key)} style={{ background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontSize: 12, padding: 0 }}>
                                {row.package_usage_count} package(s)
                              </button>
                            </td>
                            <td style={TD}>
                              <button onClick={() => setTenantDrawer(row.engine_key)} style={{ background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontSize: 12, padding: 0 }}>
                                {row.tenant_impact_count} tenant(s)
                              </button>
                            </td>
                            <td style={TD}><RiskBadge risk={row.runtime_risk} /></td>
                            <td style={TD}>
                              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                                {!row.is_enabled ? (
                                  <Btn size="xs" variant="success" onClick={() => openActionPreview(row.engine_key, "enable")}>Enable for Category</Btn>
                                ) : (
                                  <Btn size="xs" variant="danger" onClick={() => openActionPreview(row.engine_key, "disable")}>Disable for Category</Btn>
                                )}
                                {row.is_required
                                  ? <Btn size="xs" variant="secondary" onClick={() => markOptional(row.engine_key)}>Mark Optional</Btn>
                                  : <Btn size="xs" variant="secondary" onClick={() => markRequired(row.engine_key)}>Mark Required</Btn>}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                      {rows.length === 0 && (
                        <tr><td colSpan={8} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No engines match the current filters.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </Card>

      <SeedPreviewModal
        open={seedModal} preview={seedPreview} loading={seedLoading}
        onClose={() => { setSeedModal(false); setSeedPreview(null); setSeedNeedsPick(false); setSeedSelectedTemplate(""); }}
        onConfirm={confirmSeed} confirmLoading={seedConfirming}
        needsTemplatePick={seedNeedsPick} templates={seedTemplates} templatesLoading={seedTemplatesLoading}
        selectedTemplate={seedSelectedTemplate} onSelectTemplate={setSeedSelectedTemplate}
        onLoadPreview={loadPreviewForSelectedTemplate}
      />
      <ActionPreviewModal
        open={!!actionModal} preview={actionPreview} action={actionModal?.action ?? "enable"}
        loading={actionLoading}
        onClose={() => { setActionModal(null); setActionPreview(null); }}
        onConfirm={confirmAction} confirmLoading={actionConfirming}
      />
      <PackageUsageDrawer
        open={!!packageDrawer} categoryId={category?.id ?? null} engineKey={packageDrawer}
        onClose={() => setPackageDrawer(null)}
      />
      <TenantImpactDrawer
        open={!!tenantDrawer} categoryId={category?.id ?? null} engineKey={tenantDrawer}
        onClose={() => setTenantDrawer(null)}
      />
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: DEPENDENCIES
// ══════════════════════════════════════════════════════════════════════════════
function DependenciesTab() {
  const deps = useApi(useCallback(() => engineMgmtApi.getDependencies(), []), []);
  const graph = useApi(useCallback(() => engineMgmtApi.getDependencyGraph(), []), []);
  const rows = (deps.data?.dependencies ?? []) as EngineDependencyItem[];
  const blockedEnables = (graph.data?.blocked_enables ?? []) as { engine_key: string; blocked_by: string }[];

  return (
    <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
      <Card style={{ flex: "1 1 400px" }}>
        <CardHeader title="Dependency Map" subtitle={`${rows.length} active dependencies`} />
        {deps.loading && <SkeletonBlock />}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Engine", "Depends On", "Type", "Active"].map(h => <th key={h} style={TH}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((d, i) => (
                <tr key={i}>
                  <td style={TD}><span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{d.engine_key}</span></td>
                  <td style={TD}>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{d.depends_on_engine_key}</span>
                  </td>
                  <td style={TD}><Badge variant={d.dependency_type === "required" ? "default" : "muted"}>{d.dependency_type}</Badge></td>
                  <td style={TD}>
                    {d.status === "active" ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} /> : <XCircle size={14} style={{ color: "var(--text-tertiary)" }} />}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && !deps.loading && (
                <tr><td colSpan={4} style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>No dependencies configured.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card style={{ flex: "0 0 280px" }}>
        <CardHeader title="Blocked Enables" subtitle="Engines blocked by disabled dependencies" />
        {graph.loading ? <SkeletonBlock n={3} /> : (
          <div>
            {blockedEnables.length === 0 ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 0", color: "var(--success-text)", fontSize: 13, fontWeight: 500 }}>
                <CheckCircle2 size={16} /> All dependencies healthy
              </div>
            ) : (
              blockedEnables.map((b, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "flex-start", gap: 8, padding: "10px 0",
                  borderBottom: "1px solid var(--border)", fontSize: 13,
                }}>
                  <XCircle size={14} style={{ color: "var(--danger)", flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600 }}>{b.engine_key}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>blocked by {b.blocked_by}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: PACKAGE ENTITLEMENTS
// ══════════════════════════════════════════════════════════════════════════════
function PackageEntitlementsTab() {
  const entitlements = useApi(useCallback(() => engineMgmtApi.getPackageEntitlements(), []), []);
  const rows = entitlements.data?.entitlements ?? [];

  const grouped = useMemo(() => {
    const m: Record<string, EnterprisePackageEntitlement[]> = {};
    rows.forEach(r => {
      if (!m[r.package_id]) m[r.package_id] = [];
      m[r.package_id].push(r);
    });
    return m;
  }, [rows]);

  return (
    <Card>
      <CardHeader title="Package Engine Entitlements" subtitle="Engines available per package tier" />
      {entitlements.loading && <SkeletonBlock />}
      {!entitlements.loading && Object.entries(grouped).map(([pkgId, items]) => (
        <div key={pkgId} style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <Package size={14} style={{ color: "var(--accent)" }} />
            <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>{pkgId}</span>
            <Badge variant="muted">{items.filter(e => e.is_included).length} / {items.length} included</Badge>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {items.map(e => (
              <div key={e.engine_key} style={{
                display: "flex", alignItems: "center", gap: 6, padding: "6px 12px",
                borderRadius: 7, border: `1px solid ${e.is_included ? "var(--success-border)" : "var(--border)"}`,
                background: e.is_included ? "var(--success-bg)" : "var(--surface-sunken)",
                opacity: e.is_included ? 1 : 0.6,
              }}>
                {e.is_included
                  ? <CheckCircle2 size={11} style={{ color: "var(--success)" }} />
                  : <XCircle size={11} style={{ color: "var(--text-tertiary)" }} />}
                <span style={{ fontSize: 12, fontWeight: 500, color: e.is_included ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                  {e.engine_key}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
      {!entitlements.loading && rows.length === 0 && (
        <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
          No package entitlements configured.
        </div>
      )}
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: TENANT OVERRIDES
// ══════════════════════════════════════════════════════════════════════════════
function TenantOverridesTab() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const overrides = useApi(useCallback(() =>
    engineMgmtApi.listTenantOverrides({ status: statusFilter || undefined, page, limit: 50 }),
    [statusFilter, page]), [statusFilter, page]);

  const [revokeModal, setRevokeModal] = useState<EnterpriseTenantOverride | null>(null);
  const [revokeReason, setRevokeReason] = useState("");
  const [revokeLoading, setRevokeLoading] = useState(false);

  async function doRevoke() {
    if (!revokeModal) return;
    setRevokeLoading(true);
    try {
      await engineMgmtApi.revokeTenantOverride(revokeModal.tenant_id, revokeModal.id, revokeReason);
      overrides.refetch();
      setRevokeModal(null);
    } finally { setRevokeLoading(false); }
  }

  const rows = overrides.data?.overrides ?? [];
  const meta = overrides.data?.meta;

  return (
    <div>
      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Tenant Engine Overrides</span>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} style={filterInput}>
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="revoked">Revoked</option>
            <option value="expired">Expired</option>
          </select>
        </div>

        {overrides.loading && <SkeletonBlock />}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Tenant", "Engine", "Type", "Status", "Reason", "Expires", ""].map(h => <th key={h} style={TH}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(o => (
                <tr key={o.id}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  <td style={TD}><span style={{ fontFamily: "monospace", fontSize: 11 }}>{o.tenant_id.slice(0, 8)}…</span></td>
                  <td style={TD}><span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, fontWeight: 600 }}>{o.engine_key}</span></td>
                  <td style={TD}><Badge variant="muted">{o.override_type}</Badge></td>
                  <td style={TD}><Badge variant={o.status === "active" ? "success" : "muted"}>{o.status}</Badge></td>
                  <td style={{ ...TD, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                    {o.reason || "—"}
                  </td>
                  <td style={{ ...TD, fontSize: 11, color: "var(--text-tertiary)" }}>
                    {o.expires_at ? new Date(o.expires_at).toLocaleDateString() : "Never"}
                  </td>
                  <td style={TD}>
                    {o.status === "active" && (
                      <Btn size="xs" variant="danger" onClick={() => { setRevokeModal(o); setRevokeReason(""); }}>
                        Revoke
                      </Btn>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && !overrides.loading && (
                <tr><td colSpan={7} style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>No overrides found.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {meta && meta.total > 50 && (
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center", marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            <Btn size="xs" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</Btn>
            <Btn size="xs" variant="secondary" onClick={() => setPage(p => p + 1)}>Next →</Btn>
          </div>
        )}
      </Card>

      <Modal open={!!revokeModal} onClose={() => setRevokeModal(null)} title="Revoke Tenant Override">
        {revokeModal && (
          <div>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
              Revoke <Badge variant="muted">{revokeModal.override_type}</Badge> override for <strong>{revokeModal.engine_key}</strong>?
            </p>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
              Reason <span style={{ color: "var(--danger)" }}>*</span>
            </label>
            <textarea
              value={revokeReason}
              onChange={e => setRevokeReason(e.target.value)}
              placeholder="Reason for revoking…"
              rows={2}
              style={{ width: "100%", fontSize: 13, padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 14 }}>
              <Btn variant="secondary" onClick={() => setRevokeModal(null)}>Cancel</Btn>
              <Btn variant="danger" onClick={doRevoke} disabled={revokeLoading || !revokeReason.trim()} loading={revokeLoading}>
                Revoke Override
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: HEALTH
// ══════════════════════════════════════════════════════════════════════════════
function HealthTab() {
  const health = useApi(useCallback(() => engineMgmtApi.getHealth(), []), []);
  const [running, setRunning] = useState(false);

  async function runAllChecks() {
    setRunning(true);
    try {
      await engineMgmtApi.checkAllHealth();
      health.refetch();
    } finally { setRunning(false); }
  }

  const h = health.data as EngineHealthOverview | null;
  const summary = h?.summary;

  return (
    <div>
      {summary && (
        <SummaryCardsRow cards={[
          { label: "Healthy", value: summary.healthy, accent: true },
          { label: "Degraded", value: summary.degraded },
          { label: "Down", value: summary.down },
          { label: "Unknown", value: summary.unknown },
          { label: "Total", value: summary.total },
        ]} />
      )}

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Engine Health Status</span>
          <Btn variant="secondary" size="sm" onClick={runAllChecks} loading={running}>
            <RefreshCw size={13} style={{ marginRight: 6 }} />
            {running ? "Running…" : "Run All Checks"}
          </Btn>
        </div>

        {health.loading && <SkeletonBlock />}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Engine", "Health", "Last Error", "Last Check"].map(h => <th key={h} style={TH}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {(h?.engines ?? []).map((eng, i) => (
                <tr key={i}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  <td style={TD}>
                    <Link href={`/admin/engines/${eng.engine_key}`} style={{ fontWeight: 600, fontSize: 13, textDecoration: "none", color: "var(--text-link)" }}>
                      {eng.display_name}
                    </Link>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{eng.engine_key}</div>
                  </td>
                  <td style={TD}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <HealthDot status={eng.health_status} />
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{eng.health_status}</span>
                    </div>
                  </td>
                  <td style={{ ...TD, color: "var(--text-secondary)", fontSize: 12, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {eng.last_error || "—"}
                  </td>
                  <td style={{ ...TD, fontSize: 11, color: "var(--text-tertiary)" }}>
                    {eng.last_check ? new Date(eng.last_check).toLocaleString() : "Never"}
                  </td>
                </tr>
              ))}
              {!health.loading && (h?.engines ?? []).length === 0 && (
                <tr><td colSpan={4} style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>
                  No health data. Click "Run All Checks" to begin.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: PERMISSIONS
// ══════════════════════════════════════════════════════════════════════════════
function PermissionsTab() {
  const [q, setQ] = useState("");
  const [scopeFilter, setScopeFilter] = useState("");
  const perms = useApi(useCallback(() =>
    engineMgmtApi.listPermissions({ q: q || undefined, scope: scopeFilter || undefined }),
    [q, scopeFilter]), [q, scopeFilter]);
  const rows = perms.data?.permissions ?? [];

  return (
    <Card>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
          Engine Permissions <Badge variant="muted">{perms.data?.meta?.total ?? rows.length}</Badge>
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }} />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search…" style={{ ...filterInput, paddingLeft: 32, width: 200 }} />
          </div>
          <select value={scopeFilter} onChange={e => setScopeFilter(e.target.value)} style={filterInput}>
            <option value="">All Scopes</option>
            <option value="admin">Admin</option>
            <option value="tenant">Tenant</option>
            <option value="customer">Customer</option>
            <option value="staff">Staff</option>
          </select>
        </div>
      </div>

      {perms.loading && <SkeletonBlock />}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Permission Key", "Engine", "Scope", "Sensitive", "Description"].map(h => <th key={h} style={TH}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((p: EnterpriseEnginePermission) => (
              <tr key={p.id}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                <td style={TD}><span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, fontWeight: 600 }}>{p.permission_key}</span></td>
                <td style={TD}><span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-secondary)" }}>{p.engine_key}</span></td>
                <td style={TD}><Badge variant="muted">{p.scope}</Badge></td>
                <td style={TD}>
                  {p.is_sensitive ? <Lock size={13} style={{ color: "var(--warning)" }} /> : <span style={{ color: "var(--text-tertiary)" }}>—</span>}
                </td>
                <td style={{ ...TD, color: "var(--text-secondary)", maxWidth: 300 }}>{p.description || "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && !perms.loading && (
              <tr><td colSpan={5} style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>No permissions found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: AUDIT LOGS
// ══════════════════════════════════════════════════════════════════════════════
function AuditLogsTab() {
  const [engineFilter, setEngineFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);
  const logs = useApi(useCallback(() =>
    engineMgmtApi.listAuditLogs({ engine_key: engineFilter || undefined, action_type: actionFilter || undefined, page, limit: 50 }),
    [engineFilter, actionFilter, page]), [engineFilter, actionFilter, page]);

  const rows = logs.data?.logs ?? [];
  const meta = logs.data?.meta;

  return (
    <Card>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          value={engineFilter}
          onChange={e => { setEngineFilter(e.target.value); setPage(1); }}
          placeholder="Filter by engine key…"
          style={{ ...filterInput, width: 200 }}
        />
        <select value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(1); }} style={filterInput}>
          <option value="">All Actions</option>
          <option value="enable">Enable</option>
          <option value="disable">Disable</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="override_create">Override Create</option>
          <option value="override_revoke">Override Revoke</option>
          <option value="health_check">Health Check</option>
        </select>
      </div>

      {logs.loading && <SkeletonBlock />}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Engine", "Action", "Scope", "Actor", "Reason", "Timestamp"].map(h => <th key={h} style={TH}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((log: EnterpriseEngineAuditLog, i) => (
              <tr key={i}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                <td style={TD}><span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600 }}>{log.engine_key ?? "—"}</span></td>
                <td style={TD}>
                  <Badge variant={
                    log.action_type.includes("disable") || log.action_type.includes("revoke") ? "danger" :
                    log.action_type.includes("enable") ? "success" : "muted"
                  }>{log.action_type}</Badge>
                </td>
                <td style={{ ...TD, fontSize: 12, color: "var(--text-secondary)" }}>{log.scope_type || "global"}</td>
                <td style={{ ...TD, fontSize: 12, fontFamily: "monospace" }}>
                  {log.actor_user_id ? log.actor_user_id.slice(0, 8) + "…" : log.actor_role || "system"}
                </td>
                <td style={{ ...TD, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-secondary)", fontSize: 12 }}>
                  {log.reason || "—"}
                </td>
                <td style={{ ...TD, fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                  {new Date(log.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {rows.length === 0 && !logs.loading && (
              <tr><td colSpan={6} style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>No audit logs found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {meta && meta.total_pages > 1 && (
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center", marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
          <Btn size="xs" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</Btn>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page} of {meta.total_pages}</span>
          <Btn size="xs" variant="secondary" disabled={page >= meta.total_pages} onClick={() => setPage(p => p + 1)}>Next →</Btn>
        </div>
      )}
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════════════
export default function EngineMgmtPage() {
  const [tab, setTab] = useState<Tab>("all");

  const summary = useApi(useCallback(() => engineMgmtApi.getSummary(), []), []);
  const s = summary.data as EngineSummary | null;

  return (
    <AdminLayout>
      <SectionHeader
        title="Engine Management"
        subtitle="Platform-level control for all ServiceOS engines"
        icon={<Cpu />}
        actions={
          <Link href="/admin/engines/resolver">
            <Btn variant="secondary" size="sm">
              <Zap size={13} style={{ marginRight: 6 }} />
              Access Resolver
            </Btn>
          </Link>
        }
      />

      {/* Tab bar — matches types-brands pattern exactly */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "2px solid var(--border)", paddingBottom: 0, overflowX: "auto" }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "10px 16px", border: "none", background: "none", cursor: "pointer",
              fontSize: 13, fontWeight: tab === t.id ? 600 : 400,
              color: tab === t.id ? "var(--accent)" : "var(--text-secondary)",
              borderBottom: tab === t.id ? "2px solid var(--accent)" : "2px solid transparent",
              marginBottom: -2, transition: "all 0.15s", whiteSpace: "nowrap", flexShrink: 0,
            }}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === "all"                  && <AllEnginesTab summary={s} />}
      {tab === "category-matrix"      && <CategoryMatrixTab />}
      {tab === "dependencies"         && <DependenciesTab />}
      {tab === "package-entitlements" && <PackageEntitlementsTab />}
      {tab === "tenant-overrides"     && <TenantOverridesTab />}
      {tab === "health"               && <HealthTab />}
      {tab === "permissions"          && <PermissionsTab />}
      {tab === "audit-logs"           && <AuditLogsTab />}
    </AdminLayout>
  );
}
