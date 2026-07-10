"use client";
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

export default function EnterpriseFilterBar({
  filters, values, onChange, onReset, onSearch, searchValue = "", rightSlot,
}: Props) {
  const [localSearch, setLocalSearch] = useState(searchValue);
  useEffect(() => { setLocalSearch(searchValue); }, [searchValue]);
  const hasActiveFilters = Object.values(values).some(v => v) || localSearch;

  return (
    <div className="space-y-2 w-full">
      <div className="flex flex-wrap gap-2 items-center">
        {onSearch !== undefined && (
          <input
            type="text"
            value={localSearch}
            onChange={e => setLocalSearch(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") onSearch(localSearch); }}
            onBlur={() => onSearch(localSearch)}
            placeholder="Search…"
            className="border rounded px-3 py-1.5 text-sm w-52 bg-white focus:ring-2 ring-blue-300 outline-none"
          />
        )}

        {filters.map(f => {
          if (f.type === "select") {
            return (
              <select key={f.key} value={values[f.key] ?? ""} onChange={e => onChange(f.key, e.target.value)}
                className="border rounded px-2 py-1.5 text-sm bg-white">
                <option value="">{f.label}</option>
                {f.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            );
          }
          if (f.type === "date") {
            return (
              <div key={f.key} className="flex items-center gap-1">
                <label className="text-xs text-gray-500">{f.label}</label>
                <input type="date" value={values[f.key] ?? ""} onChange={e => onChange(f.key, e.target.value)}
                  className="border rounded px-2 py-1.5 text-sm bg-white" />
              </div>
            );
          }
          if (f.type === "date_range") {
            return (
              <div key={f.key} className="flex items-center gap-1">
                <label className="text-xs text-gray-500">{f.label}</label>
                <input type="date" value={values[`${f.key}_from`] ?? ""} onChange={e => onChange(`${f.key}_from`, e.target.value)}
                  className="border rounded px-2 py-1.5 text-sm bg-white" />
                <span className="text-gray-400 text-xs">to</span>
                <input type="date" value={values[`${f.key}_to`] ?? ""} onChange={e => onChange(`${f.key}_to`, e.target.value)}
                  className="border rounded px-2 py-1.5 text-sm bg-white" />
              </div>
            );
          }
          return (
            <input key={f.key} type="text" value={values[f.key] ?? ""} onChange={e => onChange(f.key, e.target.value)}
              placeholder={f.placeholder ?? f.label}
              className="border rounded px-2 py-1.5 text-sm w-40 bg-white" />
          );
        })}

        {hasActiveFilters && (
          <button onClick={onReset}
            className="text-xs text-red-500 hover:text-red-700 px-2 py-1.5 border border-red-200 rounded hover:bg-red-50">
            Reset
          </button>
        )}

        {rightSlot && <div className="ml-auto">{rightSlot}</div>}
      </div>
    </div>
  );
}
