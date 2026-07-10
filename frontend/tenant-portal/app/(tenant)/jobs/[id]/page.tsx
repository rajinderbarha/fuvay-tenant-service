"use client";
/**
 * Job Detail — full 360° view of a single job with job_type-aware UI.
 * Repair:       shows assessment + quote flow
 * Service:      shows checklist only (no quote section)
 * Consultation: shows assessment + quote + spawn-repair button
 */
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, JobStatusBadge, Btn, Modal, Input, Skeleton } from "../../../../components/shared/ui";
import { jobsApi, quotesApi, mediaAssetApi, type MediaAsset } from "../../../../lib/api";
import type { JobQuotePart, JobChecklistItem } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { MediaUploader } from "../../../../components/media/MediaUploader";
import { MediaGallery } from "../../../../components/media/MediaGallery";

const JOB_TYPE_LABEL: Record<string, string> = {
  repair: "Repair", service: "Service", consultation: "Consultation",
};
const JOB_TYPE_COLOR: Record<string, string> = {
  repair: "var(--warning-text)", service: "var(--success-text)", consultation: "var(--info-text)",
};
const ASSESSMENT_STATUSES = new Set([
  "assessment_started", "assessment_complete", "quote_pending",
  "quote_approved", "quote_rejected",
]);

export default function JobDetailPage({ params }:{ params: Promise<{ id:string }> }) {
  const { id } = React.use(params);
  const job     = useApi(useCallback(() => jobsApi.get(id),         [id]));
  const history = useApi(useCallback(() => jobsApi.history(id),     [id]));
  const quotes  = useApi(useCallback(() => quotesApi.listByJob(id), [id]));

  const updateAction    = useAction(useCallback(
    (status:string, notes:string) => jobsApi.updateStatus(id, status, notes), [id]));
  const closeAction     = useAction(useCallback(
    (finalPrice:string) => jobsApi.close(id, finalPrice), [id]));
  const quoteAction     = useAction(useCallback(
    (amount:number, parts:JobQuotePart[], labour:number|undefined, notes:string|undefined, expiryDays:number) =>
      quotesApi.create(id, amount, parts, labour, notes, expiryDays), [id]));
  const checklistAction = useAction(useCallback(
    (items:JobChecklistItem[]) => jobsApi.updateChecklist(id, items), [id]));
  const findingsAction  = useAction(useCallback(
    (findings:string, rec:string) => quotesApi.submitFindings(id, findings, rec || undefined), [id]));
  const spawnAction     = useAction(useCallback(
    () => jobsApi.spawnRepair(id), [id]));

  const [statusModal, setStatusModal]   = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [statusNotes,  setStatusNotes]  = useState("");
  const [closeModal,   setCloseModal]   = useState(false);
  const [finalPrice,   setFinalPrice]   = useState("");

  const [quoteModal,      setQuoteModal]      = useState(false);
  const [quoteParts,      setQuoteParts]      = useState<JobQuotePart[]>([{ name:"", cost:0 }]);
  const [labourEstimate,  setLabourEstimate]  = useState("");
  const [quoteNotes,      setQuoteNotes]      = useState("");
  const [expiryDays,      setExpiryDays]      = useState("7");

  const [findingsModal,    setFindingsModal]   = useState(false);
  const [findingsText,     setFindingsText]    = useState("");
  const [recommendText,    setRecommendText]   = useState("");

  const [beforePhotos, setBeforePhotos] = useState<MediaAsset[]>([]);
  const [afterPhotos,  setAfterPhotos]  = useState<MediaAsset[]>([]);
  const [photosLoaded, setPhotosLoaded] = useState(false);

  const loadPhotos = useCallback(async () => {
    if (!id) return;
    const [before, after] = await Promise.all([
      mediaAssetApi.listAssets({ media_context: "job_before_photo", owner_type: "job", owner_id: id }),
      mediaAssetApi.listAssets({ media_context: "job_after_photo",  owner_type: "job", owner_id: id }),
    ]).catch(() => [null, null]);
    if (before) setBeforePhotos(before.items);
    if (after)  setAfterPhotos(after.items);
    setPhotosLoaded(true);
  }, [id]);

  React.useEffect(() => { loadPhotos(); }, [loadPhotos]);

  const partsTotal = quoteParts.reduce((sum, p) => sum + (Number(p.cost) || 0), 0);
  const quoteTotal  = partsTotal + (Number(labourEstimate) || 0);

  const j   = job.data;
  const fmt = (n:number) => `₹${n.toLocaleString("en-IN")}`;

  // Use server-resolved allowed transitions (job_type-aware — no frontend copy of the graph)
  const allowedTransitions: string[] = j?.allowed_transitions ?? [];

  const isRepair       = j?.job_type === "repair";
  const isService      = j?.job_type === "service";
  const isConsultation = j?.job_type === "consultation";
  const showQuoteSection  = isRepair || isConsultation;
  const showAssessment    = (isRepair || isConsultation) && (j ? ASSESSMENT_STATUSES.has(j.status) : false);
  const showSpawnRepair   = isConsultation && j ? ["assessment_complete","quote_pending","quote_approved","quote_rejected","pending_sign_off"].includes(j.status) : false;

  async function handleStatusUpdate() {
    const res = await updateAction.execute(targetStatus, statusNotes);
    if (res) { job.refetch(); history.refetch(); setStatusModal(false); setStatusNotes(""); }
  }

  async function handleClose() {
    const res = await closeAction.execute(finalPrice || "0");
    if (res) { job.refetch(); history.refetch(); setCloseModal(false); setFinalPrice(""); }
  }

  async function handleSendQuote() {
    const validParts = quoteParts.filter(p => p.name.trim() && p.cost > 0);
    const labour = labourEstimate ? Number(labourEstimate) : undefined;
    const res = await quoteAction.execute(quoteTotal, validParts, labour, quoteNotes || undefined, Number(expiryDays) || 7);
    if (res) {
      quotes.refetch(); job.refetch();
      setQuoteModal(false); setQuoteParts([{ name:"", cost:0 }]);
      setLabourEstimate(""); setQuoteNotes(""); setExpiryDays("7");
    }
  }

  async function handleSubmitFindings() {
    const res = await findingsAction.execute(findingsText, recommendText);
    if (res) { job.refetch(); setFindingsModal(false); setFindingsText(""); setRecommendText(""); }
  }

  async function handleSpawnRepair() {
    const res = await spawnAction.execute();
    if (res) { job.refetch(); }
  }

  function updatePart(index:number, field:"name"|"cost", value:string) {
    setQuoteParts(prev => prev.map((p,i) => i===index ? { ...p, [field]: field==="cost" ? Number(value)||0 : value } : p));
  }

  async function toggleChecklistItem(index:number) {
    if (!j?.checklist) return;
    const updated = j.checklist.map((it, i) => i===index ? { ...it, completed: !it.completed } : it);
    const res = await checklistAction.execute(updated);
    if (res) job.refetch();
  }

  return (
    <TenantLayout activeNav="jobs">
      {/* Breadcrumb */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <a href="/jobs" style={{ color:"var(--text-link)", textDecoration:"none" }}>Jobs</a>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {job.loading ? "Loading..." : j?.job_number}
        </span>
      </div>

      {job.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Skeleton height={140} style={{ borderRadius:14 }}/>
          <Skeleton height={200} style={{ borderRadius:14 }}/>
        </div>
      ) : !j ? (
        <div style={{ textAlign:"center", padding:60 }}>
          <p style={{ color:"var(--text-tertiary)" }}>Job not found</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {/* Hero */}
          <Card padding={24}>
            <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", flexWrap:"wrap", gap:16 }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                  <h1 style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                    {j.job_number}
                  </h1>
                  <JobStatusBadge status={j.status}/>
                  {/* Job type badge — key differentiator */}
                  <span style={{
                    fontSize:11, fontWeight:600, padding:"2px 8px", borderRadius:20,
                    background:"var(--surface-sunken)", color: JOB_TYPE_COLOR[j.job_type] ?? "var(--text-secondary)",
                    textTransform:"uppercase", letterSpacing:"0.06em",
                  }}>
                    {JOB_TYPE_LABEL[j.job_type] ?? j.job_type}
                  </span>
                </div>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                  {j.service_type_id} · {j.service_category}
                </p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                  Created {new Date(j.created_at).toLocaleString("en-IN")}
                  {j.parent_job_id && (
                    <span style={{ marginLeft:8, color:"var(--info-text)" }}>
                      (spawned from consultation)
                    </span>
                  )}
                </p>
              </div>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                {allowedTransitions.filter(s => !["invoice_generated","closed"].includes(s)).slice(0,4).map(st => (
                  <Btn key={st} variant={st==="cancelled"||st==="voided"?"danger":st==="work_complete"||st==="quality_passed"?"success":"secondary"}
                    size="sm" onClick={() => { setTargetStatus(st); setStatusModal(true); }}>
                    → {st.replace(/_/g," ")}
                  </Btn>
                ))}
                {allowedTransitions.includes("closed") && (
                  <Btn variant="success" size="sm" onClick={() => setCloseModal(true)}>
                    Close Job ✓
                  </Btn>
                )}
                {showSpawnRepair && (
                  <Btn variant="secondary" size="sm" loading={spawnAction.loading}
                    onClick={handleSpawnRepair}>
                    Spawn Repair →
                  </Btn>
                )}
              </div>
            </div>
          </Card>

          {/* Details grid */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Card padding={20}>
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Customer</h3>
              {[
                { label:"Name",    v: j.customer_name    ?? "—" },
                { label:"Phone",   v: j.customer_phone   ?? "—" },
                { label:"Address", v: j.customer_address ?? "—" },
              ].map(r => (
                <div key={r.label} style={{ display:"flex", gap:12, padding:"7px 0",
                  borderBottom:"1px solid var(--border)" }}>
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", width:70, flexShrink:0 }}>{r.label}</span>
                  <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                </div>
              ))}
              <div style={{ marginTop:12 }}>
                <Btn variant="ghost" size="sm"
                  onClick={() => window.location.href="/chat"}>Open Chat →</Btn>
              </div>
            </Card>

            <Card padding={20}>
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Job Info</h3>
              {[
                { label:"Staff",      v: j.assigned_staff ?? "Unassigned" },
                { label:"Value",      v: j.job_value != null ? fmt(j.job_value) : j.quoted_price != null ? fmt(j.quoted_price) : "—" },
                { label:"Duration",   v: j.duration_estimate_minutes != null ? `${j.duration_estimate_minutes} min` : "—" },
                { label:"Notes",      v: j.notes ?? "—" },
              ].map(r => (
                <div key={r.label} style={{ display:"flex", gap:12, padding:"7px 0",
                  borderBottom:"1px solid var(--border)" }}>
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", width:70, flexShrink:0 }}>{r.label}</span>
                  <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                </div>
              ))}
            </Card>
          </div>

          {/* Payment Collection — technician collects payable_to_provider directly,
              ServiceOS never collects the service payment for Home Services. */}
          {j.quoted_price != null && (
            <Card padding={20}>
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Payment Collection</h3>
              {[
                { label:"Service Price",             v: fmt(j.quoted_price) },
                { label:"ServiceOS Credit Applied",   v: fmt(j.customer_credit_applied ?? 0) },
                { label:"Payable To Provider",        v: fmt(j.payable_to_provider ?? j.quoted_price) },
                { label:"Payment Mode",               v: "Customer pays provider directly" },
                { label:"Amount Collected",           v: j.amount_collected != null ? fmt(j.amount_collected) : "Not yet recorded" },
                { label:"Payment Recorded",           v: j.payment_recorded ? "Yes" : "No" },
              ].map(r => (
                <div key={r.label} style={{ display:"flex", gap:12, padding:"7px 0",
                  borderBottom:"1px solid var(--border)" }}>
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", width:180, flexShrink:0 }}>{r.label}</span>
                  <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                </div>
              ))}
            </Card>
          )}

          {/* Usage Credit Deduction — appears once the job financially closes. */}
          {j.commission_amount != null && (
            <Card padding={20}>
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Usage Credit Deduction</h3>
              <div style={{ display:"flex", gap:12, padding:"7px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ fontSize:12, color:"var(--text-tertiary)", width:180, flexShrink:0 }}>Completed Job Deduction</span>
                <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{fmt(j.commission_amount)}</span>
              </div>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"10px 0 0" }}>
                Provider usage credits are not real money and are not withdrawable.
              </p>
            </Card>
          )}

          {/* Assessment / Findings — Repair + Consultation only */}
          {showAssessment && (
            <Card padding={20}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
                <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:0,
                  textTransform:"uppercase", letterSpacing:"0.06em" }}>
                  {isConsultation ? "Assessment & Report" : "Findings & Diagnosis"}
                </h3>
                <Btn variant="secondary" size="sm" onClick={() => {
                  setFindingsText(j.findings ?? "");
                  setRecommendText(j.recommendation ?? "");
                  setFindingsModal(true);
                }}>
                  {j.findings ? "Edit Findings" : "Add Findings"}
                </Btn>
              </div>
              {j.findings ? (
                <div>
                  <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 4px", fontWeight:600 }}>Findings</p>
                  <p style={{ fontSize:13, color:"var(--text-primary)", margin:"0 0 12px", whiteSpace:"pre-wrap" }}>{j.findings}</p>
                  {j.recommendation && (
                    <>
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 4px", fontWeight:600 }}>Recommendation</p>
                      <p style={{ fontSize:13, color:"var(--text-primary)", margin:0, whiteSpace:"pre-wrap" }}>{j.recommendation}</p>
                    </>
                  )}
                </div>
              ) : (
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                  No findings recorded yet. Add your assessment notes before sending a quote.
                </p>
              )}
            </Card>
          )}

          {/* Checklist — Service jobs + any job with a checklist */}
          {j.checklist && j.checklist.length > 0 && (
            <Card padding={20}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
                <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:0,
                  textTransform:"uppercase", letterSpacing:"0.06em" }}>
                  {isService ? "Service Checklist" : "Checklist"}
                </h3>
                <Badge variant={j.checklist.every(it => it.completed) ? "success" : "warning"}>
                  {j.checklist.filter(it => it.completed).length} / {j.checklist.length} done
                </Badge>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {j.checklist.map((item, i) => (
                  <label key={i} style={{ display:"flex", alignItems:"center", gap:10, padding:"8px 10px",
                    borderRadius:8, background: item.completed ? "var(--success-bg)" : "var(--surface-sunken)",
                    cursor: checklistAction.loading ? "wait" : "pointer" }}>
                    <input type="checkbox" checked={item.completed} disabled={checklistAction.loading}
                      onChange={() => toggleChecklistItem(i)}
                      style={{ width:16, height:16, cursor:"pointer" }}/>
                    <span style={{ fontSize:13, color: item.completed ? "var(--success-text)" : "var(--text-primary)",
                      textDecoration: item.completed ? "line-through" : "none" }}>
                      {item.step}
                    </span>
                  </label>
                ))}
              </div>
              {isService && !j.checklist.every(it => it.completed) && (
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"10px 0 0" }}>
                  Complete all steps before moving to sign-off.
                </p>
              )}
            </Card>
          )}

          {/* Quotes — Repair + Consultation only (Service has fixed price, no quote needed) */}
          {showQuoteSection && (
            <Card padding={20}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
                <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:0,
                  textTransform:"uppercase", letterSpacing:"0.06em" }}>
                  {isConsultation ? "Consultation Report & Quote" : "Quotes"}
                </h3>
                {allowedTransitions.includes("quote_pending") && (
                  <Btn variant="secondary" size="sm" onClick={() => setQuoteModal(true)}>
                    {isConsultation ? "Send Report + Quote" : "Send Quote"}
                  </Btn>
                )}
              </div>
              {quotes.loading ? (
                <Skeleton height={60} style={{ borderRadius:10 }}/>
              ) : !quotes.data?.quotes.length ? (
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                  {allowedTransitions.includes("quote_pending")
                    ? "No quotes sent yet. Complete assessment first, then send a quote."
                    : "No quotes for this job."}
                </p>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {quotes.data.quotes.map(q => (
                    <div key={q.quote_id} style={{ padding:"12px 14px", borderRadius:10,
                      border:"1px solid var(--border)", background:"var(--surface-sunken)" }}>
                      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:6 }}>
                        <span style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)" }}>{fmt(q.amount)}</span>
                        <Badge variant={
                          q.status==="approved" ? "success" : q.status==="rejected" ? "danger" :
                          q.is_expired || q.status==="expired" ? "muted" : "warning"
                        }>{q.is_expired && q.status==="pending" ? "expired" : q.status}</Badge>
                      </div>
                      {q.parts.length > 0 && (
                        <p style={{ fontSize:11, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                          Parts: {q.parts.map(p => `${p.name} (₹${p.cost})`).join(", ")}
                        </p>
                      )}
                      {q.labour_estimate != null && (
                        <p style={{ fontSize:11, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                          Labour: {fmt(q.labour_estimate)}
                        </p>
                      )}
                      {q.notes && <p style={{ fontSize:11, color:"var(--text-secondary)", margin:"0 0 4px" }}>{q.notes}</p>}
                      {q.expires_at && (
                        <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                          Expires {new Date(q.expires_at).toLocaleDateString("en-IN")}
                        </p>
                      )}
                      {/* After rejection: show option to re-send revised quote */}
                      {q.status === "rejected" && allowedTransitions.includes("assessment_complete") && (
                        <div style={{ marginTop:8, padding:"6px 10px", borderRadius:6,
                          background:"var(--warning-bg)", border:"1px solid var(--warning-border)" }}>
                          <p style={{ fontSize:11, color:"var(--warning-text)", margin:"0 0 4px" }}>
                            Customer rejected this quote. You can re-assess and send a revised quote.
                          </p>
                          <Btn variant="secondary" size="sm" onClick={() => {
                            updateAction.execute("assessment_complete", "Re-assessing after quote rejection").then(r => {
                              if (r) { job.refetch(); history.refetch(); }
                            });
                          }}>Re-assess → Send Revised Quote</Btn>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Job Photos — Before & After */}
          <Card padding={20}>
            <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 16px",
              textTransform:"uppercase", letterSpacing:"0.06em" }}>Job Photos</h3>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
              <div>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 10px" }}>
                  Before Photos
                </p>
                {photosLoaded ? (
                  <>
                    <MediaGallery
                      assets={beforePhotos}
                      canDelete
                      columns={2}
                      emptyMessage="No before photos yet."
                      onDeleted={id => setBeforePhotos(p => p.filter(a => a.id !== id))}
                    />
                    <div style={{ marginTop:10 }}>
                      <MediaUploader
                        mediaContext="job_before_photo"
                        ownerType="job"
                        ownerId={id}
                        accept="image/*"
                        maxSizeMB={10}
                        label="Upload before photo"
                        hint="Photo taken before work begins"
                        onUploaded={asset => setBeforePhotos(p => [...p, asset])}
                        canDelete={false}
                      />
                    </div>
                  </>
                ) : (
                  <Skeleton height={80} style={{ borderRadius:8 }}/>
                )}
              </div>
              <div>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 10px" }}>
                  After Photos
                </p>
                {photosLoaded ? (
                  <>
                    <MediaGallery
                      assets={afterPhotos}
                      canDelete
                      columns={2}
                      emptyMessage="No after photos yet."
                      onDeleted={id => setAfterPhotos(p => p.filter(a => a.id !== id))}
                    />
                    <div style={{ marginTop:10 }}>
                      <MediaUploader
                        mediaContext="job_after_photo"
                        ownerType="job"
                        ownerId={id}
                        accept="image/*"
                        maxSizeMB={10}
                        label="Upload after photo"
                        hint="Photo taken after work is complete"
                        onUploaded={asset => setAfterPhotos(p => [...p, asset])}
                        canDelete={false}
                      />
                    </div>
                  </>
                ) : (
                  <Skeleton height={80} style={{ borderRadius:8 }}/>
                )}
              </div>
            </div>
          </Card>

          {/* Status timeline */}
          <Card padding={20}>
            <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 16px",
              textTransform:"uppercase", letterSpacing:"0.06em" }}>Status Timeline</h3>
            {history.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(4)].map((_,i) => <Skeleton key={i} height={32}/>)}
              </div>
            ) : (history.data?.history ?? []).map((h, i) => (
              <div key={i} style={{ display:"flex", alignItems:"center", gap:14, padding:"10px 0",
                borderBottom:i<(history.data?.history.length??0)-1?"1px solid var(--border)":"none" }}>
                <div style={{ width:8, height:8, borderRadius:"50%", background:"var(--accent)",
                  flexShrink:0, marginTop:2 }}/>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                    <JobStatusBadge status={h.status}/>
                    {h.notes && <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{h.notes}</span>}
                  </div>
                </div>
                <span style={{ fontSize:11, color:"var(--text-tertiary)", flexShrink:0 }}>
                  {new Date(h.changed_at).toLocaleString("en-IN",{hour:"2-digit",minute:"2-digit",day:"numeric",month:"short"})}
                </span>
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* Update status modal */}
      <Modal open={statusModal} onClose={() => setStatusModal(false)}
        title={`Move to: ${targetStatus.replace(/_/g," ")}`}>
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {updateAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{updateAction.error}</p>
            </div>
          )}
          <Input label="Notes (optional)" placeholder="Reason for status change..."
            value={statusNotes} onChange={setStatusNotes} rows={3}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setStatusModal(false)}>Cancel</Btn>
            <Btn variant={targetStatus==="cancelled"||targetStatus==="voided"?"danger":"primary"} size="sm"
              loading={updateAction.loading} onClick={handleStatusUpdate}>
              Confirm
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Close job modal */}
      <Modal open={closeModal} onClose={() => setCloseModal(false)} title="Close Job">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--info-bg)",
            border:"1px solid var(--info-border)" }}>
            <p style={{ fontSize:12, color:"var(--info-text)", margin:0 }}>
              Closing this job will apply a Completed Job Deduction to your
              provider usage credits and send a review request to the customer.
              Provider usage credits are not real money and are not withdrawable.
            </p>
          </div>
          <Input label="Final Price (₹)" type="number" placeholder={String(j?.quoted_price ?? "")}
            value={finalPrice} onChange={setFinalPrice}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setCloseModal(false)}>Cancel</Btn>
            <Btn variant="success" size="sm" loading={closeAction.loading} onClick={handleClose}>
              Close Job ✓
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Send quote modal */}
      <Modal open={quoteModal} onClose={() => setQuoteModal(false)}
        title={isConsultation ? "Send Consultation Report + Quote" : "Send Quote to Customer"}>
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {quoteAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{quoteAction.error}</p>
            </div>
          )}
          <div>
            <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:8 }}>
              {isConsultation ? "Recommended Parts" : "Parts"}
            </label>
            {quoteParts.map((p, i) => (
              <div key={i} style={{ display:"flex", gap:8, marginBottom:8 }}>
                <Input placeholder="Part name" value={p.name} onChange={v => updatePart(i, "name", v)}/>
                <Input placeholder="Cost" type="number" value={String(p.cost || "")}
                  onChange={v => updatePart(i, "cost", v)}/>
              </div>
            ))}
            <Btn variant="ghost" size="sm" onClick={() => setQuoteParts(prev => [...prev, { name:"", cost:0 }])}>
              + Add Part
            </Btn>
          </div>
          <Input label="Labour Estimate (₹)" type="number" placeholder="500"
            value={labourEstimate} onChange={setLabourEstimate}/>
          <Input label={isConsultation ? "Report / Recommendations for customer" : "Notes for customer"}
            placeholder={isConsultation ? "Your diagnosis and recommended action..." : "Explain what needs to be done..."}
            value={quoteNotes} onChange={setQuoteNotes} rows={3}/>
          <Input label="Valid for (days)" type="number" value={expiryDays} onChange={setExpiryDays}/>
          <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--info-bg)",
            border:"1px solid var(--info-border)", display:"flex", justifyContent:"space-between" }}>
            <span style={{ fontSize:13, color:"var(--info-text)" }}>Total Quote</span>
            <span style={{ fontSize:15, fontWeight:700, color:"var(--info-text)" }}>{fmt(quoteTotal)}</span>
          </div>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setQuoteModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={quoteAction.loading}
              disabled={quoteTotal <= 0} onClick={handleSendQuote}>
              {isConsultation ? "Send Report + Quote" : "Send Quote"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Findings modal */}
      <Modal open={findingsModal} onClose={() => setFindingsModal(false)}
        title={isConsultation ? "Assessment Report" : "Assessment Findings"}>
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {findingsAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{findingsAction.error}</p>
            </div>
          )}
          <Input label="Findings / Diagnosis" placeholder="What did you find? Describe the issue clearly..."
            value={findingsText} onChange={setFindingsText} rows={4}/>
          <Input label="Recommendation" placeholder="What do you recommend? Parts, service, or repair..."
            value={recommendText} onChange={setRecommendText} rows={3}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setFindingsModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={findingsAction.loading}
              disabled={!findingsText.trim()} onClick={handleSubmitFindings}>
              Save Findings
            </Btn>
          </div>
        </div>
      </Modal>
    </TenantLayout>
  );
}
