"use client";
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { StaffLayout } from "../../../../../components/layout/StaffLayout";
import { Card, Badge, Skeleton, Btn } from "../../../../../components/shared/ui";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { homeServiceStaffJobsApi, checklistExecutionApi, type ChecklistInstanceDetail } from "../../../../../lib/api";

// job.status -> the single next CTA a technician can take. Mirrors
// JOB_TRANSITIONS in app/engines/execution/constants.py — one primary
// action per status, not a free-for-all button list, so an invalid jump
// can never be attempted from this UI (the backend also rejects it with
// a 422 either way, per HS8/HS8B).
const ACTION_METHODS: Record<string, keyof typeof homeServiceStaffJobsApi> = {
  "accept": "accept",
  "call-customer": "customerContacted",
  "on-the-way": "onTheWay",
  "reached-site": "reachedSite",
  "start-inspection": "startInspection",
  "complete-inspection": "completeInspection",
  "start-service": "startService",
  "work-done": "markWorkDone",
};

export default function StaffHomeServiceJobDetailPage() {
  const params = useParams<{ job_id: string }>();
  const jobId = params.job_id;

  const job = useApi(useCallback(() => homeServiceStaffJobsApi.get(jobId), [jobId]), [jobId]);
  const parts = useApi(useCallback(() => homeServiceStaffJobsApi.listPartsRequests(jobId), [jobId]), [jobId]);
  const checklists = useApi(useCallback(() => checklistExecutionApi.listForJob(jobId), [jobId]), [jobId]);

  const statusAction = useAction(
    useCallback(async (fnName: keyof typeof homeServiceStaffJobsApi) => {
      const fn = homeServiceStaffJobsApi[fnName] as (id: string) => Promise<unknown>;
      return fn(jobId);
    }, [jobId]),
    { onSuccess: () => { job.refetch(); } },
  );

  const [rejectReason, setRejectReason] = useState("");
  const rejectAction = useAction(
    useCallback(
      () => homeServiceStaffJobsApi.reject(jobId, rejectReason.trim()),
      [jobId, rejectReason],
    ),
    { onSuccess: () => { setRejectReason(""); job.refetch(); } },
  );

  const [partsForm, setPartsForm] = useState({ part_name: "", quantity: "1", estimated_cost: "", reason: "" });
  const partsAction = useAction(
    useCallback(() => homeServiceStaffJobsApi.createPartsRequest(jobId, {
      part_name: partsForm.part_name, quantity: Number(partsForm.quantity),
      estimated_cost: Number(partsForm.estimated_cost), reason: partsForm.reason,
    }), [jobId, partsForm]),
    { onSuccess: () => { setPartsForm({ part_name: "", quantity: "1", estimated_cost: "", reason: "" }); parts.refetch(); job.refetch(); } },
  );

  const [completeForm, setCompleteForm] = useState({ work_summary: "", collected_amount: "", technician_note: "" });
  const completeAction = useAction(
    useCallback(() => homeServiceStaffJobsApi.complete(jobId, {
      work_summary: completeForm.work_summary,
      collected_amount: Number(completeForm.collected_amount),
      technician_note: completeForm.technician_note || undefined,
    }), [jobId, completeForm]),
    { onSuccess: () => { job.refetch(); } },
  );

  // MODULE-L5-38: GET /v1/staff/service-jobs/{id} returns {job, assignment,
  // booking}, not a flat job -- this page previously read job.data.status /
  // .job_number / etc. directly, which were all undefined at runtime (blank
  // job number, undefined status -> no action ever offered). The api client's
  // .get() type was corrected to HomeServiceJobDetail; derive the job from it.
  const j = job.data?.job;
  const requiredAction = j?.next_required_action;
  const nextMethod = requiredAction?.action_type
    ? ACTION_METHODS[requiredAction.action_type]
    : undefined;
  const nextAction = requiredAction?.allowed && nextMethod
    ? { label: requiredAction.action_label || "Continue Job", fn: nextMethod }
    : undefined;
  const canRequestParts = j && ["inspection_started", "inspection_done", "service_started", "quote_required"].includes(j.status);
  const canComplete = j?.status === "work_done";
  const isCompleted = j?.status === "completed";

  return (
    <StaffLayout activeNav="jobs">
      {job.loading ? <Skeleton height={300}/> : job.error ? (
        <Card><p style={{ color: "var(--danger-text)", fontSize: 13 }}>{job.error}{job.requestId && ` — Request ID: ${job.requestId}`}</p></Card>
      ) : j ? (
        <>
          <div style={{ marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{j.job_number}</h1>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>{j.city ?? "—"} {j.zipcode ?? ""}</p>
            </div>
            <Badge variant="info" size="sm">{j.status}</Badge>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card>
                <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Status Action</h3>
                {isCompleted ? (
                  <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Job completed. No further status actions available.</p>
                ) : nextAction ? (
                  <Btn variant="primary" loading={statusAction.loading} onClick={() => statusAction.execute(nextAction.fn)}>
                    {nextAction.label}
                  </Btn>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
                    {requiredAction?.blocked_message || j.start_work_block_message ||
                      (j.status === "quote_required"
                        ? "Waiting for the estimate, parts, or customer approval before work can continue."
                        : `No status action available from "${j.status}".`)}
                  </p>
                )}
                {statusAction.error && (
                  <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 8 }}>
                    {statusAction.error}{statusAction.requestId && ` — Request ID: ${statusAction.requestId}`}
                  </p>
                )}
                {j.status === "assigned" && (
                  <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                    <textarea
                      placeholder="Reason for rejecting this assignment"
                      value={rejectReason}
                      onChange={e => setRejectReason(e.target.value)}
                      style={{ ...inputStyle, minHeight: 54 }}
                    />
                    <Btn
                      variant="danger"
                      loading={rejectAction.loading}
                      disabled={!rejectReason.trim()}
                      onClick={() => rejectAction.execute()}
                    >
                      Reject Assignment
                    </Btn>
                    {rejectAction.error && (
                      <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                        {rejectAction.error}
                      </p>
                    )}
                  </div>
                )}
              </Card>

              {checklists.data && checklists.data.length > 0 && (
                <ChecklistCard instances={checklists.data} onRefetch={() => { checklists.refetch(); job.refetch(); }} />
              )}
              {['inspection_done', 'quote_required'].includes(j.status) && <CatalogAddons jobId={jobId} />}

              {canRequestParts && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Request Parts</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <input placeholder="Part name" value={partsForm.part_name}
                      onChange={e => setPartsForm(f => ({ ...f, part_name: e.target.value }))}
                      style={inputStyle}/>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input placeholder="Quantity" type="number" min={1} value={partsForm.quantity}
                        onChange={e => setPartsForm(f => ({ ...f, quantity: e.target.value }))}
                        style={{ ...inputStyle, flex: 1 }}/>
                      <input placeholder="Estimated cost (₹)" type="number" min={0} value={partsForm.estimated_cost}
                        onChange={e => setPartsForm(f => ({ ...f, estimated_cost: e.target.value }))}
                        style={{ ...inputStyle, flex: 1 }}/>
                    </div>
                    <textarea placeholder="Reason" value={partsForm.reason}
                      onChange={e => setPartsForm(f => ({ ...f, reason: e.target.value }))}
                      style={{ ...inputStyle, minHeight: 60 }}/>
                    <Btn variant="secondary" loading={partsAction.loading}
                      disabled={!partsForm.part_name || !partsForm.estimated_cost || !partsForm.reason}
                      onClick={() => partsAction.execute()}>
                      Submit Parts Request
                    </Btn>
                    {partsAction.error && (
                      <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                        {partsAction.error}{partsAction.requestId && ` — Request ID: ${partsAction.requestId}`}
                      </p>
                    )}
                  </div>
                </Card>
              )}

              {parts.data && parts.data.parts_requests.length > 0 && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Parts Requests</h3>
                  {parts.data.parts_requests.map(pr => (
                    <div key={pr.parts_request_id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{pr.part_name} × {pr.quantity}</span>
                        <Badge variant={pr.status.includes("rejected") ? "danger" : pr.status === "installed" ? "success" : "info"} size="sm">{pr.status}</Badge>
                      </div>
                      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>₹{pr.estimated_cost} — {pr.reason}</p>
                    </div>
                  ))}
                </Card>
              )}

              {canComplete && !isCompleted && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Complete Job</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <textarea placeholder="Work summary (required)" value={completeForm.work_summary}
                      onChange={e => setCompleteForm(f => ({ ...f, work_summary: e.target.value }))}
                      style={{ ...inputStyle, minHeight: 70 }}/>
                    <input placeholder="Collected amount (₹, required)" type="number" min={0} value={completeForm.collected_amount}
                      onChange={e => setCompleteForm(f => ({ ...f, collected_amount: e.target.value }))}
                      style={inputStyle}/>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Payment mode: Customer Pays Provider Directly (fixed)</div>
                    <textarea placeholder="Technician note (optional)" value={completeForm.technician_note}
                      onChange={e => setCompleteForm(f => ({ ...f, technician_note: e.target.value }))}
                      style={{ ...inputStyle, minHeight: 50 }}/>
                    <Btn variant="primary" loading={completeAction.loading}
                      disabled={!completeForm.work_summary || !completeForm.collected_amount}
                      onClick={() => completeAction.execute()}>
                      Submit Completion
                    </Btn>
                    {completeAction.error && (
                      <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                        {completeAction.error}{completeAction.requestId && ` — Request ID: ${completeAction.requestId}`}
                      </p>
                    )}
                  </div>
                </Card>
              )}

              {isCompleted && j.completion_data && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Completion Proof</h3>
                  <p style={{ fontSize: 13 }}>{String(j.completion_data.work_summary)}</p>
                  <p style={{ fontSize: 13, fontWeight: 700, marginTop: 8 }}>
                    Collected Amount: ₹{Number(j.completion_data.collected_amount).toLocaleString("en-IN")}
                  </p>
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    Payment Collected On-site — Customer Pays Provider Directly
                  </p>
                </Card>
              )}
            </div>

            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Job Info</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
                <Row label="Booking" value={j.booking_id}/>
                <Row label="Scheduled" value={j.scheduled_date ?? undefined}/>
                <Row label="Time Window" value={j.scheduled_time_window ?? undefined}/>
                <Row label="Assignment Status" value={j.assignment_status}/>
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </StaffLayout>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "8px 10px", borderRadius:"var(--radius-md)", fontSize: 13,
  border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)",
};

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div>{value || "—"}</div>
    </div>
  );
}

