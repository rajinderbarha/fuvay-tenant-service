"use client";
/**
 * Dispatch Queue — live view of jobs awaiting/assigned to staff.
 * PROVEN: dispatchApi.getQueue() + getScoring() connected.
 * PROVEN: manual assign/reassign call live API + refetch.
 */
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Select, Input, Skeleton, SectionHeader, EmptyState } from "../../../components/shared/ui";
import { dispatchApi, staffApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { DispatchRecord } from "../../../lib/api";

const STATUS_VARIANT: Record<string, "default"|"success"|"warning"|"danger"|"info"|"muted"> = {
  pending: "warning",
  assigned: "info",
  accepted: "success",
  rejected: "danger",
  expired: "danger",
  escalated: "danger",
  completed: "success",
};

export default function DispatchQueuePage() {
  const queue = useApi(useCallback(() => dispatchApi.getQueue(), []));
  const staffList = useApi(useCallback(() => staffApi.list(), []));

  const [assignModal,  setAssignModal]  = useState(false);
  const [assignRecord, setAssignRecord] = useState<DispatchRecord | null>(null);
  const [assignStaffId,setAssignStaffId]= useState("");
  const [assignReason, setAssignReason] = useState("");

  const [scoringModal, setScoringModal] = useState(false);
  const [scoringJobId, setScoringJobId] = useState<string | null>(null);
  const scoring = useApi(useCallback(
    () => scoringJobId ? dispatchApi.getScoring(scoringJobId) : Promise.resolve(null),
    [scoringJobId]
  ));

  const assignAction = useAction(useCallback(
    (jobId: string, staffId: string, isReassign: boolean, reason: string) =>
      isReassign ? dispatchApi.reassignJob(jobId, staffId, reason)
                 : dispatchApi.dispatchJob(jobId, "manual", staffId),
    []
  ));

  function openAssign(record: DispatchRecord) {
    setAssignRecord(record); setAssignStaffId(""); setAssignReason(""); setAssignModal(true);
  }
  function openScoring(jobId: string) {
    setScoringJobId(jobId); setScoringModal(true);
  }
  async function handleAssign() {
    if (!assignRecord || !assignStaffId) return;
    const isReassign = !!assignRecord.assigned_staff_id;
    const res = await assignAction.execute(assignRecord.job_id, assignStaffId, isReassign, assignReason);
    if (res) { queue.refetch(); setAssignModal(false); }
  }

  const records = queue.data?.items ?? [];
  const activeStaff = (staffList.data?.users ?? []).filter(s => s.is_active);
  const fmtDate = (d?: string) => d ? new Date(d).toLocaleString("en-IN",
    { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" }) : "—";

  const unassignedCount = records.filter(r => !r.assigned_staff_id).length;
  const escalatedCount  = records.filter(r => r.escalation_count > 0).length;

  return (
    <TenantLayout activeNav="dispatch">
      <SectionHeader
        title="Dispatch Queue"
        subtitle={queue.loading ? "Loading..." : `${records.length} jobs in queue`}
        actions={<Btn variant="ghost" size="sm" onClick={queue.refetch}>↻ Refresh</Btn>}
      />

      {!queue.loading && records.length > 0 && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:16 }}>
          <Card padding={16}>
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Total Queued</p>
            <p style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{records.length}</p>
          </Card>
          <Card padding={16}>
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Unassigned</p>
            <p style={{ fontSize:22, fontWeight:700, color: unassignedCount>0 ? "var(--warning-text)" : "var(--text-primary)", margin:0 }}>
              {unassignedCount}
            </p>
          </Card>
          <Card padding={16}>
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Escalated</p>
            <p style={{ fontSize:22, fontWeight:700, color: escalatedCount>0 ? "var(--danger-text)" : "var(--text-primary)", margin:0 }}>
              {escalatedCount}
            </p>
          </Card>
        </div>
      )}

      {queue.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{queue.error}</p>
        </div>
      )}

      {queue.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={110} style={{ borderRadius:14 }}/>)}
        </div>
      ) : records.length === 0 ? (
        <EmptyState icon="📭" title="Queue is empty" description="No jobs currently awaiting dispatch."/>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {records.map(d => (
            <Card key={d.job_id} padding={18}>
              <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
                gap:16, flexWrap:"wrap" }}>
                <div style={{ flex:1, minWidth:220 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                    <a href={`/jobs/${d.job_id}`} style={{ fontSize:13, fontWeight:700,
                      color:"var(--text-link)", textDecoration:"none" }}>
                      Job {d.job_id.slice(0,8)}
                    </a>
                    <Badge variant={STATUS_VARIANT[d.status] ?? "muted"}>{d.status.replace(/_/g," ")}</Badge>
                    <Badge variant="muted">{d.dispatch_mode.replace(/_/g," ")}</Badge>
                    {d.escalation_count > 0 && <Badge variant="danger">Escalated ×{d.escalation_count}</Badge>}
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                    {[
                      { label:"Staff",      v: d.assigned_staff_id ?? "Unassigned" },
                      { label:"Rejections", v: String(d.rejection_count) },
                      { label:"Accepted",   v: fmtDate(d.accepted_at) },
                      { label:"Expires",    v: fmtDate(d.expires_at) },
                    ].map(r => (
                      <div key={r.label} style={{ display:"flex", gap:6 }}>
                        <span style={{ fontSize:11, color:"var(--text-tertiary)", width:70, flexShrink:0 }}>{r.label}</span>
                        <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ display:"flex", gap:8 }}>
                  <Btn variant="ghost" size="sm" onClick={() => openScoring(d.job_id)}>View Scoring</Btn>
                  <Btn variant="secondary" size="sm" onClick={() => openAssign(d)}>
                    {d.assigned_staff_id ? "Reassign" : "Assign"}
                  </Btn>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Assign / reassign modal */}
      <Modal open={assignModal} onClose={() => setAssignModal(false)}
        title={assignRecord?.assigned_staff_id ? "Reassign Staff" : "Assign Staff"}>
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {staffList.loading ? <Skeleton height={38}/> : (
            <Select label="Staff member *" value={assignStaffId} onChange={setAssignStaffId}
              placeholder="Select staff member…"
              options={activeStaff.map(s => ({
                value: s.user_id,
                label: s.full_name,
              }))}/>
          )}
          <Input label="Reason (optional)" placeholder="Reason for assignment..."
            value={assignReason} onChange={setAssignReason} rows={2}/>
          {assignAction.error && <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{assignAction.error}</p>}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setAssignModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={assignAction.loading}
              disabled={!assignStaffId} onClick={handleAssign}>
              {assignRecord?.assigned_staff_id ? "Reassign" : "Assign"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Scoring breakdown modal */}
      <Modal open={scoringModal} onClose={() => setScoringModal(false)} title="Candidate Scoring">
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {(() => { const sd = scoring.data; return scoring.loading ? (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(3)].map((_,i) => <Skeleton key={i} height={40}/>)}
            </div>
          ) : !sd || sd.candidates.length === 0 ? (
            <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No candidates scored.</p>
          ) : (
            <>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap", marginBottom:4 }}>
                {Object.entries(sd.score_weights).map(([k,v]) => (
                  <Badge key={k} variant="muted">{k.replace(/_/g," ")}: {(Number(v)*100).toFixed(0)}%</Badge>
                ))}
              </div>
              {sd.candidates
                .slice().sort((a,b) => b.score - a.score)
                .map(c => (
                <div key={c.staff_id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
                  padding:"10px 0", borderBottom:"1px solid var(--border)" }}>
                  <div>
                    <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                      {c.staff_id.slice(0,8)}
                    </p>
                    {c.distance_km != null && (
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                        {c.distance_km.toFixed(1)} km away
                      </p>
                    )}
                  </div>
                  <Badge variant={c.score >= 70 ? "success" : c.score >= 40 ? "warning" : "muted"}>
                    {c.score.toFixed(0)}%
                  </Badge>
                </div>
              ))}
            </>
          ); })()}
        </div>
      </Modal>
    </TenantLayout>
  );
}
