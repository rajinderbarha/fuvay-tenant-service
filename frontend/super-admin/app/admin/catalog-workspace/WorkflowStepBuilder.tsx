"use client";
/**
 * Cross-app step builder for a job type's workflow blueprint (migration 274).
 *
 * The capability flags above this in the Workflow tab say what a job REQUIRES.
 * This says what actually happens, in order, in which app, and who does it —
 * the journey the technician app, provider portal and customer app all render
 * from a single definition.
 *
 * Every vocabulary here is fetched from the API rather than hard-coded, so the
 * builder can only ever offer values the server will accept. In particular the
 * job-status list is derived server-side from the execution engine's own
 * transition graph: a step mapped to a status that cannot exist would render
 * forever without completing.
 */
import React, { useCallback, useState } from "react";
import { ArrowDown, ArrowUp, Plus, X, AlertTriangle, CheckCircle2, Info } from "lucide-react";

import { Btn, Badge, Card, Input, Select } from "../../../components/shared/ui";
import {
  catalogWorkspaceApi,
  type ServiceJobWorkflow, type WorkflowStepDef, type WorkflowTransitionDef,
  type WorkflowOwnerApp, type WorkflowOwnerRole,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const APP_LABEL: Record<string, string> = {
  customer_app: "Customer app", tenant_app: "Provider portal",
  staff_app: "Technician app", admin: "Admin", system: "System",
};

function blankStep(order: number): WorkflowStepDef {
  return {
    step_key: "", step_name: "", maps_to_status: null,
    owner_app: "staff_app", owner_role: "technician",
    customer_visible: false, tenant_visible: true, staff_visible: true, admin_visible: true,
    requires_note: false, requires_photo: false, requires_approval: false,
    sla_minutes: null, display_order: order,
  };
}

/** Derive a stable key from the name, so an admin never has to invent one. */
function keyFromName(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

export function WorkflowStepBuilder({
  masterServiceId, jobTypeId, workflow, canWrite, notify, onSaved,
}: {
  masterServiceId: string; jobTypeId: string;
  workflow: ServiceJobWorkflow; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onSaved: () => void;
}) {
  const [steps, setSteps] = useState<WorkflowStepDef[]>(workflow.steps ?? []);
  const [transitions, setTransitions] = useState<WorkflowTransitionDef[]>(workflow.transitions ?? []);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const options = useApi(
    useCallback(() => catalogWorkspaceApi.getWorkflowStepOptions(masterServiceId, jobTypeId),
      [masterServiceId, jobTypeId]), [masterServiceId, jobTypeId]);
  const review = useApi(
    useCallback(() => catalogWorkspaceApi.reviewWorkflowSteps(masterServiceId, jobTypeId),
      [masterServiceId, jobTypeId]), [masterServiceId, jobTypeId]);

  // Re-sync when the parent loads a different job type's workflow.
  React.useEffect(() => {
    setSteps(workflow.steps ?? []);
    setTransitions(workflow.transitions ?? []);
    setDirty(false);
    setError(null);
  }, [workflow]);

  const save = useAction(async () => {
    setError(null);
    const cleaned = steps.map((s, i) => ({
      ...s,
      step_key: s.step_key.trim() || keyFromName(s.step_name) || `step_${i + 1}`,
      display_order: i + 1,
    }));
    try {
      await catalogWorkspaceApi.setJobTypeWorkflow(masterServiceId, jobTypeId, {
        steps: cleaned, transitions,
      });
      setDirty(false);
      notify("Workflow steps saved as a new version.");
      review.refetch();
      onSaved();
    } catch (e) {
      // The server validates the whole definition; surface its message verbatim
      // rather than a generic failure, because it names the offending field.
      setError(e instanceof Error ? e.message : "Couldn't save the workflow steps.");
    }
  });

  const patch = (i: number, changes: Partial<WorkflowStepDef>) => {
    setSteps(prev => prev.map((s, j) => (j === i ? { ...s, ...changes } : s)));
    setDirty(true);
  };
  const move = (i: number, delta: number) => {
    const j = i + delta;
    if (j < 0 || j >= steps.length) return;
    const next = [...steps];
    [next[i], next[j]] = [next[j], next[i]];
    setSteps(next.map((s, k) => ({ ...s, display_order: k + 1 })));
    setDirty(true);
  };
  const remove = (i: number) => {
    const key = steps[i].step_key;
    setSteps(prev => prev.filter((_, j) => j !== i).map((s, k) => ({ ...s, display_order: k + 1 })));
    // Transitions referencing a deleted step would be rejected on save, so drop
    // them here rather than letting the admin discover it as a 422.
    setTransitions(prev => prev.filter(t => t.from_step_key !== key && t.to_step_key !== key));
    setDirty(true);
  };

  const statusOptions = [
    { value: "", label: "No job status (booking-level or post-completion)" },
    ...(options.data?.job_statuses ?? []).map(s => ({ value: s, label: s.replace(/_/g, " ") })),
  ];
  const appOptions = (options.data?.owner_apps ?? []).map(a => ({ value: a, label: APP_LABEL[a] ?? a }));
  const roleOptions = (options.data?.owner_roles ?? []).map(r => ({ value: r, label: r.replace(/_/g, " ") }));
  const stepOptions = steps.filter(s => s.step_key || s.step_name)
    .map(s => ({ value: s.step_key || keyFromName(s.step_name), label: s.step_name || s.step_key }));

  const mappedCount = steps.filter(s => s.maps_to_status).length;

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        gap: 12, marginBottom: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700 }}>Cross-app journey</div>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "3px 0 0", maxWidth: 640 }}>
            The ordered steps this job runs through. Each step belongs to one app and is shown
            only to the audiences you tick, so internal work never reaches the customer.
            Editing publishes a new version — jobs already running keep the journey they started on.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {workflow.version_number ? <Badge variant="muted" size="sm">v{workflow.version_number}</Badge> : null}
          <Btn size="sm" variant="secondary" disabled={!canWrite}
            onClick={() => { setSteps(prev => [...prev, blankStep(prev.length + 1)]); setDirty(true); }}>
            <Plus size={13}/> Add step
          </Btn>
          <Btn size="sm" disabled={!canWrite || !dirty || save.loading} onClick={() => save.execute()}>
            {save.loading ? "Saving…" : "Save journey"}
          </Btn>
        </div>
      </div>

      {error && (
        <div role="alert" style={{ padding: "9px 12px", marginBottom: 10, borderRadius: "var(--radius-md)",
          background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{error}</p>
        </div>
      )}

      {/* A journey whose steps map to no job status renders but can never
          progress, which is the single most likely way to author a useless
          workflow — so it is called out before the admin leaves the page. */}
      {steps.length > 0 && mappedCount === 0 && (
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start", padding: "9px 12px",
          marginBottom: 10, borderRadius: "var(--radius-md)", background: "var(--warning-bg)",
          border: "1px solid var(--warning-border)" }}>
          <AlertTriangle size={14} style={{ color: "var(--warning-text)", flexShrink: 0, marginTop: 1 }}/>
          <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0 }}>
            No step is mapped to a job status, so no step can ever be marked complete from the
            job&apos;s real state. Map at least one step to the status it represents.
          </p>
        </div>
      )}
      {!dirty && review.data && (review.data.warnings.length > 0) && (
        <div style={{ padding: "9px 12px", marginBottom: 10, borderRadius: "var(--radius-md)",
          background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
          {review.data.warnings.map((w, i) => (
            <p key={i} style={{ fontSize: 12, color: "var(--text-secondary)", margin: i ? "5px 0 0" : 0,
              display: "flex", gap: 6 }}>
              <Info size={13} style={{ flexShrink: 0, marginTop: 1 }}/>{w}
            </p>
          ))}
        </div>
      )}

      {steps.length === 0 ? (
        <Card padding={20}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            No journey defined. This job type falls back to the platform&apos;s standard stage
            sequence. Add steps to control what each app shows and who acts at every stage.
          </p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {steps.map((s, i) => (
            <Card key={i} padding={12}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 2, paddingTop: 18 }}>
                  <Btn size="xs" variant="ghost" disabled={!canWrite || i === 0} onClick={() => move(i, -1)}>
                    <ArrowUp size={12}/>
                  </Btn>
                  <span style={{ fontSize: 11, textAlign: "center", color: "var(--text-tertiary)", fontWeight: 700 }}>
                    {i + 1}
                  </span>
                  <Btn size="xs" variant="ghost" disabled={!canWrite || i === steps.length - 1} onClick={() => move(i, 1)}>
                    <ArrowDown size={12}/>
                  </Btn>
                </div>

                <div style={{ flex: 1, minWidth: 0, display: "grid", gap: 10 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 10 }}>
                    <Input label="Step name" value={s.step_name} disabled={!canWrite}
                      onChange={v => patch(i, { step_name: v, step_key: s.step_key || keyFromName(v) })}
                      placeholder="e.g. Technician Assigned"/>
                    <Select label="Owned by" value={s.owner_app} disabled={!canWrite}
                      onChange={v => patch(i, { owner_app: v as WorkflowOwnerApp })} options={appOptions}/>
                    <Select label="Acted by" value={s.owner_role} disabled={!canWrite}
                      onChange={v => patch(i, { owner_role: v as WorkflowOwnerRole })} options={roleOptions}/>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 10 }}>
                    <Select label="Marks the job as" value={s.maps_to_status ?? ""} disabled={!canWrite}
                      onChange={v => patch(i, { maps_to_status: v || null })} options={statusOptions}/>
                    <Input label="Step SLA (minutes)" type="number" disabled={!canWrite}
                      value={s.sla_minutes == null ? "" : String(s.sla_minutes)}
                      onChange={v => patch(i, { sla_minutes: v ? Number(v) : null })}/>
                  </div>

                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                      textTransform: "uppercase", letterSpacing: "0.05em" }}>Visible to</span>
                    {([["customer_visible", "Customer"], ["tenant_visible", "Provider"],
                       ["staff_visible", "Technician"], ["admin_visible", "Admin"]] as const).map(([k, label]) => (
                      <label key={k} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12 }}>
                        <input type="checkbox" disabled={!canWrite} checked={!!s[k]}
                          onChange={e => patch(i, { [k]: e.target.checked } as Partial<WorkflowStepDef>)}/>
                        {label}
                      </label>
                    ))}
                  </div>

                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                      textTransform: "uppercase", letterSpacing: "0.05em" }}>Requires</span>
                    {([["requires_photo", "Photo"], ["requires_note", "Note"],
                       ["requires_approval", "Approval"]] as const).map(([k, label]) => (
                      <label key={k} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12 }}>
                        <input type="checkbox" disabled={!canWrite} checked={!!s[k]}
                          onChange={e => patch(i, { [k]: e.target.checked } as Partial<WorkflowStepDef>)}/>
                        {label}
                      </label>
                    ))}
                  </div>
                </div>

                <Btn size="xs" variant="ghost" disabled={!canWrite} onClick={() => remove(i)}
                  aria-label={`Remove ${s.step_name || "step"}`}>
                  <X size={12}/>
                </Btn>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Transitions: who may move the job from one step to the next. */}
      {steps.length >= 2 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Transitions ({transitions.length})</span>
            <Btn size="xs" variant="secondary" disabled={!canWrite}
              onClick={() => {
                setTransitions(prev => [...prev, {
                  from_step_key: stepOptions[0]?.value ?? "", to_step_key: stepOptions[1]?.value ?? "",
                  action_label: null, allowed_role: "technician",
                  requires_reason: false, triggers_notification: false, auto_transition: false,
                }]);
                setDirty(true);
              }}>
              <Plus size={12}/> Add transition
            </Btn>
          </div>
          {transitions.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              No transitions defined. Steps still render in order; transitions record which role
              may advance the job and what the action is called in each app.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {transitions.map((t, i) => (
                <Card key={i} padding={10}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr auto", gap: 8, alignItems: "end" }}>
                    <Select label="From" value={t.from_step_key} disabled={!canWrite}
                      onChange={v => { setTransitions(p => p.map((x, j) => j === i ? { ...x, from_step_key: v } : x)); setDirty(true); }}
                      options={stepOptions}/>
                    <Select label="To" value={t.to_step_key} disabled={!canWrite}
                      onChange={v => { setTransitions(p => p.map((x, j) => j === i ? { ...x, to_step_key: v } : x)); setDirty(true); }}
                      options={stepOptions}/>
                    <Input label="Action label" value={t.action_label ?? ""} disabled={!canWrite}
                      onChange={v => { setTransitions(p => p.map((x, j) => j === i ? { ...x, action_label: v || null } : x)); setDirty(true); }}
                      placeholder="e.g. Start Travel"/>
                    <Select label="Allowed role" value={t.allowed_role} disabled={!canWrite}
                      onChange={v => { setTransitions(p => p.map((x, j) => j === i ? { ...x, allowed_role: v as WorkflowOwnerRole } : x)); setDirty(true); }}
                      options={roleOptions}/>
                    <Btn size="xs" variant="ghost" disabled={!canWrite}
                      onClick={() => { setTransitions(p => p.filter((_, j) => j !== i)); setDirty(true); }}>
                      <X size={12}/>
                    </Btn>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {!dirty && steps.length > 0 && review.data?.valid && review.data.warnings.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--success-text)", margin: "12px 0 0",
          display: "flex", gap: 6, alignItems: "center" }}>
          <CheckCircle2 size={13}/> Journey is coherent — {steps.length} steps, {mappedCount} mapped to a job status.
        </p>
      )}
    </div>
  );
}