// ── Checklist execution (Checklist Catalog Engine) ───────────────────────
// Shows only the checklist instances the backend already resolved as
// applicable to this exact job + phase. This is a response/evidence
// capture surface for technicians -- not the reusable template editor
// (that lives in the platform-admin Checklist Library).
function CatalogAddons({ jobId }: { jobId: string }) {
  const data = useApi(useCallback(() => homeServiceStaffJobsApi.catalogAddons(jobId), [jobId]), [jobId]);
  const [mappingId, setMappingId] = useState("");
  const [quoteId, setQuoteId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [notice, setNotice] = useState("");
  const option = data.data?.options.find(o => o.mapping_id === mappingId);
  const add = useAction(useCallback(() => homeServiceStaffJobsApi.addCatalogAddon(jobId, { quote_id: quoteId, mapping_id: mappingId, quantity }), [jobId, quoteId, mappingId, quantity]),
    { onSuccess: () => { setNotice("Added to the estimate. It must follow the provider/customer approval flow before charging."); setMappingId(""); data.refetch(); } });
  return <Card padding="sm"><h3>Catalog add-ons</h3>
    <p>After inspection, add a platform-permitted extra to an editable estimate. Prices come from your provider's catalog.</p>
    {data.error && <p role="alert">{data.error}</p>}{add.error && <p role="alert">{add.error}</p>}{notice && <p role="status">{notice}</p>}
    {data.loading ? <p>Loading add-ons…</p> : !data.data?.options.length ? <p>No technician add-ons are configured for this job type.</p> : <>
      <select aria-label="Catalog add-on" value={mappingId} onChange={e => { setMappingId(e.target.value); setQuantity(data.data?.options.find(o => o.mapping_id === e.target.value)?.minimum_quantity ?? 1); }} style={inputStyle}>
        <option value="">Select add-on</option>{data.data.options.map(o => <option key={o.mapping_id} value={o.mapping_id}>{o.name}</option>)}
      </select>
      <input aria-label="Add-on quantity" type="number" min={option?.minimum_quantity ?? 1} max={option?.maximum_quantity ?? undefined} step={1} disabled={!option?.quantity_supported} value={quantity} onChange={e => setQuantity(Number(e.target.value))} style={inputStyle}/>
      <select aria-label="Editable estimate" value={quoteId} onChange={e => setQuoteId(e.target.value)} style={inputStyle}><option value="">Select estimate</option>{data.data.quotes.map(q => <option key={q.id} value={q.id}>{q.quote_number}</option>)}</select>
      {!data.data.quotes.length && <p>Ask your provider to prepare an editable estimate first. Approved estimates cannot be changed here.</p>}
      <Btn loading={add.loading} disabled={!mappingId || !quoteId || !Number.isInteger(quantity) || quantity < 1} onClick={() => add.execute()}>Add to estimate</Btn>
    </>}
  </Card>;
}

function ChecklistCard({ instances, onRefetch }: { instances: ChecklistInstanceDetail[]; onRefetch: () => void }) {
  return (
    <>
      {instances.map(instance => <ChecklistInstanceBlock key={instance.id} instance={instance} onRefetch={onRefetch} />)}
    </>
  );
}

function ChecklistInstanceBlock({ instance, onRefetch }: { instance: ChecklistInstanceDetail; onRefetch: () => void }) {
  const requiredItems = instance.items.filter(i => i.is_required);
  const requiredDone = requiredItems.filter(i => i.response && i.response.response_value != null).length;
  const complete = useAction(useCallback(() => checklistExecutionApi.complete(instance.id), [instance.id]), { onSuccess: onRefetch });

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Checklist — {instance.phase}</h3>
        <Badge size="sm" variant={instance.state === "COMPLETED" || instance.state === "WAIVED" ? "success" : instance.state === "BLOCKED" ? "danger" : "warning"}>
          {instance.state.replace(/_/g, " ")}
        </Badge>
      </div>
      {requiredItems.length > 0 && (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
          {requiredDone} of {requiredItems.length} required items complete
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {instance.items.map(item => (
          <ChecklistItemRow key={item.id} instanceId={instance.id} item={item} onSaved={onRefetch} />
        ))}
      </div>
      {instance.state !== "COMPLETED" && instance.state !== "WAIVED" && (
        <div style={{ marginTop: 14 }}>
          <Btn variant="primary" size="sm" loading={complete.loading} onClick={() => complete.execute()}>
            Complete Phase
          </Btn>
          {complete.error && (
            <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 6 }}>
              {complete.error}{complete.requestId && ` — Request ID: ${complete.requestId}`}
            </p>
          )}
        </div>
      )}
      {instance.completed_at && (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>
          Completed {new Date(instance.completed_at).toLocaleString()}
        </p>
      )}
    </Card>
  );
}

