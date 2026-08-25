"use client";
/**
 * Pagination footer for EnterpriseDataGrid.
 *
 * Third of the three enterprise-grid components written in Tailwind utilities
 * in an app with no Tailwind (see EnterpriseFilterBar / EnterpriseColumnManager).
 * Nothing resolved, so the footer rendered as bare text and four unstyled
 * `«  ‹  ›  »` buttons with no borders, no spacing and no disabled state —
 * and its hard-coded `bg-gray-50` / `text-gray-600` would have been wrong in
 * dark mode regardless.
 *
 * Rewritten with inline styles over the CSS design tokens, and the arrow
 * glyphs replaced with labelled controls so the buttons are usable and
 * screen-reader friendly.
 */
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

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

function navBtn(disabled: boolean): React.CSSProperties {
  return {
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    width: 30, height: 30, borderRadius: 8,
    border: "1px solid var(--border)", background: "var(--surface)",
    color: disabled ? "var(--text-tertiary)" : "var(--text-secondary)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.45 : 1, fontFamily: "inherit",
  };
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
      gap: 12, flexWrap: "wrap", padding: "12px 14px",
      borderTop: "1px solid var(--border)", background: "var(--surface-sunken)",
      borderBottomLeftRadius: 12, borderBottomRightRadius: 12,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>
          {from}–{to} of {total_items.toLocaleString()}
        </span>
        <select
          aria-label="Rows per page"
          value={page_size}
          onChange={e => { onPageSize(+e.target.value); onPage(1); }}
          style={{
            height: 30, padding: "0 8px", fontSize: 12.5, borderRadius: 8,
            border: "1px solid var(--border)", background: "var(--surface)",
            color: "var(--text-primary)", fontFamily: "inherit",
          }}
        >
          {pageSizes.map(s => <option key={s} value={s}>{s} / page</option>)}
        </select>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <button aria-label="First page" onClick={() => onPage(1)} disabled={!has_previous} style={navBtn(!has_previous)}>
          <ChevronsLeft size={14}/>
        </button>
        <button aria-label="Previous page" onClick={() => onPage(page - 1)} disabled={!has_previous} style={navBtn(!has_previous)}>
          <ChevronLeft size={14}/>
        </button>
        <span style={{ padding: "0 8px", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
          Page {page} of {total_pages}
        </span>
        <button aria-label="Next page" onClick={() => onPage(page + 1)} disabled={!has_next} style={navBtn(!has_next)}>
          <ChevronRight size={14}/>
        </button>
        <button aria-label="Last page" onClick={() => onPage(total_pages)} disabled={!has_next} style={navBtn(!has_next)}>
          <ChevronsRight size={14}/>
        </button>
      </div>
    </div>
  );
}
