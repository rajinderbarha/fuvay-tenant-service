"use client";
/**
 * Filter bar for EnterpriseDataGrid.
 *
 * This component was written entirely in Tailwind utility classes
 * (`border rounded px-3 py-1.5 text-sm bg-white focus:ring-2 …`), but this app
 * has no Tailwind — no config, no dependency, no directives. Every other
 * component styles itself with inline styles over the CSS design tokens. So
 * none of those classes resolved and the bar rendered as raw unstyled form
 * controls: no borders, no spacing, mismatched heights, and hard-coded
 * `bg-white`/`text-gray-500` that would have been wrong in dark mode anyway.
 *
 * Rewritten against the same tokens the rest of the portal uses, so the bar
 * matches the surrounding surfaces and follows the theme.
 */
import { useState, useEffect } from "react";

export interface FilterDef {
  key:          string;
  label:        string;
  type:         "text" | "select" | "date" | "date_range";
  options?:     { value: string; label: string }[];
  placeholder?: string;
}

interface Props {
  filters:      FilterDef[];
  values:       Record<string, string>;
  onChange:     (key: string, value: string) => void;
  onReset:      () => void;
  onSearch?:    (q: string) => void;
  searchValue?: string;
  rightSlot?:   React.ReactNode;
}

const CONTROL: React.CSSProperties = {
  height: 34,
  padding: "0 10px",
  fontSize: 13,
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--surface)",
  color: "var(--text-primary)",
  fontFamily: "inherit",
  outline: "none",
  boxSizing: "border-box",
};

const LABEL: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: "var(--text-tertiary)",
  whiteSpace: "nowrap",
};

export default function EnterpriseFilterBar({
  filters, values, onChange, onReset, onSearch, searchValue = "", rightSlot,
}: Props) {
  const [localSearch, setLocalSearch] = useState(searchValue);
  useEffect(() => { setLocalSearch(searchValue); }, [searchValue]);
  const hasActiveFilters = Object.values(values).some(v => v) || Boolean(localSearch);

  return (
    <div style={{
      display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", width: "100%",
    }}>
      {onSearch !== undefined && (
        <input
          type="text"
          aria-label="Search"
          value={localSearch}
          onChange={e => setLocalSearch(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") onSearch(localSearch); }}
          onBlur={() => onSearch(localSearch)}
          placeholder="Search…"
          style={{ ...CONTROL, width: 220, background: "var(--surface-sunken)" }}
        />
      )}

      {filters.map(f => {
        if (f.type === "select") {
          return (
            <select
              key={f.key} aria-label={f.label}
              value={values[f.key] ?? ""}
              onChange={e => onChange(f.key, e.target.value)}
              style={{ ...CONTROL, minWidth: 150 }}
            >
              <option value="">{f.label}</option>
              {f.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          );
        }
        if (f.type === "date") {
          return (
            <label key={f.key} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <span style={LABEL}>{f.label}</span>
              <input
                type="date" value={values[f.key] ?? ""}
                onChange={e => onChange(f.key, e.target.value)}
                style={{ ...CONTROL, minWidth: 148 }}
              />
            </label>
          );
        }
        if (f.type === "date_range") {
          return (
            <div key={f.key} style={{ display: "flex", alignItems: "flex-end", gap: 6 }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <span style={LABEL}>{f.label} from</span>
                <input
                  type="date" value={values[`${f.key}_from`] ?? ""}
                  onChange={e => onChange(`${f.key}_from`, e.target.value)}
                  style={{ ...CONTROL, minWidth: 148 }}
                />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <span style={LABEL}>to</span>
                <input
                  type="date" value={values[`${f.key}_to`] ?? ""}
                  onChange={e => onChange(`${f.key}_to`, e.target.value)}
                  style={{ ...CONTROL, minWidth: 148 }}
                />
              </label>
            </div>
          );
        }
        return (
          <input
            key={f.key} type="text" aria-label={f.label}
            value={values[f.key] ?? ""}
            onChange={e => onChange(f.key, e.target.value)}
            placeholder={f.placeholder ?? f.label}
            style={{ ...CONTROL, width: 170 }}
          />
        );
      })}

      {hasActiveFilters && (
        <button
          onClick={onReset}
          style={{
            height: 34, padding: "0 12px", fontSize: 12, fontWeight: 600, borderRadius: 8,
            border: "1px solid var(--danger-border)", background: "var(--danger-bg)",
            color: "var(--danger-text)", cursor: "pointer", fontFamily: "inherit",
          }}
        >
          Reset
        </button>
      )}

      {rightSlot && <div style={{ marginLeft: "auto" }}>{rightSlot}</div>}
    </div>
  );
}
