"use client";
import { useState } from "react";

export interface ColumnDef {
  key:     string;
  label:   string;
  visible: boolean;
  order:   number;
  width?:  number;
}

interface Props {
  columns:  ColumnDef[];
  onChange: (columns: ColumnDef[]) => void;
  onReset?: () => void;
}

export default function EnterpriseColumnManager({ columns, onChange, onReset }: Props) {
  const [open, setOpen] = useState(false);
  const toggle = (key: string) => onChange(columns.map(c => c.key === key ? { ...c, visible: !c.visible } : c));
  const visibleCount = columns.filter(c => c.visible).length;

  return (
    <div className="relative">
      <button onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 border rounded px-2.5 py-1.5 text-sm bg-white hover:bg-gray-50">
        <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
        </svg>
        Columns <span className="text-xs text-gray-400">({visibleCount}/{columns.length})</span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-white border rounded-xl shadow-lg p-3 w-52 space-y-1.5">
            <p className="text-xs font-medium text-gray-500 pb-1 border-b">Visible Columns</p>
            {columns.sort((a, b) => a.order - b.order).map(c => (
              <label key={c.key} className="flex items-center gap-2 text-sm cursor-pointer hover:text-gray-900">
                <input type="checkbox" checked={c.visible} onChange={() => toggle(c.key)} className="w-3.5 h-3.5" />
                {c.label}
              </label>
            ))}
            {onReset && (
              <button onClick={() => { onReset(); setOpen(false); }}
                className="w-full text-xs text-red-500 hover:text-red-700 pt-1 border-t mt-1">
                Reset to defaults
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
