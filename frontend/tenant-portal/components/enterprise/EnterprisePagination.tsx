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
import { Pagination } from "../shared/ui";

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

export default function EnterprisePagination({
  pagination, onPage, onPageSize, pageSizes = [10, 25, 50, 100],
}: Props) {
  const { page, page_size, total_items, total_pages, has_next, has_previous } = pagination;
  return <Pagination page={page} pageSize={page_size} total={total_items} pageCount={total_pages}
    hasNext={has_next} hasPrevious={has_previous} onPage={onPage} alwaysShow
    pageSizes={pageSizes} onPageSize={size => { onPageSize(size); onPage(1); }} />;
}
