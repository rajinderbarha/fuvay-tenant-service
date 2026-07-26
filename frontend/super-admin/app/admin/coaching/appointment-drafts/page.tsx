"use client";

import { useEffect, useState, useCallback } from "react";
import {
  adminCoachingAppointmentApi,
  CoachingAppointmentDraft,
  CoachingAppointmentDraftEvent,
  CoachingAppointmentSlotHold,
  ServiceOSError,
} from "@/lib/api";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  draft:                  { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  collecting_details:     { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  location_checked:       { background: "var(--info-bg)",        color: "var(--info-text)" },
  slots_loaded:           { background: "var(--info-bg)",        color: "var(--info-text)" },
  slot_selected:          { background: "var(--info-bg)",        color: "var(--info-text)" },
  ready_for_confirmation: { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  confirmed:              { background: "var(--success-bg)",     color: "var(--success-text)" },
  expired:                { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  cancelled:              { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  failed:                 { background: "var(--danger-bg)",      color: "var(--danger-text)" },
};

const HOLD_STYLE: Record<string, React.CSSProperties> = {
  held:      { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  released:  { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  converted: { background: "var(--success-bg)",     color: "var(--success-text)" },
  expired:   { background: "var(--danger-bg)",      color: "var(--danger-text)" },
};

const ACTOR_STYLE: Record<string, React.CSSProperties> = {
  backend: { background: "var(--info-bg)",     color: "var(--info-text)" },
  ai:      { background: "var(--surface)",     color: "var(--text-secondary)", border: "1px solid var(--border)" },
};

const th: React.CSSProperties = {
  padding: "10px 16px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

const btnPageStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 13, borderRadius:"var(--radius-md)", cursor: "pointer", fontFamily: "inherit",
  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
};

function DraftDetailModal({ draft, onClose }: { draft: CoachingAppointmentDraft; onClose: () => void }) {
  const [events, setEvents] = useState<CoachingAppointmentDraftEvent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    adminCoachingAppointmentApi.getDraftEvents(draft.id)
      .then((res) => setEvents(res.events))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [draft.id]);

  const fee = draft.appointment_fee_snapshot as Record<string, unknown> | null;
  const slot = draft.slot_snapshot as Record<string, unknown> | null;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)" }}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-xl, 1rem)", boxShadow: "0 16px 48px rgba(0,0,0,0.22)",
        width: "100%", maxWidth: 720, maxHeight: "90vh", overflowY: "auto", padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
              Coaching Draft — {draft.offering_name ?? draft.offering_id.slice(0, 8)}
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
          {draft.location_status && (
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, background: "var(--surface-sunken)", color: "var(--text-tertiary)" }}>
              Location: {draft.location_status}
            </span>
          )}
          {draft.slot_status && (
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, background: "var(--surface-sunken)", color: "var(--text-tertiary)" }}>
              Slot: {draft.slot_status}
            </span>
          )}
          {draft.fee_status && (
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, background: "var(--surface-sunken)", color: "var(--text-tertiary)" }}>
              Fee: {draft.fee_status}
            </span>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: 13, marginBottom: 16 }}>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Student</p>
            <p style={{ fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{draft.student_name ?? "—"}</p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{draft.student_phone ?? ""}</p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Target</p>
            <p style={{ color: "var(--text-primary)", margin: 0 }}>
              {draft.target_exam ?? "—"} {draft.target_band ? `(Band ${draft.target_band})` : ""}
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Mode / Location</p>
            <p style={{ color: "var(--text-primary)", margin: 0 }}>
              {draft.preferred_mode ?? "—"} — {draft.city ?? "—"} {draft.zipcode ? `(${draft.zipcode})` : ""}
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Selected Slot</p>
            <p style={{ color: "var(--text-primary)", margin: 0 }}>
              {draft.selected_date ?? "—"} {draft.selected_time_start ? `at ${draft.selected_time_start}` : ""}
            </p>
          </div>
          {fee && (
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Appointment Fee</p>
              <p style={{ fontWeight: 700, color: "var(--success-text)", margin: 0 }}>
                {fee["display_fee"] as string ?? fee["fee_type"] as string ?? "—"}
              </p>
            </div>
          )}
          {slot && (
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Slot Snapshot</p>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>
                {slot["slot_date"] as string} {slot["start_time"] as string}–{slot["end_time"] as string}
                {slot["mode"] ? ` (${slot["mode"]})` : ""}
              </p>
            </div>
          )}
        </div>

        {draft.next_available_slots && draft.next_available_slots.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Next Available Slots</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 128, overflowY: "auto" }}>
              {(draft.next_available_slots as Record<string, unknown>[]).map((s, i) => (
                <div key={i} style={{ fontSize: 11, background: "var(--info-bg)", borderRadius: 6, padding: "4px 8px",
                  display: "flex", gap: 8, alignItems: "center", color: "var(--info-text)" }}>
                  {s["is_recommended"] && (
                    <span style={{ background: "var(--brand)", color: "white", padding: "1px 5px", borderRadius: 4, fontSize: 10 }}>
                      Recommended
                    </span>
                  )}
                  <span>{s["slot_date"] as string} {s["start_time"] as string}</span>
                  <span style={{ color: "var(--text-tertiary)" }}>{s["business_name"] as string}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {draft.fallback_inquiry_payload && (
          <div style={{ marginBottom: 16, background: "var(--warning-bg)", border: "1px solid var(--warning-border, var(--border))",
            borderRadius: 10, padding: 12 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--warning-text)", margin: "0 0 6px" }}>Fallback Inquiry Prepared</p>
            <pre style={{ fontSize: 11, color: "var(--text-secondary)", overflowX: "auto", margin: 0 }}>
              {JSON.stringify(draft.fallback_inquiry_payload, null, 2)}
            </pre>
          </div>
        )}

        {draft.appointment_summary && (
          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 6px" }}>Appointment Summary</p>
            <pre style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 10, fontSize: 11,
              overflowX: "auto", color: "var(--text-primary)", margin: 0 }}>
              {JSON.stringify(draft.appointment_summary, null, 2)}
            </pre>
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Event Log</p>
          {loading ? (
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

        <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ ...btnPageStyle }}>Close</button>
        </div>
      </div>
    </div>
  );
}

type Tab = "drafts" | "holds";

const selStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};

export default function CoachingAppointmentDraftsPage() {
  const [tab, setTab]                   = useState<Tab>("drafts");
  const [drafts, setDrafts]             = useState<CoachingAppointmentDraft[]>([]);
  const [holds,  setHolds]              = useState<CoachingAppointmentSlotHold[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [selectedDraft, setSelected]    = useState<CoachingAppointmentDraft | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCity, setFilterCity]     = useState("");
  const [page, setPage]                 = useState(1);

  const loadDrafts = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await adminCoachingAppointmentApi.listDrafts({
        page, page_size: 25,
        status: filterStatus || undefined,
        city:   filterCity   || undefined,
      });
      setDrafts(res.drafts);
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Failed to load drafts");
    } finally { setLoading(false); }
  }, [page, filterStatus, filterCity]);

  const loadHolds = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await adminCoachingAppointmentApi.listSlotHolds({ page, page_size: 25 });
      setHolds(res.holds);
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Failed to load slot holds");
    } finally { setLoading(false); }
  }, [page]);

  useEffect(() => {
    if (tab === "drafts") void loadDrafts();
    else void loadHolds();
  }, [tab, loadDrafts, loadHolds]);

  const STATUSES = [
    "draft", "collecting_details", "location_checked", "slots_loaded",
    "slot_selected", "ready_for_confirmation", "confirmed", "expired", "cancelled", "failed",
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
            Coaching Appointment Drafts
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Sprint 17 — Read-only admin view of coaching/IELTS appointment pre-flow.
          </p>
        </div>
        <button onClick={() => tab === "drafts" ? void loadDrafts() : void loadHolds()} style={btnPageStyle}>
          Refresh
        </button>
      </div>

      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)" }}>
        {(["drafts", "holds"] as Tab[]).map((t) => (
          <button key={t} onClick={() => { setTab(t); setPage(1); }} style={{
            padding: "8px 16px", fontSize: 13, fontWeight: 500, border: "none", background: "none",
            cursor: "pointer", fontFamily: "inherit",
            borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
            color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)", marginBottom: -1,
          }}>
            {t === "drafts" ? "Appointment Drafts" : "Slot Holds"}
          </button>
        ))}
      </div>

      {tab === "drafts" && (
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
      )}

      {error && (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 10,
          padding: 16, fontSize: 13, color: "var(--danger-text)" }}>{error}</div>
      )}

      {!error && tab === "drafts" && (
        loading ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading drafts…</div>
        ) : drafts.length === 0 ? (
          <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-lg)", padding: "40px 0", textAlign: "center" }}>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No coaching appointment drafts found.</p>
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                    {["Draft ID","Student","Exam","Mode","City","Date","Status","Slot","Fee","Created",""].map((h) => (
                      <th key={h} style={th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {drafts.map((d) => (
                    <tr key={d.id} style={{ borderBottom: "1px solid var(--border)", cursor: "pointer" }}
                      onClick={() => setSelected(d)}>
                      <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                        {d.id.slice(0, 8)}…
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>
                        <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>{d.student_name ?? "—"}</div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{d.student_phone ?? ""}</div>
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{d.target_exam ?? "—"}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{d.preferred_mode ?? "—"}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{d.city ?? "—"}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{d.selected_date ?? "—"}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, fontWeight: 600,
                          ...(STATUS_STYLE[d.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                          {d.status}
                        </span>
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{d.slot_status ?? "—"}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {d.appointment_fee_snapshot
                          ? (d.appointment_fee_snapshot as Record<string, unknown>)["display_fee"] as string
                          : d.fee_status ?? "—"}
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
        )
      )}

      {!error && tab === "holds" && (
        loading ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading slot holds…</div>
        ) : holds.length === 0 ? (
          <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-lg)", padding: "40px 0", textAlign: "center" }}>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No slot holds found.</p>
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                    {["Hold ID","Draft ID","Slot Date","Time","Status","Expires At","Created"].map((h) => (
                      <th key={h} style={th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {holds.map((h) => (
                    <tr key={h.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{h.id.slice(0, 8)}…</td>
                      <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{h.draft_id.slice(0, 8)}…</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{h.slot_date}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{h.start_time} – {h.end_time}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, fontWeight: 600,
                          ...(HOLD_STYLE[h.hold_status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                          {h.hold_status}
                        </span>
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(h.expires_at).toLocaleString()}</td>
                      <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(h.created_at).toLocaleString()}</td>
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
              <button disabled={holds.length < 25} onClick={() => setPage((p) => p + 1)}
                style={{ ...btnPageStyle, opacity: holds.length < 25 ? 0.4 : 1, cursor: holds.length < 25 ? "not-allowed" : "pointer" }}>
                Next
              </button>
            </div>
          </div>
        )
      )}

      {selectedDraft && (
        <DraftDetailModal draft={selectedDraft} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
