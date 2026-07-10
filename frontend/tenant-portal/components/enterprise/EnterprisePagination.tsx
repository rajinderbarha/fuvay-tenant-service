"use client";

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
  if (total_items === 0) return null;
  const from = (page - 1) * page_size + 1;
  const to   = Math.min(page * page_size, total_items);

  return (
    <div className="flex items-center justify-between px-3 py-3 border-t bg-gray-50 rounded-b-lg">
      <div className="flex items-center gap-3 text-sm text-gray-600">
        <span>{from}–{to} of {total_items.toLocaleString()}</span>
        <select value={page_size} onChange={e => { onPageSize(+e.target.value); onPage(1); }}
          className="border rounded px-2 py-1 text-sm bg-white">
          {pageSizes.map(s => <option key={s} value={s}>{s} / page</option>)}
        </select>
      </div>
      <div className="flex items-center gap-1">
        <button onClick={() => onPage(1)} disabled={!has_previous}
          className="px-2 py-1 rounded text-sm border bg-white disabled:opacity-40 hover:bg-gray-100">«</button>
        <button onClick={() => onPage(page - 1)} disabled={!has_previous}
          className="px-2 py-1 rounded text-sm border bg-white disabled:opacity-40 hover:bg-gray-100">‹</button>
        <span className="px-3 py-1 text-sm font-medium">Page {page} of {total_pages}</span>
        <button onClick={() => onPage(page + 1)} disabled={!has_next}
          className="px-2 py-1 rounded text-sm border bg-white disabled:opacity-40 hover:bg-gray-100">›</button>
        <button onClick={() => onPage(total_pages)} disabled={!has_next}
          className="px-2 py-1 rounded text-sm border bg-white disabled:opacity-40 hover:bg-gray-100">»</button>
      </div>
    </div>
  );
}
