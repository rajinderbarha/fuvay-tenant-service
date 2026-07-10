"use client";
import React from "react";
export interface CursorPaginationProps {
  hasNext: boolean; hasPrev?: boolean; onNext: ()=>void; onPrev?: ()=>void;
  total?: number; pageSize?: number; loading?: boolean;
  nextLabel?: string; prevLabel?: string;
}
export function CursorPagination({ hasNext, hasPrev, onNext, onPrev, total, pageSize, loading, nextLabel = "Next →", prevLabel = "← Prev" }: CursorPaginationProps) {
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"12px 0", gap:10, flexWrap:"wrap" }}>
      {total != null && (
        <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-tertiary)", margin:0 }}>
          {total.toLocaleString()} result{total !== 1 ? "s" : ""}
          {pageSize && `, ${pageSize} per page`}
        </p>
      )}
      <div style={{ display:"flex", gap:8, marginLeft:"auto" }}>
        {hasPrev && onPrev && (
          <button onClick={onPrev} disabled={loading}
            style={{ padding:"7px 14px", borderRadius:"var(--radius-md)",
              border:"1px solid var(--color-border)", background:"var(--color-surface-base)",
              color:"var(--color-text-secondary)", cursor: loading ? "not-allowed" : "pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)",
              opacity: loading ? 0.6 : 1, transition:"all 0.15s" }}
            onMouseEnter={e=>(e.currentTarget as HTMLButtonElement).style.borderColor="var(--color-border-strong)"}
            onMouseLeave={e=>(e.currentTarget as HTMLButtonElement).style.borderColor="var(--color-border)"}>
            {prevLabel}
          </button>
        )}
        <button onClick={onNext} disabled={!hasNext || loading}
          style={{ padding:"7px 14px", borderRadius:"var(--radius-md)",
            border:"none", background: !hasNext ? "var(--color-surface-sunken)" : "var(--color-brand-500)",
            color: !hasNext ? "var(--color-text-tertiary)" : "white",
            cursor: !hasNext || loading ? "not-allowed" : "pointer",
            fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-medium)",
            opacity: loading ? 0.6 : 1, transition:"all 0.15s" }}>
          {loading ? "Loading…" : nextLabel}
        </button>
      </div>
    </div>
  );
}
