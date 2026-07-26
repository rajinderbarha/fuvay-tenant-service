"use client";
import React, { useState } from "react";
import Link from "next/link";
import { AdminLayout, useAdminMenuRefresh } from "../../../components/layout/AdminLayout";
import {
  SectionHeader, Card, Badge, Btn, Modal,
} from "../../../components/shared/ui";
import {
  Globe, CheckCircle, XCircle, Zap, FlaskConical, RefreshCw,
  Settings, ToggleLeft, ToggleRight, Layers, FolderTree, Tag,
  Wrench, HelpCircle, MapPin, LayoutGrid, Sliders,
} from "lucide-react";
import {
  verticalCatalogApi,
  type VerticalItem, type VerticalDetail,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

// ── Finance model badge ────────────────────────────────────────────────────────
const FINANCE_V: Record<string, "info" | "success" | "golden"> = {
  commission: "info", subscription: "success", hybrid: "golden",
};

// ── Module icon map ────────────────────────────────────────────────────────────
const MOD_ICON: Record<string, React.ReactNode> = {
  categories:        <Layers size={13}/>,
  service_groups:    <FolderTree size={13}/>,
  master_services:   <Wrench size={13}/>,
  types_brands:      <Tag size={13}/>,
  brands:            <Tag size={13}/>,
  brand_requests:    <FolderTree size={13}/>,
  service_options:   <Settings size={13}/>,
  issue_types:       <HelpCircle size={13}/>,
  pricing_tiers:     <LayoutGrid size={13}/>,
  location_mapping:  <MapPin size={13}/>,
  pricing_rules:     <Sliders size={13}/>,
  checklist_templates:<Layers size={13}/>,
  service_setup:     <Wrench size={13}/>,
};

// ── Detail Modal ───────────────────────────────────────────────────────────────

function VerticalDetailModal({ vertical, onClose, onToggled }: {
  vertical: VerticalItem;
  onClose: () => void;
  onToggled: () => void;
}) {
  const { data: detail, loading } = useApi(
    () => verticalCatalogApi.getVertical(vertical.key),
    [vertical.key],
  );

  const { execute: enableMod, loading: toggling } = useAction(
    (moduleKey: string) => verticalCatalogApi.enableModule(vertical.key, moduleKey),
  );
  const { execute: disableMod } = useAction(
    (moduleKey: string) => verticalCatalogApi.disableModule(vertical.key, moduleKey),
  );

  const groups: Record<string, typeof detail extends VerticalDetail ? VerticalDetail["modules"] : never[]> = {};
  if (detail && "modules" in detail) {
    for (const m of (detail as VerticalDetail).modules) {
      const g = m.module_group ?? "other";
      if (!groups[g]) groups[g] = [];
      (groups[g] as (typeof m)[]).push(m);
    }
  }

  return (
    <Modal open title={`${vertical.label} — Catalog Modules`} onClose={onClose} size="lg">
      {loading ? (
        <p style={{ color: "var(--text-secondary)", textAlign: "center", padding: 24 }}>Loading…</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {Object.entries(groups).map(([group, mods]) => (
            <div key={group}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
                color: "var(--text-tertiary)", margin: "0 0 6px" }}>{group}</p>
              {(mods as VerticalDetail["modules"]).map(m => (
                <div key={m.key} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "8px 12px", borderRadius: 8,
                  background: "var(--surface-sunken)",
                  border: "1px solid var(--border)",
                  marginBottom: 4,
                }}>
                  <span style={{ color: "var(--brand)", flexShrink: 0 }}>{MOD_ICON[m.key] ?? <Layers size={13}/>}</span>
                  <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{m.label}</span>
                  {m.is_required && <Badge variant="warning">Required</Badge>}
                  {m.is_universal && <Badge variant="muted">Universal</Badge>}
                  <button
                    disabled={m.is_required || toggling}
                    onClick={async () => {
                      if (m.is_enabled) await disableMod(m.key);
                      else await enableMod(m.key);
                      onToggled();
                    }}
                    style={{
                      border: "none", background: "transparent", cursor: m.is_required ? "not-allowed" : "pointer",
                      color: m.is_enabled ? "var(--success)" : "var(--text-tertiary)",
                      display: "flex", alignItems: "center", opacity: m.is_required ? 0.4 : 1,
                    }}
                  >
                    {m.is_enabled ? <ToggleRight size={20}/> : <ToggleLeft size={20}/>}
                  </button>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

// ── Vertical Card ──────────────────────────────────────────────────────────────

function VerticalCard({ v, onToggle, onConfigure }: {
  v: VerticalItem;
  onToggle: (key: string, enable: boolean) => void;
  onConfigure: (v: VerticalItem) => void;
}) {
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 12, padding: 18, display: "flex", flexDirection: "column", gap: 12,
      borderTop: `3px solid ${v.color ?? "var(--brand)"}`,
      opacity: v.is_enabled ? 1 : 0.65,
      transition: "opacity 0.15s",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0,
          background: `${v.color ?? "var(--brand)"}22`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: v.color ?? "var(--brand)",
        }}>
          <Globe size={18}/>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>{v.label}</span>
            {v.is_beta && <Badge variant="info">Beta</Badge>}
            <Badge variant={v.is_enabled ? "success" : "muted"}>
              {v.is_enabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
            {v.key}
          </p>
        </div>
      </div>

      {v.finance_model && (
        <div style={{ display: "flex", gap: 6 }}>
          <Badge variant={FINANCE_V[v.finance_model] ?? "muted"}>
            {v.finance_model}
          </Badge>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
        <Btn variant="ghost" size="sm" icon={<Settings size={13}/>} onClick={() => onConfigure(v)}>
          Modules
        </Btn>
        <Link href={`/admin/verticals/${v.key}?tab=capabilities`} style={{ textDecoration: "none" }}>
          <Btn variant="ghost" size="sm">Capabilities & Policies</Btn>
        </Link>
        <div style={{ flex: 1 }}/>
        {v.is_enabled ? (
          <Btn variant="danger" size="sm" icon={<XCircle size={13}/>} onClick={() => onToggle(v.key, false)}>
            Disable
          </Btn>
        ) : (
          <Btn variant="success" size="sm" icon={<CheckCircle size={13}/>} onClick={() => onToggle(v.key, true)}>
            Enable
          </Btn>
        )}
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function VerticalsPage() {
  const [configuring, setConfiguring] = useState<VerticalItem | null>(null);
  const refreshMenu = useAdminMenuRefresh();

  const { data, loading, error, refetch } = useApi(
    () => verticalCatalogApi.listVerticals(true),
    [],
  );

  const { execute: doEnable } = useAction(
    (key: string) => verticalCatalogApi.enableVertical(key),
  );
  const { execute: doDisable } = useAction(
    (key: string) => verticalCatalogApi.disableVertical(key),
  );

  const items: VerticalItem[] = (data as { items: VerticalItem[] } | null)?.items ?? [];
  const enabledCount = items.filter(v => v.is_enabled).length;
  const betaCount = items.filter(v => v.is_beta).length;

  // FINAL-L5-04: activating/deactivating a vertical must update the sidebar
  // (AdminLayout's effectiveMenu), not just this page's own list -- the
  // sidebar previously only fetched effectiveMenu once on mount.
  async function handleToggle(key: string, enable: boolean) {
    if (enable) await doEnable(key);
    else await doDisable(key);
    refetch();
    refreshMenu();
  }

  return (
    <AdminLayout activeNav="verticals">
      <SectionHeader
        title="Verticals"
        subtitle={`${enabledCount} of ${items.length} enabled${betaCount ? ` · ${betaCount} beta` : ""}`}
        icon={<Globe size={20}/>}
        actions={
          <Btn variant="ghost" size="sm" icon={<RefreshCw size={13}/>} onClick={refetch}>
            Refresh
          </Btn>
        }
      />

      {/* Summary strip */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {[
          { label: "Total Verticals",  value: items.length,    icon: <Globe size={15}/>,        color: "var(--brand)" },
          { label: "Enabled",          value: enabledCount,    icon: <Zap size={15}/>,           color: "#16a34a" },
          { label: "Beta / Upcoming",  value: betaCount,       icon: <FlaskConical size={15}/>,  color: "#7c3aed" },
        ].map(c => (
          <div key={c.label} style={{
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, padding: "12px 18px", display: "flex", alignItems: "center", gap: 10,
          }}>
            <span style={{ color: c.color }}>{c.icon}</span>
            <div>
              <p style={{ fontSize: 18, fontWeight: 700, margin: 0, fontVariantNumeric: "tabular-nums" }}>
                {loading ? "…" : c.value}
              </p>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>{c.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div style={{
          background: "var(--danger-bg, #fee2e2)", border: "1px solid var(--danger-border, #fca5a5)",
          borderRadius: 8, padding: "12px 16px", marginBottom: 16,
          color: "var(--danger, #dc2626)", fontSize: 13,
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <XCircle size={15} style={{ flexShrink: 0 }}/>
          <span>{error}</span>
          <Btn variant="ghost" size="sm" onClick={refetch} style={{ marginLeft: "auto" }}>Retry</Btn>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 160, borderRadius: 12 }}/>
          ))}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
          {items.map(v => (
            <VerticalCard
              key={v.key}
              v={v}
              onToggle={handleToggle}
              onConfigure={setConfiguring}
            />
          ))}
        </div>
      )}

      {configuring && (
        <VerticalDetailModal
          vertical={configuring}
          onClose={() => setConfiguring(null)}
          onToggled={() => { refetch(); refreshMenu(); }}
        />
      )}
    </AdminLayout>
  );
}
