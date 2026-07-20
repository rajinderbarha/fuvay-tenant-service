"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { homeServiceExecutionApi, ExecutionEventRecord, ExecutionNoteRecord, PartsRequestRecord, serviceJobAssignmentApi } from "../../../../../lib/api";
import { useBreadcrumbOverride } from "../../../../../components/layout/Breadcrumbs";

const STATUS_ACTIONS: Record<string, { label: string; action: string }[]> = {
  accepted:          [{ label: "On the Way", action: "on_the_way" }],
  scheduled:         [{ label: "On the Way", action: "on_the_way" }],
  on_the_way:        [{ label: "Reached Site", action: "reached_site" }],
  reached_site:      [{ label: "Start Inspection", action: "start_inspection" }],
  inspection_started:[{ label: "Complete Inspection", action: "complete_inspection" }],
  inspection_done:   [
    { label: "Start Service", action: "start_service" },
    { label: "Quote Required", action: "quote_required" },
  ],
  service_started:   [
    { label: "Work Done", action: "work_done" },
    { label: "Quote Required", action: "quote_required" },
  ],
};

export default function JobExecutionPage() {
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<Record<string, unknown> | null>(null);
  const [timeline, setTimeline] = useState<ExecutionEventRecord[]>([]);
  const [notes, setNotes] = useState<ExecutionNoteRecord[]>([]);
  const [partsRequests, setPartsRequests] = useState<PartsRequestRecord[]>([]);
  const [partsActionLoading, setPartsActionLoading] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [noteText, setNoteText] = useState("");
  const [noteLoading, setNoteLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [quoteNote, setQuoteNote] = useState("");
  const [showQuoteModal, setShowQuoteModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [showCancelModal, setShowCancelModal] = useState(false);

  async function loadJob() {
    try {
      // HS8B fix: this page previously never fetched the job itself —
      // `job` stayed null forever, so `STATUS_ACTIONS[status]` always
      // resolved against an empty string and the status action bar never
      // rendered for any job. Fixed by loading real job data (which also
      // now carries HS8B's `completion_data` for the Completion Proof
      // section below).
      const [ctxRes, tlRes, notesRes, partsRes] = await Promise.all([
        serviceJobAssignmentApi.getContext(jobId),
        homeServiceExecutionApi.getProviderTimeline(jobId),
        homeServiceExecutionApi.getNotes(jobId),
        homeServiceExecutionApi.listPartsRequests(jobId),
      ]);
      setJob(ctxRes.job as unknown as Record<string, unknown>);
      setTimeline(Array.isArray(tlRes) ? tlRes : []);
      setNotes(Array.isArray(notesRes) ? notesRes : []);
      setPartsRequests(partsRes.parts_requests ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveParts(partsRequestId: string) {
    setPartsActionLoading(partsRequestId);
    try {
      await homeServiceExecutionApi.approveParts(jobId, partsRequestId);
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to approve parts request");
    } finally {
      setPartsActionLoading(null);
    }
  }

  async function handleRejectParts(partsRequestId: string) {
    setPartsActionLoading(partsRequestId);
    try {
      await homeServiceExecutionApi.rejectParts(jobId, partsRequestId, "Rejected by business");
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to reject parts request");
    } finally {
      setPartsActionLoading(null);
    }
  }

  // Phase 2A — the install action existed in the API client but was never
  // wired to a button on this page; approve/reject worked but an approved
  // parts request had no way to be marked installed from here.
  async function handleInstallParts(partsRequestId: string) {
    setPartsActionLoading(partsRequestId);
    try {
      await homeServiceExecutionApi.installParts(jobId, partsRequestId);
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to mark parts request installed");
    } finally {
      setPartsActionLoading(null);
    }
  }

  useEffect(() => { loadJob(); }, [jobId]);

  // Phase 2A Slice 2B: reconstructs correct breadcrumb context for a direct
  // deep link to this job, using the real job number rather than the
  // generic "Jobs > Service Jobs" static registry entry. Falls back to null
  // (registry default) while the job is still loading, rather than showing
  // an empty or wrong entity name.
  const jobNumber = job ? String((job as { job_number?: string }).job_number ?? jobId.slice(0, 8)) : null;
  useBreadcrumbOverride(jobNumber ? [
    { label: "Jobs", href: "/service-jobs" },
    { label: `Service Job ${jobNumber}`, href: `/service-jobs/${jobId}` },
    { label: "Inspection and Quote" },
  ] : null);

  async function handleAction(action: string) {
    setActionLoading(true);
    try {
      if (action === "on_the_way")          await homeServiceExecutionApi.onTheWay(jobId);
      else if (action === "reached_site")   await homeServiceExecutionApi.reachedSite(jobId);
      else if (action === "start_inspection") await homeServiceExecutionApi.startInspection(jobId);
      else if (action === "complete_inspection") await homeServiceExecutionApi.completeInspection(jobId);
      else if (action === "start_service")  await homeServiceExecutionApi.startService(jobId);
      else if (action === "work_done")      await homeServiceExecutionApi.workDone(jobId);
      else if (action === "quote_required") { setShowQuoteModal(true); return; }
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitQuote() {
    if (!quoteNote.trim()) return;
    setActionLoading(true);
    try {
      await homeServiceExecutionApi.quoteRequired(jobId, quoteNote);
      setShowQuoteModal(false);
      setQuoteNote("");
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitCancel() {
    if (!cancelReason.trim()) return;
    setActionLoading(true);
    try {
      await homeServiceExecutionApi.cancel(jobId, cancelReason);
      setShowCancelModal(false);
      setCancelReason("");
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitNote() {
    if (!noteText.trim()) return;
    setNoteLoading(true);
    try {
      await homeServiceExecutionApi.addNote(jobId, noteText);
      setNoteText("");
      await loadJob();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setNoteLoading(false);
    }
  }

  const status = (job?.status as string) ?? "";
  const actions = STATUS_ACTIONS[status] ?? [];

  if (loading) return <div style={{ padding: 32 }}>Loading job execution...</div>;

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Job Execution</h1>
          <div style={{ color: "#6b7280", marginTop: 4 }}>
            Status: <strong>{status || "—"}</strong>
          </div>
        </div>
        <a href={`/service-jobs/${jobId}`} style={{ color: "#6366f1", textDecoration: "none", fontSize: 14 }}>
          ← Back to Job
        </a>
      </div>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 6, padding: 12, marginBottom: 16, color: "#dc2626" }}>
          {error}
        </div>
      )}

      {/* Status Action Bar */}
      {actions.length > 0 && (
        <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: 16, marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Next Action</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {actions.map((a) => (
              <button
                key={a.action}
                onClick={() => handleAction(a.action)}
                disabled={actionLoading}
                style={{
                  background: "#16a34a", color: "white", border: "none",
                  borderRadius: 6, padding: "8px 16px", cursor: "pointer", fontWeight: 600,
                }}
              >
                {a.label}
              </button>
            ))}
            <button
              onClick={() => setShowCancelModal(true)}
              disabled={actionLoading}
              style={{
                background: "white", color: "#dc2626", border: "1px solid #dc2626",
                borderRadius: 6, padding: "8px 16px", cursor: "pointer",
              }}
            >
              Cancel Job
            </button>
          </div>
        </div>
      )}

      {/* HS8B — Parts Requests (tenant/business approval) */}
      {partsRequests.length > 0 && (
        <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Parts Requests</div>
          {partsRequests.map((pr) => (
            <div key={pr.parts_request_id} style={{ borderBottom: "1px solid #f3f4f6", paddingBottom: 10, marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontWeight: 500, fontSize: 14 }}>{pr.part_name} × {pr.quantity}</div>
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
                  background: pr.status.includes("rejected") ? "#fef2f2" : pr.status === "installed" ? "#f0fdf4" : "#eff6ff",
                  color: pr.status.includes("rejected") ? "#dc2626" : pr.status === "installed" ? "#16a34a" : "#2563eb",
                }}>{pr.status}</span>
              </div>
              <div style={{ fontSize: 13, color: "#374151", marginTop: 2 }}>
                Estimated cost: ₹{pr.estimated_cost.toLocaleString("en-IN")} — {pr.reason}
              </div>
              {pr.status === "requested" && (
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button onClick={() => handleApproveParts(pr.parts_request_id)} disabled={partsActionLoading === pr.parts_request_id}
                    style={{ background: "#16a34a", color: "white", border: "none", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                    Approve
                  </button>
                  <button onClick={() => handleRejectParts(pr.parts_request_id)} disabled={partsActionLoading === pr.parts_request_id}
                    style={{ background: "white", color: "#dc2626", border: "1px solid #dc2626", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 12 }}>
                    Reject
                  </button>
                </div>
              )}
              {(pr.status === "business_approved" || pr.status === "customer_approved") && (
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button onClick={() => handleInstallParts(pr.parts_request_id)} disabled={partsActionLoading === pr.parts_request_id}
                    style={{ background: "#2563eb", color: "white", border: "none", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                    Mark Installed
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* HS8B — Completion Proof (view only, tenant does not complete jobs) */}
      {job?.completion_data != null && (
        <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: 16, marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Completion Proof</div>
          {(() => {
            const cd = job.completion_data as Record<string, unknown>;
            return (
              <>
                <div style={{ fontSize: 14, marginBottom: 6 }}>{String(cd.work_summary ?? "")}</div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>
                  Collected Amount: ₹{Number(cd.collected_amount ?? 0).toLocaleString("en-IN")}
                </div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
                  Payment Collected On-site — Customer Pays Provider Directly
                </div>
                {cd.technician_note ? (
                  <div style={{ fontSize: 12, color: "#374151", marginTop: 6 }}>Note: {String(cd.technician_note)}</div>
                ) : null}
              </>
            );
          })()}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Timeline */}
        <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Timeline</div>
          {timeline.length === 0 ? (
            <div style={{ color: "#9ca3af", fontSize: 14 }}>No events yet.</div>
          ) : (
            timeline.map((ev) => (
              <div key={ev.id} style={{ borderBottom: "1px solid #f3f4f6", paddingBottom: 10, marginBottom: 10 }}>
                <div style={{ fontWeight: 500, fontSize: 14 }}>{ev.event_type.replace(/_/g, " ")}</div>
                {ev.old_status && (
                  <div style={{ fontSize: 12, color: "#6b7280" }}>
                    {ev.old_status} → {ev.new_status}
                  </div>
                )}
                {ev.notes && <div style={{ fontSize: 12, color: "#374151", marginTop: 2 }}>{ev.notes}</div>}
                <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 2 }}>
                  {ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Notes */}
        <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Notes</div>
          {notes.length === 0 ? (
            <div style={{ color: "#9ca3af", fontSize: 14, marginBottom: 12 }}>No notes yet.</div>
          ) : (
            notes.map((n) => (
              <div key={n.id} style={{ borderBottom: "1px solid #f3f4f6", paddingBottom: 10, marginBottom: 10 }}>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{n.note_type}</div>
                <div style={{ fontSize: 14 }}>{n.note_text}</div>
                <div style={{ fontSize: 11, color: "#9ca3af" }}>
                  {n.created_at ? new Date(n.created_at).toLocaleString() : "—"}
                </div>
              </div>
            ))
          )}
          <div style={{ marginTop: 12 }}>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a note..."
              rows={3}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: 8, fontSize: 14, boxSizing: "border-box" }}
            />
            <button
              onClick={submitNote}
              disabled={noteLoading || !noteText.trim()}
              style={{
                background: "#6366f1", color: "white", border: "none",
                borderRadius: 6, padding: "8px 14px", cursor: "pointer",
                marginTop: 8, width: "100%",
              }}
            >
              {noteLoading ? "Saving..." : "Add Note"}
            </button>
          </div>
        </div>
      </div>

      {/* Quote Required Modal */}
      {showQuoteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "white", borderRadius: 8, padding: 24, width: 400, maxWidth: "90%" }}>
            <h3 style={{ margin: "0 0 12px" }}>Quote Required</h3>
            <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 12 }}>Describe what quote/parts are needed.</p>
            <textarea
              value={quoteNote}
              onChange={(e) => setQuoteNote(e.target.value)}
              rows={4}
              placeholder="Describe the quote requirements..."
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: 8, boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 10, marginTop: 12, justifyContent: "flex-end" }}>
              <button onClick={() => setShowQuoteModal(false)} style={{ padding: "8px 16px", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button onClick={submitQuote} disabled={!quoteNote.trim() || actionLoading} style={{ background: "#dc2626", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer" }}>
                Mark Quote Required
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "white", borderRadius: 8, padding: 24, width: 400, maxWidth: "90%" }}>
            <h3 style={{ margin: "0 0 12px" }}>Cancel Job</h3>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              rows={3}
              placeholder="Reason for cancellation..."
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: 8, boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 10, marginTop: 12, justifyContent: "flex-end" }}>
              <button onClick={() => setShowCancelModal(false)} style={{ padding: "8px 16px", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>Back</button>
              <button onClick={submitCancel} disabled={!cancelReason.trim() || actionLoading} style={{ background: "#dc2626", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer" }}>
                Cancel Job
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
