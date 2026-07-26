"use client";
import React, { useCallback } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn, Skeleton } from "../../../components/shared/ui";
import {
  serviceSetupTemplatesApi, bulkWizardApi,
  type SetupTemplateItem, type BulkRunItem,
} from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import {
  Wrench, History, Tag, FolderTree, FileStack,
  Settings, HelpCircle, ArrowRight, CheckCircle2, Clock, AlertTriangle,
  RefreshCw, Sparkles,
} from "lucide-react";

// ── Summary card ──────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, icon, color, href,
}: {
  label: string; value: number | string; icon: React.ReactNode; color?: string; href?: string;
}) {
  const accent = color ?? "var(--brand)";
  const content = (
    <Card padding={18} hover={!!href} style={{ height: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{
          width: 38, height: 38, borderRadius: 10, background: `color-mix(in srgb, ${accent} 14%, transparent)`,
          display: "flex", alignItems: "center", justifyContent: "center", color: accent, flexShrink: 0,
        }}>
          {icon}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.1 }}>{value}</div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>{label}</div>
        </div>
      </div>
    </Card>
  );
  return href ? <Link href={href} style={{ textDecoration: "none", display: "block" }}>{content}</Link> : content;
}

// ── Module nav card ────────────────────────────────────────────────────────────

interface ModuleDef {
  key: string; label: string; description: string; href: string;
  icon: React.ReactNode; badge?: string;
}

const MODULES: ModuleDef[] = [
  { key: "templates", label: "Setup Templates", href: "/admin/service-setup/templates",
    icon: <FileStack size={18}/>, description: "Reusable starter packs bundling services, brands, options, pricing and workflows for one-click category launch." },
  { key: "bulk-wizard", label: "Bulk Setup Wizard", href: "/admin/service-setup/bulk-wizard",
    icon: <Wrench size={18}/>, description: "Guided step-by-step flow to configure a new category or service end-to-end, with a dry-run preview before applying." },
  { key: "bulk-runs", label: "Bulk Setup Runs", href: "/admin/service-setup/bulk-runs",
    icon: <History size={18}/>, description: "Full audit trail of every applied bulk setup — what was created, reused, or skipped, and by whom." },
  { key: "brands", label: "Brand Master", href: "/admin/service-setup/brands",
    icon: <Tag size={18}/>, description: "Canonical brand list shared across verticals, with duplicate detection and merge tooling." },
  { key: "brand-requests", label: "Brand Requests", href: "/admin/service-setup/brand-requests",
    icon: <FolderTree size={18}/>, description: "Provider-submitted new-brand requests awaiting admin review and approval." },
  { key: "brand-templates", label: "Brand Templates", href: "/admin/service-setup/brand-templates",
    icon: <Sparkles size={18}/>, description: "Starter brand sets seeded per vertical to speed up brand-required service onboarding." },
  { key: "option-groups", label: "Option Groups", href: "/admin/service-setup/option-groups",
    icon: <Settings size={18}/>, description: "Grouping of service options (e.g. AC Tonnage, Vehicle Type) used to build provider-facing option pickers." },
  { key: "service-options", label: "Service Options", href: "/admin/service-setup/service-options",
    icon: <Settings size={18}/>, description: "Individual selectable options a customer picks when booking, mapped to services and pricing tiers." },
  { key: "issue-types", label: "Issue Types", href: "/admin/service-setup/issue-types",
    icon: <HelpCircle size={18}/>, description: "Customer-facing issue/complaint categories mapped to services, driving diagnosis and severity flows." },
];

const STATUS_VARIANT: Record<string, "default"|"success"|"warning"|"danger"|"info"|"muted"> = {
  draft: "warning", published: "success", archived: "muted",
  queued: "info", running: "info", completed: "success",
  partially_completed: "warning", rolled_back: "muted", failed: "danger",
};

