"use client";
import React, { useState } from "react";
import { Badge } from "../shared/ui";
import type { AdminMasterServiceRow } from "../../lib/api";
import { Search, CheckCircle2 } from "lucide-react";

/** Step 2: Service. Schema-driven -- lists master services available to
 * this tenant for the selected category (already entitlement-filtered by
 * the backend). No hardcoded service names. Never renders base_price/
 * min_price/max_price/visit_fee from this list -- those are admin-side
 * reference fields the tenant must never see as "the price"; the tenant's
 * OWN price is configured later in this same wizard. */
export function ServiceSelector({ services, selectedServiceId, onSelect }: {
  services: AdminMasterServiceRow[];
  selectedServiceId: string | null;
  onSelect: (s: AdminMasterServiceRow) => void;
}) {
  const [q, setQ] = useState("");
  const filtered = services.filter(s =>
    !q || s.service_name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px" }}>Which service do you offer?</h1>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
        Pick the service you want to configure. You'll set your own pricing in a later step.
      </p>
      <div style={{ position: "relative", marginBottom: 16 }}>
        <Search size={14} style={{ position: "absolute", left: 10, top: 11, color: "var(--text-tertiary)" }} />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search services…"
          style={{ width: "100%", height: 36, paddingLeft: 32, borderRadius: "var(--radius-md)",
            border: "1px solid var(--border)", background: "var(--input-bg)", color: "var(--text-primary)",
            fontSize: 13, boxSizing: "border-box" }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px,1fr))", gap: 12 }}>
        {filtered.map(s => {
          const selected = s.service_id === selectedServiceId;
          const already = !!s.is_enabled;
          return (
            <button key={s.service_id} type="button" onClick={() => onSelect(s)}
              aria-pressed={selected}
              style={{
                textAlign: "left", padding: "14px 16px", borderRadius: "var(--radius-lg)",
                border: `2px solid ${selected ? "var(--accent)" : "var(--border)"}`,
                background: selected ? "var(--accent-muted)" : "var(--surface)",
                cursor: "pointer", fontFamily: "inherit",
                display: "flex", flexDirection: "column", gap: 6,
              }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>{s.service_name}</p>
                {selected && <CheckCircle2 size={16} color="var(--accent)" />}
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {already && <Badge variant="info" size="sm">Already configured</Badge>}
                {s.is_type_required && <Badge variant="muted" size="sm">Has types</Badge>}
                {s.is_brand_required && <Badge variant="muted" size="sm">Has brands</Badge>}
              </div>
            </button>
          );
        })}
        {filtered.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No services match your search.</p>
        )}
      </div>
    </div>
  );
}
