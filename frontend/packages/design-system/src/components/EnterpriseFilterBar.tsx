"use client";
import { useState, useEffect, useCallback, useRef } from "react";

export interface FilterDef {
  key:          string;
  label:        string;
  type:         "text" | "select" | "date" | "date_range";
  options?:     { value: string; label: string }[];
  placeholder?: string;
  advanced?:    boolean;   // moves to advanced drawer
  group?:       string;    // section heading inside drawer
}

interface Props {
  filters:        FilterDef[];
  values:         Record<string, string>;
  onChange:       (key: string, value: string) => void;
  onBatchChange?: (changes: Record<string, string>) => void;
  onReset:        () => void;
  onSearch?:      (q: string) => void;
  searchValue?:   string;
  rightSlot?:     React.ReactNode;
}

// ── helpers ──────────────────────────────────────────────────────────────────

const BASE: React.CSSProperties = {
  height: 34, padding: "0 10px", fontSize: 13,
  background: "var(--input-bg, var(--surface-sunken))",
  border: "1px solid var(--border)", borderRadius: 8,
  color: "var(--text-primary)", outline: "none", fontFamily: "inherit",
};

function advancedKeys(filters: FilterDef[]): string[] {
  return filters.filter(f => f.advanced).flatMap(f =>
    f.type === "date_range" ? [`${f.key}_from`, `${f.key}_to`] : [f.key]
  );
}

function getChipLabel(key: string, value: string, filters: FilterDef[]): string {
  // Direct match
  const def = filters.find(f => f.key === key);
  if (def) {
    const optLabel = def.options?.find(o => o.value === value)?.label;
    return `${def.label}: ${optLabel ?? value}`;
  }
  // Date range suffix
  const fromM = key.match(/^(.+)_from$/);
  const toM   = key.match(/^(.+)_to$/);
  const base  = fromM?.[1] ?? toM?.[1];
  const rDef  = base ? filters.find(f => f.key === base && f.type === "date_range") : undefined;
  if (rDef) return `${rDef.label} ${fromM ? "from" : "to"}: ${value}`;
  return `${key}: ${value}`;
}

// ── sub-components ────────────────────────────────────────────────────────────

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      height: 26, padding: "0 6px 0 10px",
      background: "var(--brand-muted, #eff6ff)", color: "var(--brand, #2563eb)",
      border: "1px solid var(--brand-border, #bfdbfe)",
      borderRadius: 999, fontSize: 12, fontWeight: 500,
      whiteSpace: "nowrap",
    }}>
      {label}
      <button
        onClick={onRemove}
        aria-label={`Remove ${label} filter`}
        style={{
          width: 18, height: 18, display: "inline-flex", alignItems: "center",
          justifyContent: "center", borderRadius: "50%", background: "none",
          border: "none", cursor: "pointer", color: "inherit",
          fontSize: 14, lineHeight: 1, opacity: 0.7,
        }}
      >×</button>
    </span>
  );
}