export default function ServiceSetupHubPage() {
  const templates = useApi(useCallback(
    () => serviceSetupTemplatesApi.list({ page_size: 100 }), []));
  const wizardSummary = useApi(useCallback(
    () => bulkWizardApi.getSummary(), []));
  const runs = useApi(useCallback(
    () => bulkWizardApi.listRuns({ page_size: 10 }), []));

  const loading = templates.loading || wizardSummary.loading || runs.loading;

  const tItems: SetupTemplateItem[] = templates.data?.items ?? [];
  const rItems: BulkRunItem[] = runs.data?.items ?? [];
  const sum = wizardSummary.data ?? null;

  const publishedCount = tItems.filter(t => t.status === "published").length;
  const draftTplCount  = tItems.filter(t => t.status === "draft").length;

  function refetchAll() { templates.refetch(); wizardSummary.refetch(); runs.refetch(); }

  return (
    <AdminLayout activeNav="service-setup">
      <SectionHeader
        title="Service Setup"
        subtitle="Bulk service configuration — templates, guided wizard, and audit trail for launching categories and services fast"
        icon={<Wrench size={20}/>}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="ghost" size="sm" icon={<RefreshCw size={14}/>} onClick={refetchAll}>Refresh</Btn>
            <Btn variant="primary" size="sm" icon={<Wrench size={14}/>}
              onClick={() => { window.location.href = "/admin/service-setup/bulk-wizard"; }}>
              Start Bulk Setup
            </Btn>
          </div>
        }
      />

      {/* KPI summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14, marginBottom: 20 }}>
        {loading ? (
          [...Array(6)].map((_, i) => <Skeleton key={i} height={72} style={{ borderRadius: 12 }}/>)
        ) : (
          <>
            <SummaryCard label="Total Templates" value={tItems.length} icon={<FileStack size={18}/>}
              color="var(--brand)" href="/admin/service-setup/templates"/>
            <SummaryCard label="Published Templates" value={publishedCount} icon={<CheckCircle2 size={18}/>}
              color="var(--success)" href="/admin/service-setup/templates"/>
            <SummaryCard label="Draft Templates" value={draftTplCount} icon={<Clock size={18}/>}
              color="var(--warning)" href="/admin/service-setup/templates"/>
            <SummaryCard label="Active Wizard Drafts" value={sum?.ready_to_run ?? sum?.total_drafts ?? 0} icon={<Wrench size={18}/>}
              color="var(--info)" href="/admin/service-setup/bulk-wizard"/>
            <SummaryCard label="Total Bulk Runs" value={runs.data?.total ?? rItems.length} icon={<History size={18}/>}
              color="var(--brand)" href="/admin/service-setup/bulk-runs"/>
            <SummaryCard label="Failed Runs" value={sum?.failed_runs ?? 0} icon={<AlertTriangle size={18}/>}
              color={(sum?.failed_runs ?? 0) > 0 ? "var(--danger)" : "var(--text-tertiary)"} href="/admin/service-setup/bulk-runs"/>
          </>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
        {/* Module grid */}
        <div>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-tertiary)", margin: "0 0 12px",
            textTransform: "uppercase", letterSpacing: "0.06em" }}>Setup Modules</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
            {MODULES.map(m => (
              <a key={m.key} href={m.href} style={{ textDecoration: "none" }}>
                <Card hover padding={18} style={{ height: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 34, height: 34, borderRadius: 9, background: "var(--surface-sunken)",
                      display: "flex", alignItems: "center", justifyContent: "center", color: "var(--brand)" }}>
                      {m.icon}
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{m.label}</div>
                  </div>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5, flex: 1 }}>
                    {m.description}
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "var(--text-link)", fontWeight: 600 }}>
                    Open <ArrowRight size={13}/>
                  </div>
                </Card>
              </a>
            ))}
          </div>
        </div>

        {/* Recent activity sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card padding={18}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-tertiary)", margin: "0 0 12px",
              textTransform: "uppercase", letterSpacing: "0.06em" }}>Recent Templates</h3>
            {templates.loading ? (
              <Skeleton height={100}/>
            ) : tItems.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No templates yet.</p>
            ) : tItems.slice(0, 5).map(t => (
              <a key={t.id} href={`/admin/service-setup/templates/${t.id}`} style={{ textDecoration: "none" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.name}</div>
                    <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{t.code}</div>
                  </div>
                  <Badge variant={STATUS_VARIANT[t.status] ?? "muted"} size="sm">{t.status}</Badge>
                </div>
              </a>
            ))}
            <Link href="/admin/service-setup/templates" style={{ fontSize: 12, color: "var(--text-link)",
              fontWeight: 600, display: "inline-block", marginTop: 10 }}>View all templates →</Link>
          </Card>

          <Card padding={18}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-tertiary)", margin: "0 0 12px",
              textTransform: "uppercase", letterSpacing: "0.06em" }}>Recent Bulk Runs</h3>
            {runs.loading ? (
              <Skeleton height={100}/>
            ) : rItems.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No runs yet.</p>
            ) : rItems.slice(0, 5).map(r => (
              <a key={r.id} href={`/admin/service-setup/bulk-runs/${r.id}`} style={{ textDecoration: "none" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.vertical_key ?? "Bulk Setup Run"}
                    </div>
                    <div style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>
                      {r.created_at ? new Date(r.created_at).toLocaleDateString("en-IN") : "—"}
                    </div>
                  </div>
                  <Badge variant={STATUS_VARIANT[r.status] ?? "muted"} size="sm">{r.status}</Badge>
                </div>
              </a>
            ))}
            <Link href="/admin/service-setup/bulk-runs" style={{ fontSize: 12, color: "var(--text-link)",
              fontWeight: 600, display: "inline-block", marginTop: 10 }}>View all runs →</Link>
          </Card>

          {(templates.error || wizardSummary.error || runs.error) && (
            <Card padding={16} style={{ borderColor: "var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
                Could not load some setup data.
                {templates.requestId || wizardSummary.requestId || runs.requestId
                  ? ` Request ID: ${templates.requestId ?? wizardSummary.requestId ?? runs.requestId}` : ""}
              </p>
              <Btn variant="ghost" size="sm" onClick={refetchAll} style={{ marginTop: 8 }}>Retry</Btn>
            </Card>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
