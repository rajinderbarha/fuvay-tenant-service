"use client";
import React, { useState } from "react";
export interface SearchResult { id: string; label: string; description?: string; type?: string; href?: string; }
export interface GlobalSearchProps {
  placeholder?: string; results?: SearchResult[];
  onSearch?: (q: string) => void; onSelect?: (r: SearchResult) => void;
  loading?: boolean; width?: number|string;
}
export function GlobalSearch({ placeholder = "Search…", results = [], onSearch, onSelect, loading, width = 360 }: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value); onSearch?.(e.target.value);
  }
  const show = focused && query.length > 0;
  return (
    <div style={{ position:"relative", width }}>
      <div style={{ position:"relative" }}>
        <span style={{ position:"absolute", left:11, top:"50%", transform:"translateY(-50%)",
          color:"var(--color-text-tertiary)", fontSize:14, pointerEvents:"none" }}>⌕</span>
        <input value={query} onChange={handleChange}
          onFocus={() => setFocused(true)} onBlur={() => setTimeout(() => setFocused(false), 200)}
          placeholder={placeholder} role="searchbox" aria-label={placeholder}
          style={{ width:"100%", height:36, padding:"0 12px 0 34px", fontSize:"var(--text-sm)",
            background:"var(--color-surface-sunken)", border:"1px solid var(--color-border)",
            borderRadius:"var(--radius-md)", color:"var(--color-text-primary)", outline:"none",
            fontFamily:"var(--font-sans)", transition:"all 0.15s", boxSizing:"border-box" as const }}
          onFocus={e => { e.currentTarget.style.background = "var(--color-surface-base)"; e.currentTarget.style.borderColor = "var(--color-border-focus)"; }}
          onBlur={e  => { e.currentTarget.style.background = "var(--color-surface-sunken)"; e.currentTarget.style.borderColor = "var(--color-border)"; }}
        />
        {loading && <span style={{ position:"absolute", right:11, top:"50%", transform:"translateY(-50%)",
          fontSize:12, color:"var(--color-text-tertiary)" }}>⏳</span>}
      </div>
      {show && results.length > 0 && (
        <div role="listbox" style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0,
          background:"var(--color-surface-elevated)", border:"1px solid var(--color-border)",
          borderRadius:"var(--radius-lg)", boxShadow:"var(--shadow-lg)",
          zIndex:"var(--z-dropdown)" as unknown as number, overflow:"hidden",
          animation:"slideUp 0.15s ease" }}>
          {results.map(r => (
            <div key={r.id} role="option" onClick={() => { onSelect?.(r); setQuery(""); setFocused(false); }}
              style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 14px",
                cursor:"pointer", borderBottom:"1px solid var(--color-border)" }}
              onMouseEnter={e=>(e.currentTarget as HTMLDivElement).style.background="var(--color-surface-sunken)"}
              onMouseLeave={e=>(e.currentTarget as HTMLDivElement).style.background="transparent"}>
              {r.type && <span style={{ fontSize:"var(--text-xs)", padding:"2px 6px",
                borderRadius:"var(--radius-sm)", background:"var(--color-accent-muted)",
                color:"var(--color-accent)", fontWeight:"var(--font-semibold)" }}>{r.type}</span>}
              <div style={{ flex:1, minWidth:0 }}>
                <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
                  color:"var(--color-text-primary)", margin:0, overflow:"hidden",
                  textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{r.label}</p>
                {r.description && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
                  margin:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{r.description}</p>}
              </div>
              <span style={{ fontSize:12, color:"var(--color-text-tertiary)" }}>↵</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
