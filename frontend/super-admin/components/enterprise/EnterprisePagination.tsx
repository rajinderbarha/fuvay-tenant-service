"use client";
import { useState } from "react";

interface PaginationMeta {
  page:         number;
  page_size:    number;
  total_items:  number;
  total_pages:  number;
  has_next:     boolean;
  has_previous: boolean;
}

interface Props {
  pagination: PaginationMeta;
  onPage:     (page: number) => void;
  onPageSize: (size: number) => void;
  pageSizes?: number[];
}

function PageBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        minWidth: 30, height: 30, padding: "0 8px", fontSize: 13, borderRadius: 7,
        border: "1px solid var(--border)",
        background: hov && !disabled ? "var(--surface-sunken)" : "var(--surface)",
        color: disabled ? "var(--text-tertiary)" : "var(--text-secondary)",
        cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "inherit", opacity: disabled ? 0.45 : 1,
        transition: "background 0.12s",
      }}>
      {label}
    </button>
  );
}

export default function EnterprisePagination({
  pagination, onPage, onPageSize, pageSizes = [10, 25, 50, 100],
}: Props) {
  const { page, page_size, total_items, total_pages, has_next, has_previous } = pagination;
  if (total_items === 0) return null;
  const from = (page - 1) * page_size + 1;
  const to   = Math.min(page * page_size, total_items);

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 16px", borderTop: "1px solid var(--border)",
      background: "var(--surface-sunken)", borderRadius: "0 0 12px 12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13, color: "var(--text-secondary)" }}>
        <span>{from}–{to} of {total_items.toLocaleString()}</span>
        <select value={page_size} onChange={e => { onPageSize(+e.target.value); onPage(1); }}
          style={{
            height: 30, padding: "0 8px", fontSize: 12, borderRadius: 7,
            border: "1px solid var(--border)", background: "var(--surface)",
            color: "var(--text-primary)", fontFamily: "inherit", cursor: "pointer",
          }}>
          {pageSizes.map(s => <option key={s} value={s}>{s} / page</option>)}
        </select>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <PageBtn label="«" onClick={() => onPage(1)} disabled={!has_previous} />
        <PageBtn label="‹" onClick={() => onPage(page - 1)} disabled={!has_previous} />
        <span style={{ padding: "0 12px", fontSize: 13, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
          Page {page} of {total_pages}
        </span>
        <PageBtn label="›" onClick={() => onPage(page + 1)} disabled={!has_next} />
        <PageBtn label="»" onClick={() => onPage(total_pages)} disabled={!has_next} />
      </div>
    </div>
  );
}