function QuickSelect({ def, value, onChange }: {
  def: FilterDef; value: string; onChange: (v: string) => void;
}) {
  const active = Boolean(value);
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        ...BASE,
        paddingRight: 28, cursor: "pointer",
        fontWeight: active ? 600 : undefined,
        borderColor: active ? "var(--brand, #2563eb)" : undefined,
        color: active ? "var(--brand, #2563eb)" : undefined,
      }}
    >
      <option value="">{def.label}</option>
      {def.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ── Advanced Filters drawer ───────────────────────────────────────────────────

function AdvancedInput({ def, values, onChange }: {
  def: FilterDef;
  values: Record<string, string>;
  onChange: (key: string, val: string) => void;
}) {
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: 11, fontWeight: 600,
    color: "var(--text-tertiary)", textTransform: "uppercase",
    letterSpacing: "0.06em", marginBottom: 5,
  };

  if (def.type === "select") {
    return (
      <div>
        <label style={labelStyle}>{def.label}</label>
        <select
          value={values[def.key] ?? ""}
          onChange={e => onChange(def.key, e.target.value)}
          style={{ ...BASE, width: "100%", paddingRight: 28, cursor: "pointer" }}
        >
          <option value="">All</option>
          {def.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
    );
  }
  if (def.type === "date_range") {
    return (
      <div>
        <label style={labelStyle}>{def.label}</label>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="date"
            value={values[`${def.key}_from`] ?? ""}
            onChange={e => onChange(`${def.key}_from`, e.target.value)}
            style={{ ...BASE, flex: 1 }}
          />
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>–</span>
          <input
            type="date"
            value={values[`${def.key}_to`] ?? ""}
            onChange={e => onChange(`${def.key}_to`, e.target.value)}
            style={{ ...BASE, flex: 1 }}
          />
        </div>
      </div>
    );
  }
  return (
    <div>
      <label style={labelStyle}>{def.label}</label>
      <input
        type="text"
        value={values[def.key] ?? ""}
        onChange={e => onChange(def.key, e.target.value)}
        placeholder={def.placeholder ?? def.label}
        style={{ ...BASE, width: "100%" }}
      />
    </div>
  );
}

function AdvancedDrawer({
  open, advFilters, draftValues, onDraftChange,
  onApply, onReset, onClose,
}: {
  open: boolean;
  advFilters: FilterDef[];
  draftValues: Record<string, string>;
  onDraftChange: (key: string, val: string) => void;
  onApply: () => void;
  onReset: () => void;
  onClose: () => void;
}) {
  // Group filters
  const groups: Record<string, FilterDef[]> = {};
  advFilters.forEach(f => {
    const g = f.group ?? "Filters";
    if (!groups[g]) groups[g] = [];
    groups[g].push(f);
  });

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  const hasDraft = Object.values(draftValues).some(Boolean);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "rgba(0,0,0,0.25)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
          transition: "opacity 0.2s ease",
        }}
      />

      {/* Drawer panel */}
      <div
        style={{
          position: "fixed", top: 0, right: 0, bottom: 0,
          width: "min(380px, 100vw)", zIndex: 1001,
          background: "var(--surface)",
          borderLeft: "1px solid var(--border)",
          boxShadow: "-12px 0 40px rgba(0,0,0,0.12)",
          transform: open ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.22s cubic-bezier(0.4, 0, 0.2, 1)",
          display: "flex", flexDirection: "column",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px", borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>
              Advanced Filters
            </div>
            {hasDraft && (
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                {Object.values(draftValues).filter(Boolean).length} filter{Object.values(draftValues).filter(Boolean).length !== 1 ? "s" : ""} selected
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              width: 30, height: 30, display: "inline-flex", alignItems: "center",
              justifyContent: "center", background: "none", border: "none",
              cursor: "pointer", color: "var(--text-tertiary)", fontSize: 20,
              borderRadius: 8,
            }}
          >×</button>
        </div>

        {/* Scrollable filter body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {Object.entries(groups).map(([groupName, groupFilters], gi) => (
            <div key={groupName} style={{ marginBottom: gi < Object.keys(groups).length - 1 ? 24 : 0 }}>
              <div style={{
                fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                letterSpacing: "0.08em", color: "var(--text-tertiary)",
                marginBottom: 12,
              }}>
                {groupName}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {groupFilters.map(f => (
                  <AdvancedInput
                    key={f.key}
                    def={f}
                    values={draftValues}
                    onChange={onDraftChange}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: "14px 20px",
          borderTop: "1px solid var(--border)",
          display: "flex", gap: 10, flexShrink: 0,
        }}>
          <button
            onClick={onReset}
            style={{
              flex: 1, height: 38, fontSize: 13, fontWeight: 500,
              borderRadius: 8, border: "1px solid var(--border)",
              background: "var(--surface)", color: "var(--text-secondary)",
              cursor: "pointer", fontFamily: "inherit",
            }}
          >
            Reset
          </button>
          <button
            onClick={onApply}
            style={{
              flex: 2, height: 38, fontSize: 13, fontWeight: 600,
              borderRadius: 8, border: "none",
              background: "var(--brand, #2563eb)", color: "#fff",
              cursor: "pointer", fontFamily: "inherit",
            }}
          >
            Apply Filters
          </button>
        </div>
      </div>
    </>
  );
}

// ── Main FilterBar component ──────────────────────────────────────────────────

export function EnterpriseFilterBar({
  filters, values, onChange, onBatchChange, onReset, onSearch,
  searchValue = "", rightSlot,
}: Props) {
  const [localSearch,  setLocalSearch]  = useState(searchValue);
  const [drawerOpen,   setDrawerOpen]   = useState(false);
  const [draftValues,  setDraftValues]  = useState<Record<string, string>>({});
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { setLocalSearch(searchValue); }, [searchValue]);

  const quickFilters    = filters.filter(f => !f.advanced);
  const advFilters      = filters.filter(f =>  f.advanced);
  const advKeys         = advancedKeys(advFilters);
  const activeAdvCount  = advKeys.filter(k => values[k]).length;
  const allActiveValues = Object.entries(values).filter(([, v]) => Boolean(v));

  // ── search ──────────────────────────────────────────────────────────────────
  const handleSearchChange = (q: string) => {
    setLocalSearch(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => onSearch?.(q), 350);
  };

  // ── drawer ──────────────────────────────────────────────────────────────────
  const openDrawer = useCallback(() => {
    const draft: Record<string, string> = {};
    advKeys.forEach(k => { if (values[k]) draft[k] = values[k]; });
    setDraftValues(draft);
    setDrawerOpen(true);
  }, [advKeys, values]);

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const handleDraftChange = (key: string, val: string) => {
    setDraftValues(prev => ({ ...prev, [key]: val }));
  };

  const applyDrawer = useCallback(() => {
    const changes: Record<string, string> = {};
    advKeys.forEach(k => { changes[k] = draftValues[k] ?? ""; });
    if (onBatchChange) {
      onBatchChange(changes);
    } else {
      // fallback: call onChange for each key
      Object.entries(changes).forEach(([k, v]) => onChange(k, v));
    }
    setDrawerOpen(false);
  }, [advKeys, draftValues, onBatchChange, onChange]);

  const resetDrawer = useCallback(() => {
    setDraftValues({});
    advKeys.forEach(k => { if (values[k]) onChange(k, ""); });
    setDrawerOpen(false);
  }, [advKeys, values, onChange]);

  // ── chip removal ─────────────────────────────────────────────────────────────
  const removeChip = (key: string) => onChange(key, "");
  const clearAll = () => {
    onReset();
    setLocalSearch("");
  };

  return (
    <>
      {/* Toolbar row */}
      <div style={{
        display: "flex", flexWrap: "wrap", gap: 8,
        alignItems: "center", width: "100%",
      }}>
        {/* Search */}
        {onSearch !== undefined && (
          <div style={{ position: "relative", flexShrink: 0 }}>
            <span style={{
              position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)",
              color: "var(--text-tertiary)", pointerEvents: "none", fontSize: 14,
            }}>⌕</span>
            <input
              type="text"
              value={localSearch}
              onChange={e => handleSearchChange(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") { onSearch?.(localSearch); } }}
              placeholder="Search tenants…"
              style={{ ...BASE, paddingLeft: 30, width: 220 }}
            />
          </div>
        )}

        {/* Quick filters */}
        {quickFilters.map(f => {
          if (f.type === "select") {
            return (
              <QuickSelect
                key={f.key}
                def={f}
                value={values[f.key] ?? ""}
                onChange={v => onChange(f.key, v)}
              />
            );
          }
          return (
            <input
              key={f.key}
              type="text"
              value={values[f.key] ?? ""}
              onChange={e => onChange(f.key, e.target.value)}
              placeholder={f.placeholder ?? f.label}
              style={{ ...BASE, width: 140 }}
            />
          );
        })}

        {/* Advanced Filters button */}
        {advFilters.length > 0 && (
          <button
            onClick={openDrawer}
            style={{
              height: 34, padding: "0 12px", fontSize: 13, borderRadius: 8,
              border: `1px solid ${activeAdvCount > 0 ? "var(--brand, #2563eb)" : "var(--border)"}`,
              background: activeAdvCount > 0 ? "var(--brand-muted, #eff6ff)" : "var(--surface-sunken)",
              color: activeAdvCount > 0 ? "var(--brand, #2563eb)" : "var(--text-secondary)",
              cursor: "pointer", fontFamily: "inherit", fontWeight: activeAdvCount > 0 ? 600 : undefined,
              display: "inline-flex", alignItems: "center", gap: 6,
              whiteSpace: "nowrap",
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h18M7 12h10M11 20h2" />
            </svg>
            Filters
            {activeAdvCount > 0 && (
              <span style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                width: 18, height: 18, fontSize: 11, fontWeight: 700,
                background: "var(--brand, #2563eb)", color: "#fff", borderRadius: "50%",
              }}>
                {activeAdvCount}
              </span>
            )}
          </button>
        )}

        {/* Right actions */}
        {rightSlot && (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            {rightSlot}
          </div>
        )}
      </div>

      {/* Active filter chips */}
      {allActiveValues.length > 0 && (
        <div style={{
          display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center",
          paddingTop: 8,
        }}>
          {allActiveValues.map(([key, value]) => (
            <Chip
              key={key}
              label={getChipLabel(key, value, filters)}
              onRemove={() => removeChip(key)}
            />
          ))}
          {allActiveValues.length > 1 && (
            <button
              onClick={clearAll}
              style={{
                height: 26, padding: "0 10px", fontSize: 12,
                background: "none", border: "1px solid var(--border)",
                borderRadius: 999, cursor: "pointer", color: "var(--text-tertiary)",
                fontFamily: "inherit",
              }}
            >
              Clear all
            </button>
          )}
        </div>
      )}

      {/* Advanced Filters Drawer */}
      {advFilters.length > 0 && (
        <AdvancedDrawer
          open={drawerOpen}
          advFilters={advFilters}
          draftValues={draftValues}
          onDraftChange={handleDraftChange}
          onApply={applyDrawer}
          onReset={resetDrawer}
          onClose={closeDrawer}
        />
      )}
    </>
  );
}
