"use client";
import React from "react";
import { use } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { SectionHeader, Card, Badge, Btn } from "../../../../components/shared/ui";
import {
  FolderTree, Layers, Tag, Wrench, HelpCircle, MapPin,
  LayoutGrid, Sliders, Settings, Inbox, Package, ExternalLink,
  Globe,
} from "lucide-react";
import {
  verticalCatalogApi, type VerticalDetail, type VerticalModuleItem,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

// ── Module icon + group color ──────────────────────────────────────────────────
const MOD_ICON: Record<string, React.ReactNode> = {
  categories:          <Layers size={16}/>,
  service_groups:      <FolderTree size={16}/>,
  master_services:     <Wrench size={16}/>,
  types_brands:        <Tag size={16}/>,
  brands:              <Tag size={16}/>,
  brand_requests:      <Inbox size={16}/>,
  service_options:     <Settings size={16}/>,
  issue_types:         <HelpCircle size={16}/>,
  pricing_tiers:       <LayoutGrid size={16}/>,
  location_mapping:    <MapPin size={16}/>,
  pricing_rules:       <Sliders size={16}/>,
  checklist_templates: <Layers size={16}/>,
  service_setup:       <Package size={16}/>,
};

const GROUP_COLOR: Record<string, string> = {
  services:   "var(--brand)",
  qualifiers: "#7c3aed",
  pricing:    "#0891b2",
  compliance: "#d97706",
  other:      "var(--text-tertiary)",
};

// ── Module card ────────────────────────────────────────────────────────────────
function ModuleCard({ m }: { m: VerticalModuleItem }) {
  if (!m.is_enabled) return null;
  const group = m.module_group ?? "other";
  const color = GROUP_COLOR[group] ?? GROUP_COLOR.other;

  return (
    <a
      href={m.admin_path ?? "#"}
      style={{
        display: "flex", alignItems: "center", gap: 14,
        padding: "14px 16px", borderRadius: 10,
        background: "var(--surface)", border: "1px solid var(--border)",
        textDecoration: "none", color: "inherit",
        transition: "border-color 0.12s, box-shadow 0.12s",
        borderLeft: `3px solid ${color}`,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLAnchorElement).style.borderColor = color;
        (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow-sm)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--border)";
        (e.currentTarget as HTMLAnchorElement).style.boxShadow = "none";
      }}
    >
      <span style={{ color, flexShrink: 0 }}>{MOD_ICON[m.key] ?? <Layers size={16}/>}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>{m.label}</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
          {group.charAt(0).toUpperCase() + group.slice(1)}
          {m.is_required && " · Required"}
          {m.is_universal && " · Universal"}
        </p>
      </div>
      <ExternalLink size={13} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
    </a>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function VerticalCatalogPage({
  params,
}: {
  params: Promise<{ vertical: string }>;
}) {
  const { vertical: verticalKey } = use(params);

  const { data, loading } = useApi(
    () => verticalCatalogApi.getVertical(verticalKey),
    [verticalKey],
  );

  const detail = data as VerticalDetail | null;

  const groups: Record<string, VerticalModuleItem[]> = {};
  if (detail?.modules) {
    for (const m of detail.modules) {
      if (!m.is_enabled) continue;
      const g = m.module_group ?? "other";
      if (!groups[g]) groups[g] = [];
      groups[g].push(m);
    }
  }

  const groupOrder = ["services", "qualifiers", "pricing", "compliance", "other"];
  const sortedGroups = Object.entries(groups).sort(([a], [b]) => {
    const ai = groupOrder.indexOf(a), bi = groupOrder.indexOf(b);
    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
  });

  return (
    <AdminLayout activeNav={`catalog-${verticalKey}`}>
      {loading ? (
        <div>
          <div className="skeleton" style={{ height: 40, borderRadius: 8, marginBottom: 16, maxWidth: 300 }}/>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 70, borderRadius: 10 }}/>
            ))}
          </div>
        </div>
      ) : !detail ? (
        <div style={{ textAlign: "center", padding: 60, color: "var(--text-secondary)" }}>
          <Globe size={40} style={{ margin: "0 auto 12px", display: "block", opacity: 0.3 }}/>
          <p>Vertical not found</p>
          <Btn variant="ghost" onClick={() => window.history.back()}>Go back</Btn>
        </div>
      ) : (
        <>
          <SectionHeader
            title={detail.label}
            subtitle={`${detail.modules.filter(m => m.is_enabled).length} catalog modules enabled`}
            icon={<Globe size={20}/>}
            actions={
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {detail.is_beta && <Badge variant="info">Beta</Badge>}
                <Badge variant={detail.is_enabled ? "success" : "muted"}>
                  {detail.is_enabled ? "Enabled" : "Disabled"}
                </Badge>
                <Btn variant="ghost" size="sm" onClick={() => window.location.href = "/admin/verticals"}>
                  Manage Verticals
                </Btn>
              </div>
            }
          />

          {sortedGroups.length === 0 ? (
            <Card style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>
              No catalog modules enabled for this vertical.
            </Card>
          ) : (
            sortedGroups.map(([group, mods]) => (
              <div key={group} style={{ marginBottom: 28 }}>
                <p style={{
                  fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                  textTransform: "uppercase", color: GROUP_COLOR[group] ?? "var(--text-tertiary)",
                  margin: "0 0 10px",
                }}>
                  {group.charAt(0).toUpperCase() + group.slice(1)}
                </p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
                  {mods.map(m => <ModuleCard key={m.key} m={m}/>)}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </AdminLayout>
  );
}
