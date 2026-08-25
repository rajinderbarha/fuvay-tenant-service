"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { homeServiceExecutionApi, ExecutionEventRecord, ExecutionNoteRecord, PartsRequestRecord, serviceJobAssignmentApi, inventoryApi, type InventoryItem, type StockLocation } from "../../../../../lib/api";
import { PageShell, PageHeader, Card, Button, Modal, Alert, StatusBadge } from "@serviceos/design-system";

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
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [stockLocations, setStockLocations] = useState<StockLocation[]>([]);
  const [approveRequest, setApproveRequest] = useState<PartsRequestRecord | null>(null);
  const [procurementSource, setProcurementSource] = useState<"inventory" | "external">("inventory");
  const [allocationItemId, setAllocationItemId] = useState("");
  const [allocationLocationId, setAllocationLocationId] = useState("");
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
      const [ctxRes, tlRes, notesRes, partsRes, inventoryRes, locationsRes] = await Promise.all([
        serviceJobAssignmentApi.getContext(jobId),
        homeServiceExecutionApi.getProviderTimeline(jobId),
        homeServiceExecutionApi.getNotes(jobId),
        homeServiceExecutionApi.listPartsRequests(jobId),
        inventoryApi.listItems({ limit: 200, stockStatus: "all", sort: "name_asc" })
          .catch(() => ({ items: [], total: 0, offset: 0, limit: 200, has_next: false })),
        inventoryApi.listLocations().catch(() => ({ locations: [], total: 0 })),
      ]);
      setJob(ctxRes.job as unknown as Record<string, unknown>);
      setTimeline(Array.isArray(tlRes) ? tlRes : []);
      setNotes(Array.isArray(notesRes) ? notesRes : []);
      setPartsRequests(partsRes.parts_requests ?? []);
      setInventoryItems(inventoryRes.items ?? []);
      setStockLocations(locationsRes.locations ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  function openApproveParts(pr: PartsRequestRecord) {
    const exact = inventoryItems.find(item => item.name.toLowerCase() === pr.part_name.toLowerCase());
    setApproveRequest(pr);
    setProcurementSource(inventoryItems.length && stockLocations.length ? "inventory" : "external");
    setAllocationItemId(exact?.item_id ?? inventoryItems[0]?.item_id ?? "");
    setAllocationLocationId(stockLocations[0]?.location_id ?? "");
  }

  async function handleApproveParts() {
    if (!approveRequest) return;
    if (procurementSource === "inventory" && (!allocationItemId || !allocationLocationId)) {
      setError("Select an inventory item and stock location, or choose external procurement.");
      return;
    }
    setPartsActionLoading(approveRequest.parts_request_id);
    try {
      await homeServiceExecutionApi.approveParts(jobId, approveRequest.parts_request_id, {
        procurement_source: procurementSource,
        ...(procurementSource === "inventory" ? {
          inventory_item_id: allocationItemId, stock_location_id: allocationLocationId,
        } : {}),
      });
      setApproveRequest(null);
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

  useEffect(() => { loadJob(); }, [jobId]);

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

  if (loading) {
    return (
      <PageShell>
        <div style={{ padding: 32 }}>Loading job execution...</div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title="Job Execution"
        description={`Status: ${status || "—"}`}
        actions={<Link href={`/service-jobs/${jobId}`} style={{ color: "var(--brand)", textDecoration: "none", fontSize: 14 }}>← Back to Job</Link>}
      />

      {error && <div style={{ marginBottom: 16 }}><Alert tone="danger">{error}</Alert></div>}

      {/* Status Action Bar */}
      {actions.length > 0 && (
        <Card padding="md" style={{ marginBottom: 20, background: "var(--success-bg)", borderColor: "var(--success-border)" }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Next Action</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {actions.map((a) => (
              <Button key={a.action} variant="primary" disabled={actionLoading} onClick={() => handleAction(a.action)}>
                {a.label}
              </Button>
            ))}
            <Button variant="destructive" disabled={actionLoading} onClick={() => setShowCancelModal(true)}>
              Cancel Job
            </Button>
          </div>
        </Card>
      )}

      {/* HS8B — Parts Requests (tenant/business approval) */}
      {partsRequests.length > 0 && (
        <Card padding="md" style={{ marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Parts Requests</div>
          {partsRequests.map((pr) => (
            <div key={pr.parts_request_id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 10, marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontWeight: 500, fontSize: 14 }}>{pr.part_name} × {pr.quantity}</div>
                <StatusBadge status={pr.status} size="sm" />
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                Estimated cost: ₹{pr.estimated_cost.toLocaleString("en-IN")} — {pr.reason}
              </div>
              {pr.status === "requested" && (
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <Button size="sm" variant="primary" disabled={partsActionLoading === pr.parts_request_id}
                    onClick={() => openApproveParts(pr)}>
                    Approve
                  </Button>
                  <Button size="sm" variant="destructive" disabled={partsActionLoading === pr.parts_request_id}
                    onClick={() => handleRejectParts(pr.parts_request_id)}>
                    Reject
                  </Button>
                </div>
              )}
              {pr.status !== "requested" && (
                <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 6 }}>
                  Fulfilment: {pr.procurement_source === "inventory" ? "Provider inventory" : "External purchase"}
                  {pr.stock_reservation_id ? " · stock reserved" : ""}
                </div>
              )}
            </div>
          ))}
        </Card>
      )}

      {/* HS8B — Completion Proof (view only, tenant does not complete jobs) */}
      {job?.completion_data != null && (
        <Card padding="md" style={{ marginBottom: 20, background: "var(--success-bg)", borderColor: "var(--success-border)" }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Completion Proof</div>
          {(() => {
            const cd = job.completion_data as Record<string, unknown>;
            return (
              <>
                <div style={{ fontSize: 14, marginBottom: 6 }}>{String(cd.work_summary ?? "")}</div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>
                  Collected Amount: ₹{Number(cd.collected_amount ?? 0).toLocaleString("en-IN")}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                  Payment Collected On-site — Customer Pays Provider Directly
                </div>
                {cd.technician_note ? (
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>Note: {String(cd.technician_note)}</div>
                ) : null}
              </>
            );
          })()}
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Timeline */}
        <Card padding="md">
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Timeline</div>
          {timeline.length === 0 ? (
            <div style={{ color: "var(--text-tertiary)", fontSize: 14 }}>No events yet.</div>
          ) : (
            timeline.map((ev) => (
              <div key={ev.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 10, marginBottom: 10 }}>
                <div style={{ fontWeight: 500, fontSize: 14 }}>{ev.event_type.replace(/_/g, " ")}</div>
                {ev.old_status && (
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    {ev.old_status} → {ev.new_status}
                  </div>
                )}
                {ev.notes && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{ev.notes}</div>}
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                  {ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}
                </div>
              </div>
            ))
          )}
        </Card>

        {/* Notes */}
        <Card padding="md">
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Notes</div>
          {notes.length === 0 ? (
            <div style={{ color: "var(--text-tertiary)", fontSize: 14, marginBottom: 12 }}>No notes yet.</div>
          ) : (
            notes.map((n) => (
              <div key={n.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 10, marginBottom: 10 }}>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{n.note_type}</div>
                <div style={{ fontSize: 14 }}>{n.note_text}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
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
              style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 6, padding: 8, fontSize: 14,
                boxSizing: "border-box", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" }}
            />
            <Button variant="primary" style={{ marginTop: 8, width: "100%" }}
              disabled={noteLoading || !noteText.trim()} loading={noteLoading} onClick={submitNote}>
              Add Note
            </Button>
          </div>
        </Card>
      </div>

      <Modal open={!!approveRequest} onClose={() => setApproveRequest(null)} title="Approve parts request"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setApproveRequest(null)}>Cancel</Button>
          <Button variant="primary" size="sm" loading={partsActionLoading === approveRequest?.parts_request_id}
            disabled={procurementSource === "inventory" && (!allocationItemId || !allocationLocationId)}
            onClick={handleApproveParts}>Approve request</Button>
        </>}>
        {approveRequest && <div style={{ display: "grid", gap: 14, minWidth: "min(420px, 75vw)" }}>
          <div style={{ padding: 12, borderRadius: 8, background: "var(--surface-sunken)", fontSize: 13 }}>
            <strong>{approveRequest.part_name} × {approveRequest.quantity}</strong>
            <div style={{ marginTop: 3, color: "var(--text-secondary)" }}>{approveRequest.reason}</div>
          </div>
          <label style={{ display: "grid", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
            Fulfilment source
            <select value={procurementSource} onChange={e => setProcurementSource(e.target.value as "inventory" | "external")}
              style={{ height: 38, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px" }}>
              <option value="inventory">Provider inventory (reserve stock)</option>
              <option value="external">External purchase (no stock movement)</option>
            </select>
          </label>
          {procurementSource === "inventory" && <>
            <label style={{ display: "grid", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
              Inventory item
              <select value={allocationItemId} onChange={e => setAllocationItemId(e.target.value)}
                style={{ height: 38, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px" }}>
                <option value="">Select item</option>
                {inventoryItems.map(item => <option key={item.item_id} value={item.item_id} disabled={item.available_qty < approveRequest.quantity}>
                  {item.name} · {item.available_qty} available · ₹{item.selling_price.toLocaleString("en-IN")}
                </option>)}
              </select>
            </label>
            <label style={{ display: "grid", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
              Stock location
              <select value={allocationLocationId} onChange={e => setAllocationLocationId(e.target.value)}
                style={{ height: 38, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px" }}>
                <option value="">Select location</option>
                {stockLocations.map(location => <option key={location.location_id} value={location.location_id}>{location.location_name}</option>)}
              </select>
            </label>
            <div style={{ padding: 10, borderRadius: 8, background: "var(--info-bg)", color: "var(--info-text)", fontSize: 12 }}>
              Customer pricing comes from the inventory catalogue. Stock is reserved after the final required approval and deducted only when installed.
            </div>
          </>}
        </div>}
      </Modal>

      {/* Quote Required Modal */}
      <Modal open={showQuoteModal} onClose={() => setShowQuoteModal(false)} title="Quote Required"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setShowQuoteModal(false)}>Cancel</Button>
          <Button variant="destructive" size="sm" disabled={!quoteNote.trim() || actionLoading}
            loading={actionLoading} onClick={submitQuote}>
            Mark Quote Required
          </Button>
        </>}>
        <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 12 }}>Describe what quote/parts are needed.</p>
        <textarea
          value={quoteNote}
          onChange={(e) => setQuoteNote(e.target.value)}
          rows={4}
          placeholder="Describe the quote requirements..."
          style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 6, padding: 8,
            boxSizing: "border-box", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" }}
        />
      </Modal>

      {/* Cancel Modal */}
      <Modal open={showCancelModal} onClose={() => setShowCancelModal(false)} title="Cancel Job"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setShowCancelModal(false)}>Back</Button>
          <Button variant="destructive" size="sm" disabled={!cancelReason.trim() || actionLoading}
            loading={actionLoading} onClick={submitCancel}>
            Cancel Job
          </Button>
        </>}>
        <textarea
          value={cancelReason}
          onChange={(e) => setCancelReason(e.target.value)}
          rows={3}
          placeholder="Reason for cancellation..."
          style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 6, padding: 8,
            boxSizing: "border-box", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" }}
        />
      </Modal>
    </PageShell>
  );
}
