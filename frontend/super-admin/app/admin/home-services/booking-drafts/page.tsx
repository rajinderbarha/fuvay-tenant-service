"use client";

import { useEffect, useState, useCallback } from "react";
import {
  adminHomeServiceBookingApi,
  HomeServiceBookingDraft,
  HomeServiceBookingDraftEvent,
  ServiceOSError,
} from "@/lib/api";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  draft:                  { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  collecting_details:     { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  serviceability_checked: { background: "var(--info-bg)",        color: "var(--info-text)" },
  price_estimated:        { background: "var(--info-bg)",        color: "var(--info-text)" },
  provider_matched:       { background: "var(--info-bg)",        color: "var(--info-text)" },
  ready_for_confirmation: { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  confirmed:              { background: "var(--success-bg)",     color: "var(--success-text)" },
  expired:                { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  cancelled:              { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  failed:                 { background: "var(--danger-bg)",      color: "var(--danger-text)" },
};

const SVCABILITY_COLOR: Record<string, string> = {
  pending:          "var(--text-tertiary)",
  serviceable:      "var(--success-text)",
  not_serviceable:  "var(--danger-text)",
};

const ACTOR_STYLE: Record<string, React.CSSProperties> = {
  backend: { background: "var(--info-bg)", color: "var(--info-text)" },
  ai:      { background: "var(--surface)", color: "var(--text-secondary)", border: "1px solid var(--border)" },
};

const th: React.CSSProperties = {
  padding: "10px 16px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

const btnPageStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 13, borderRadius:"var(--radius-md)", cursor: "pointer", fontFamily: "inherit",
  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
};

const selStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};

function DraftDetailModal({ draft, onClose }: { draft: HomeServiceBookingDraft; onClose: () => void }) {
  const [events, setEvents] = useState<HomeServiceBookingDraftEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  useEffect(() => {
    setLoadingEvents(true);
    adminHomeServiceBookingApi.getDraftEvents(draft.id)
      .then((res) => setEvents(res.events))
      .catch(console.error)
      .finally(() => setLoadingEvents(false));
  }, [draft.id]);

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)" }}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-xl, 1rem)", boxShadow: "0 16px 48px rgba(0,0,0,0.22)",
        width: "100%", maxWidth: 720, maxHeight: "90vh", overflowY: "auto", padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
              Booking Draft — {draft.offering_name ?? draft.offering_id.slice(0, 8)}
            </h2>
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{draft.id}</p>
          </div>
          <button onClick={onClose} style={{ fontSize: 22, background: "none", border: "none", cursor: "pointer",
            color: "var(--text-tertiary)", lineHeight: 1 }}>&times;</button>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, fontWeight: 600,
            ...(STATUS_STYLE[draft.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
            {draft.status}
          </span>
          {draft.serviceability_status && (
            <span style={{ fontSize: 11, fontWeight: 500,
              color: SVCABILITY_COLOR[draft.serviceability_status] ?? "var(--text-secondary)" }}>
              Svc: {draft.serviceability_status}
            </span>
          )}
          {draft.price_status && (
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Price: {draft.price_status}</span>
          )}
          {draft.provider_match_status && (
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Provider: {draft.provider_match_status}</span>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: 13, marginBottom: 16 }}>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Offering</p>
            <p style={{ fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{draft.offering_name ?? "—"}</p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Category</p>
            <p style={{ color: "var(--text-primary)", margin: 0 }}>{draft.category_name ?? "—"}</p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>City / Zipcode</p>
            <p style={{ color: "var(--text-primary)", margin: 0 }}>
              {draft.city ?? "—"} {draft.zipcode ? `(${draft.zipcode})` : ""}
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Customer</p>
            <p style={{ color: "var(--text-primary)", margin: "0 0 2px" }}>
              {draft.customer_name ?? draft.customer_id?.slice(0, 8) ?? "Guest"}
            </p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{draft.customer_phone ?? ""}</p>
          </div>
          <div style={{ gridColumn: "span 2" }}>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Issue Summary</p>
            <p style={{ color: "var(--text-primary)", margin: 0 }}>{draft.issue_summary ?? "—"}</p>
          </div>
          {draft.price_snapshot && (
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Price Estimate</p>
              <p style={{ fontWeight: 700, color: "var(--success-text)", margin: "0 0 2px" }}>
                {(draft.price_snapshot as Record<string, unknown>)["display_price"] as string ?? "—"}
              </p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                {(draft.price_snapshot as Record<string, unknown>)["note"] as string ?? ""}
              </p>
            </div>
          )}
          {draft.selected_provider_snapshot && (
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Selected Provider</p>
              <p style={{ color: "var(--text-primary)", margin: 0 }}>
                {(draft.selected_provider_snapshot as Record<string, unknown>)["business_name"] as string ?? "—"}
              </p>
            </div>
          )}
        </div>

        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Event Log</p>
          {loadingEvents ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading events…</p>
          ) : events.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No events.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 192, overflowY: "auto" }}>
              {events.map((e) => (
                <div key={e.id} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 11,
                  borderLeft: "2px solid var(--border)", paddingLeft: 8, paddingTop: 2, paddingBottom: 2 }}>
                  <span style={{ color: "var(--text-tertiary)", flexShrink: 0, width: 80 }}>
                    {new Date(e.created_at).toLocaleTimeString()}
                  </span>
                  <span style={{ flexShrink: 0, padding: "1px 5px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                    ...(ACTOR_STYLE[e.actor_type] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                    {e.actor_type}
                  </span>
                  <span style={{ color: "var(--text-primary)" }}>{e.event_type}</span>
                  {e.message && <span style={{ color: "var(--text-tertiary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.message}</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {draft.booking_summary && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 6px" }}>Booking Summary</p>
            <pre style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 10, fontSize: 11,
              overflowX: "auto", color: "var(--text-primary)", margin: 0 }}>
              {JSON.stringify(draft.booking_summary, null, 2)}
            </pre>
          </div>
        )}

        <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnPageStyle}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function HomeServiceBookingDraftsPage() {
  const [drafts, setDrafts]           = useState<HomeServiceBookingDraft[]>([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);
  const [selectedDraft, setSelected]  = useState<HomeServiceBookingDraft | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCity, setFilterCity]   = useState("");
  const [page, setPage]               = useState(1);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await adminHomeServiceBookingApi.listDrafts({
        page, page_size: 25,
        status: filterStatus || undefined,
        city:   filterCity   || undefined,
      });
      setDrafts(res.drafts);
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Failed to load drafts");
    } finally { setLoading(false); }
  }, [page, filterStatus, filterCity]);

  useEffect(() => { void load(); }, [load]);

  const STATUSES = [
    "draft", "collecting_details", "serviceability_checked",
    "price_estimated", "provider_matched", "ready_for_confirmation",
    "confirmed", "expired", "cancelled", "failed",
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
            Home Service Booking Drafts
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Pre-booking chatbot drafts — Sprint 16. Read-only admin view.
          </p>
        </div>
        <button onClick={() => void load()} style={btnPageStyle}>Refresh</button>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }} style={selStyle}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input type="text" placeholder="Filter by city…" value={filterCity}
          onChange={(e) => { setFilterCity(e.target.value); setPage(1); }}
          style={{ height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
            background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit" }}
        />
      </div>

      {error ? (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 10,
          padding: 16, fontSize: 13, color: "var(--danger-text)" }}>{error}</div>
      ) : loading ? (
        <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading drafts…</div>
      ) : drafts.length === 0 ? (
        <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-lg)", padding: "40px 0", textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No booking drafts found.</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
            Drafts appear here when customers start the chatbot booking flow.
          </p>
        </div>
      ) : (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Draft ID","Customer","Offering","City","Zipcode","Status","Serviceability","Price","Provider Match","Created",""].map((h) => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {drafts.map((d) => (
                  <tr key={d.id} style={{ borderBottom: "1px solid var(--border)", cursor: "pointer" }} onClick={() => setSelected(d)}>
                    <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {d.id.slice(0, 8)}…
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {d.customer_name ?? (d.customer_id ? d.customer_id.slice(0, 8) + "…" : "Guest")}
                    </td>
                    <td style={{ padding: "10px 16px", fontWeight: 500, color: "var(--text-primary)" }}>{d.offering_name ?? "—"}</td>
                    <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{d.city ?? "—"}</td>
                    <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {d.zipcode ?? "—"}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, fontWeight: 600,
                        ...(STATUS_STYLE[d.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                        {d.status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, fontWeight: 500,
                      color: SVCABILITY_COLOR[d.serviceability_status ?? "pending"] ?? "var(--text-tertiary)" }}>
                      {d.serviceability_status ?? "pending"}
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {d.price_snapshot
                        ? (d.price_snapshot as Record<string, unknown>)["display_price"] as string
                        : d.price_status ?? "—"}
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {d.provider_match_status ?? "—"}
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {new Date(d.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <button onClick={(e) => { e.stopPropagation(); setSelected(d); }}
                        style={{ fontSize: 12, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 12 }}>
            <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
              style={{ ...btnPageStyle, opacity: page === 1 ? 0.4 : 1, cursor: page === 1 ? "not-allowed" : "pointer" }}>
              Previous
            </button>
            <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Page {page}</span>
            <button disabled={drafts.length < 25} onClick={() => setPage((p) => p + 1)}
              style={{ ...btnPageStyle, opacity: drafts.length < 25 ? 0.4 : 1, cursor: drafts.length < 25 ? "not-allowed" : "pointer" }}>
              Next
            </button>
          </div>
        </div>
      )}

      {selectedDraft && (
        <DraftDetailModal draft={selectedDraft} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