function ChecklistItemRow({ instanceId, item, onSaved }: {
  instanceId: string; item: ChecklistInstanceDetail["items"][number]; onSaved: () => void;
}) {
  const [value, setValue] = useState<string>(
    item.response?.response_value != null ? String(item.response.response_value) : "",
  );
  const save = useAction(
    useCallback(() => checklistExecutionApi.saveResponse(instanceId, item.id, { response_value: value }), [instanceId, item.id, value]),
    { onSuccess: onSaved },
  );
  const validationErrors = (item.response?.validation_result as { errors?: string[] } | null)?.errors;

  return (
    <div style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{item.label}</span>
        {item.is_required && <Badge size="sm" variant="warning">Required</Badge>}
        {item.evidence_required && <Badge size="sm" variant="muted">Evidence required</Badge>}
      </div>
      {item.help_text && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>{item.help_text}</p>}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {item.item_type === "YES_NO" ? (
          <select value={value} onChange={e => setValue(e.target.value)} style={inputStyle}>
            <option value="">— Select —</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        ) : item.item_type === "SINGLE_SELECT" && item.select_options ? (
          <select value={value} onChange={e => setValue(e.target.value)} style={inputStyle}>
            <option value="">— Select —</option>
            {item.select_options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ) : item.item_type === "NUMBER" || item.item_type === "MEASUREMENT" ? (
          <input type="number" value={value} onChange={e => setValue(e.target.value)}
            placeholder={item.measurement_unit ?? undefined} style={inputStyle} />
        ) : item.item_type === "LONG_TEXT" ? (
          <textarea value={value} onChange={e => setValue(e.target.value)} style={{ ...inputStyle, minHeight: 50, flex: 1 }} />
        ) : (
          <input type="text" value={value} onChange={e => setValue(e.target.value)} style={{ ...inputStyle, flex: 1 }} />
        )}
        <Btn size="xs" variant="secondary" loading={save.loading} disabled={!value} onClick={() => save.execute()}>
          Save
        </Btn>
      </div>
      {validationErrors && validationErrors.length > 0 && (
        <p style={{ fontSize: 11, color: "var(--danger-text)", marginTop: 4 }}>{validationErrors.join(", ")}</p>
      )}
      {save.error && <p style={{ fontSize: 11, color: "var(--danger-text)", marginTop: 4 }}>{save.error}</p>}
    </div>
  );
}
