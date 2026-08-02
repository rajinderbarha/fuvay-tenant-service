"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { PageShell, PageHeader, SearchBar, ActionMenu } from "../../../components/shared/layout";
import { Card, CardHeader, Badge, Btn, Modal, Input, Skeleton, StatCard } from "../../../components/shared/ui";
import {
  masterDataApi, catalogApi,
  type MasterWorkflowTemplate, type WorkflowTemplatesSummary, type WorkflowStep,
  type WorkflowTransition, type WorkflowServiceMapping, type CategoryOption,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  GitBranch, Plus, Pencil, Power, PowerOff, Copy, GitCommit, Zap, Map as MapIcon,
  ClipboardList, RefreshCw, Sparkles, CheckCircle2, XCircle, AlertTriangle, X,
} from "lucide-react";

const TH: React.CSSProperties = {
  padding: "9px 10px", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
  letterSpacing: "0.06em", textTransform: "uppercase", background: "var(--surface-sunken)",
  borderBottom: "1px solid var(--border)", textAlign: "left",
};
const TD: React.CSSProperties = { padding: "10px 10px", fontSize: 13, borderBottom: "1px solid var(--border)" };
const selectStyle: React.CSSProperties = {
  height: 36, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px",
  fontSize: 13, background: "var(--surface)", color: "var(--text-primary)",
};

const WORKFLOW_TYPES = [
  "repair", "installation", "uninstallation", "inspection", "maintenance",
  "cleaning", "delivery", "appointment", "lead_followup", "custom",
];
const STEP_TYPES = [
  "system", "customer_action", "tenant_action", "technician_action",
  "admin_action", "approval", "notification", "automation", "condition",
];
const ACTORS = [
  "system", "customer", "tenant_owner", "tenant_manager", "technician",
  "platform_admin", "support_admin", "finance_admin",
];

function statusBadge(status: string) {
  const map: Record<string, "success" | "warning" | "muted" | "danger" | "info"> = {
    draft: "warning", active: "success", inactive: "muted", deprecated: "info", archived: "muted",
  };
  return <Badge variant={map[status] ?? "muted"} size="sm">{status}</Badge>;
}
function readinessBadge(readiness: string) {
  const map: Record<string, { label: string; variant: "success" | "warning" | "danger" | "muted" }> = {
    ready: { label: "Ready", variant: "success" },
    missing_steps: { label: "Missing Steps", variant: "danger" },
    missing_mapping: { label: "Missing Mapping", variant: "warning" },
    invalid_transitions: { label: "Invalid Transitions", variant: "danger" },
  };
  const m = map[readiness] ?? { label: readiness, variant: "muted" as const };
  return <Badge variant={m.variant} size="sm">{m.label}</Badge>;
}

function deriveReadiness(row: MasterWorkflowTemplate): string {
  const steps = row.steps ?? [];
  if (steps.length < 2) return "missing_steps";
  const starts = steps.filter(s => s.is_start).length;
  const terminals = steps.filter(s => s.is_terminal).length;
  if (starts !== 1 || terminals < 1) return "invalid_transitions";
  const codes = new Set(steps.map(s => s.step_code));
  for (const t of row.transitions ?? []) {
    if (!codes.has(t.from_step_code) || !codes.has(t.to_step_code)) return "invalid_transitions";
  }
  if (!row.category_id && !row.master_service_id) return "missing_mapping";
  return "ready";
}

// ── Seed defaults modal ────────────────────────────────────────────────────────
function SeedDefaultsModal({ open, onClose, onSeeded }: { open: boolean; onClose: () => void; onSeeded: () => void }) {
  const preview = useApi(useCallback(() => open ? masterDataApi.seedWorkflowDefaultsPreview() : Promise.resolve(null), [open]), [open]);
  const seed = useAction(async () => {
    await masterDataApi.seedWorkflowDefaults();
    onSeeded(); onClose();
  });
  return (
    <Modal open={open} onClose={onClose} title="Seed Home Services Default Workflows" size="lg">
      {preview.loading && <Skeleton height={120} />}
      {!preview.loading && preview.data && (
        <div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
            This will create <strong>{preview.data.will_create}</strong> new draft workflow template(s).
            {preview.data.already_exist.length > 0 && (
              <> Already exist: {preview.data.already_exist.join(", ")}.</>
            )}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
            {preview.data.templates.map(t => (
              <div key={t.name} style={{ padding: "10px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{t.name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{t.description}</div>
                </div>
                <Badge variant="muted" size="sm">{t.steps} steps</Badge>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
            <Btn onClick={() => seed.execute()} loading={seed.loading} disabled={preview.data.will_create === 0}>
              Seed {preview.data.will_create} Template(s)
            </Btn>
          </div>
        </div>
      )}
    </Modal>
  );
}

// ── Create / Edit modal ────────────────────────────────────────────────────────
const BLANK_FORM = {
  name: "", template_code: "", workflow_type: "repair", description: "",
  category_id: "", master_service_id: "",
  estimated_duration_minutes: "", max_sla_hours: "", display_order: 0,
  requires_technician_assignment: true, requires_customer_confirmation: false,
  requires_photo_proof: false, requires_part_approval: false,
  requires_estimate_approval: false, requires_direct_payment_confirmation: false,
  allows_reschedule: true, allows_cancellation: true, allows_dispute_after_completion: true,
};
type FormState = typeof BLANK_FORM;

function CreateEditModal({
  open, editing, onClose, onSaved,
}: { open: boolean; editing: MasterWorkflowTemplate | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<FormState>(BLANK_FORM);
  const [catQuery, setCatQuery] = useState("");
  const cats = useApi(useCallback(() => catalogApi.getCategoryOptions({ q: catQuery || undefined }), [catQuery]), [catQuery]);

  React.useEffect(() => {
    if (editing) {
      setForm({
        name: editing.name, template_code: editing.template_code ?? editing.slug,
        workflow_type: editing.workflow_type, description: editing.description ?? "",
        category_id: editing.category_id ?? "", master_service_id: editing.master_service_id ?? "",
        estimated_duration_minutes: editing.estimated_duration_minutes ? String(editing.estimated_duration_minutes) : "",
        max_sla_hours: editing.max_sla_hours ? String(editing.max_sla_hours) : "",
        display_order: editing.display_order,
        requires_technician_assignment: editing.requires_technician_assignment ?? true,
        requires_customer_confirmation: editing.requires_customer_confirmation ?? false,
        requires_photo_proof: editing.requires_photo_proof ?? false,
        requires_part_approval: editing.requires_part_approval ?? false,
        requires_estimate_approval: editing.requires_estimate_approval ?? false,
        requires_direct_payment_confirmation: editing.requires_direct_payment_confirmation ?? false,
        allows_reschedule: editing.allows_reschedule ?? true,
        allows_cancellation: editing.allows_cancellation ?? true,
        allows_dispute_after_completion: editing.allows_dispute_after_completion ?? true,
      });
    } else {
      setForm(BLANK_FORM);
    }
  }, [editing, open]);

  const save = useAction(async () => {
    const payload = {
      ...form,
      estimated_duration_minutes: form.estimated_duration_minutes ? Number(form.estimated_duration_minutes) : undefined,
      max_sla_hours: form.max_sla_hours ? Number(form.max_sla_hours) : undefined,
      category_id: form.category_id || undefined,
      master_service_id: form.master_service_id || undefined,
    };
    if (editing) await masterDataApi.updateWorkflowTemplate(editing.id, payload);
    else await masterDataApi.createWorkflowTemplate(payload);
    onSaved(); onClose();
  });

  const toggle = (key: keyof FormState) => (
    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, padding: "6px 0" }}>
      <input type="checkbox" checked={form[key] as boolean} onChange={e => setForm(f => ({ ...f, [key]: e.target.checked }))} />
      {key.replace(/_/g, " ").replace(/^./, c => c.toUpperCase())}
    </label>
  );

  return (
    <Modal open={open} onClose={onClose} title={editing ? "Edit Workflow Template" : "New Workflow Template"} size="lg">
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {save.error && (
          <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
            <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{save.error}</p>
          </div>
        )}

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>Basic Details</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Template Name *" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} />
            <Input label="Template Code" placeholder="auto from name" value={form.template_code} onChange={v => setForm(f => ({ ...f, template_code: v }))} />
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Workflow Type *</label>
            <select value={form.workflow_type} onChange={e => setForm(f => ({ ...f, workflow_type: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
              {WORKFLOW_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2}
              style={{ width: "100%", padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", boxSizing: "border-box" }} />
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>Scope & Mapping</div>
          <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Category *</label>
          <select value={form.category_id} onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
            <option value="">Select category…</option>
            {(cats.data ?? []).map((c: CategoryOption) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>Runtime Settings</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
            {toggle("requires_technician_assignment")}
            {toggle("requires_customer_confirmation")}
            {toggle("requires_photo_proof")}
            {toggle("requires_part_approval")}
            {toggle("requires_estimate_approval")}
            {toggle("requires_direct_payment_confirmation")}
            {toggle("allows_reschedule")}
            {toggle("allows_cancellation")}
            {toggle("allows_dispute_after_completion")}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>SLA Settings</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <Input label="Est. Duration (min)" type="number" value={form.estimated_duration_minutes} onChange={v => setForm(f => ({ ...f, estimated_duration_minutes: v }))} />
            <Input label="Max SLA (hours)" type="number" value={form.max_sla_hours} onChange={v => setForm(f => ({ ...f, max_sla_hours: v }))} />
            <Input label="Display Order" type="number" value={String(form.display_order)} onChange={v => setForm(f => ({ ...f, display_order: Number(v) || 0 }))} />
          </div>
        </div>

        {editing && editing.status === "active" && (
          <div style={{ padding: "10px 14px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)" }}>
            <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0 }}>
              This template is active. Saving changes will create a new draft version — the active version keeps running unmodified for existing jobs.
            </p>
          </div>
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn onClick={() => save.execute()} loading={save.loading} disabled={!form.name.trim() || !form.category_id}>
            {editing ? "Save Changes" : "Create Template"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Workflow Builder modal ─────────────────────────────────────────────────────
const BLANK_STEP: Partial<WorkflowStep> = {
  step_name: "", step_type: "technician_action", actor: "technician",
  is_start: false, is_terminal: false, is_required: true, can_skip: false,
  requires_note: false, requires_photo: false, requires_document: false,
  requires_customer_signature: false, requires_customer_approval: false, requires_admin_approval: false,
};

function WorkflowBuilderModal({ templateId, onClose, onChanged }: { templateId: string | null; onClose: () => void; onChanged: () => void }) {
  const detail = useApi(useCallback(() => templateId ? masterDataApi.getWorkflowTemplate(templateId) : Promise.resolve(null), [templateId]), [templateId]);
  const [stepForm, setStepForm] = useState<Partial<WorkflowStep> | null>(null);
  const [transForm, setTransForm] = useState<Partial<WorkflowTransition> | null>(null);
  const [validation, setValidation] = useState<{ valid: boolean; errors: string[]; warnings: string[] } | null>(null);

  const addOrUpdateStep = useAction(async () => {
    if (!templateId || !stepForm) return;
    if (stepForm.id) await masterDataApi.updateWorkflowStep(templateId, stepForm.id, stepForm);
    else await masterDataApi.addWorkflowStep(templateId, stepForm);
    setStepForm(null); detail.refetch(); onChanged();
  });
  const deleteStep = useAction(async (stepId: string) => {
    if (!templateId) return;
    await masterDataApi.deleteWorkflowStep(templateId, stepId);
    detail.refetch(); onChanged();
  });
  const addTransition = useAction(async () => {
    if (!templateId || !transForm) return;
    await masterDataApi.addWorkflowTransition(templateId, transForm);
    setTransForm(null); detail.refetch(); onChanged();
  });
  const deleteTransition = useAction(async (id: string) => {
    if (!templateId) return;
    await masterDataApi.deleteWorkflowTransition(templateId, id);
    detail.refetch(); onChanged();
  });
  const validate = useAction(async () => {
    if (!templateId) return;
    const res = await masterDataApi.validateWorkflowTemplate(templateId);
    setValidation(res);
  });

  const t = detail.data as MasterWorkflowTemplate | null;
  const steps = t?.steps ?? [];
  const transitions = t?.transitions ?? [];

  return (
    <Modal open={!!templateId} onClose={onClose} title={`Workflow Builder — ${t?.name ?? ""}`} size="xl">
      {detail.loading && <Skeleton height={200} />}
      {!detail.loading && t && (
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", gap: 6 }}>
              {statusBadge(t.status)}
              {readinessBadge(deriveReadiness(t))}
            </div>
            <Btn size="sm" variant="secondary" onClick={() => validate.execute()} loading={validate.loading}>Validate Workflow</Btn>
          </div>

          {validation && (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", background: validation.valid ? "var(--success-bg)" : "var(--danger-bg)", border: `1px solid ${validation.valid ? "var(--success-border)" : "var(--danger-border)"}` }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: validation.valid ? "var(--success-text)" : "var(--danger-text)" }}>
                {validation.valid ? "Workflow is valid and can be activated." : "This workflow cannot be activated because required steps or transitions are missing."}
              </p>
              {validation.errors.map((e, i) => <p key={i} style={{ margin: "4px 0 0", fontSize: 12, color: "var(--danger-text)" }}>{e}</p>)}
              {validation.warnings.map((w, i) => <p key={i} style={{ margin: "4px 0 0", fontSize: 12, color: "var(--warning-text)" }}>{w}</p>)}
            </div>
          )}

          {/* Steps */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>Steps ({steps.length})</span>
              <Btn size="xs" variant="secondary" onClick={() => setStepForm({ ...BLANK_STEP })}><Plus size={12} />Add Step</Btn>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {steps.map((s, i) => (
                <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                  <span style={{ width: 20, height: 20, borderRadius: "50%", background: "var(--accent-muted)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>{i + 1}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>
                      {s.step_name} {s.is_start && <Badge variant="info" size="sm">start</Badge>} {s.is_terminal && <Badge variant="muted" size="sm">terminal</Badge>}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{s.step_code} · {s.step_type} · {s.actor}</div>
                  </div>
                  <Btn size="xs" variant="ghost" onClick={() => setStepForm(s)}><Pencil size={11} /></Btn>
                  <Btn size="xs" variant="ghost" onClick={() => deleteStep.execute(s.id)}><X size={11} /></Btn>
                </div>
              ))}
              {steps.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No steps yet. Add the first step above.</p>}
            </div>
          </div>

          {/* Transitions */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>Transitions ({transitions.length})</span>
              <Btn size="xs" variant="secondary" onClick={() => setTransForm({ allowed_actor: "system" })} disabled={steps.length < 2}>
                <Plus size={12} />Add Transition
              </Btn>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {transitions.map(tr => (
                <div key={tr.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                  <span style={{ fontSize: 12, flex: 1 }}>
                    <code>{tr.from_step_code}</code> → <code>{tr.to_step_code}</code>
                    <Badge variant="muted" size="sm">{tr.allowed_actor}</Badge>
                    {tr.auto_transition && <Badge variant="info" size="sm">auto</Badge>}
                  </span>
                  <Btn size="xs" variant="ghost" onClick={() => deleteTransition.execute(tr.id)}><X size={11} /></Btn>
                </div>
              ))}
              {transitions.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No transitions yet.</p>}
            </div>
          </div>
        </div>
      )}

      {/* Step editor sub-modal */}
      <Modal open={!!stepForm} onClose={() => setStepForm(null)} title={stepForm?.id ? "Edit Step" : "Add Step"} size="md">
        {stepForm && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Input label="Step Name *" value={stepForm.step_name ?? ""} onChange={v => setStepForm(f => ({ ...f, step_name: v }))} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Step Type *</label>
                <select value={stepForm.step_type} onChange={e => setStepForm(f => ({ ...f, step_type: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
                  {STEP_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Actor *</label>
                <select value={stepForm.actor} onChange={e => setStepForm(f => ({ ...f, actor: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
                  {ACTORS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
              {(["is_start", "is_terminal", "is_required", "can_skip", "requires_note", "requires_photo",
                 "requires_document", "requires_customer_signature", "requires_customer_approval", "requires_admin_approval"] as const).map(key => (
                <label key={key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                  <input type="checkbox" checked={!!stepForm[key]} onChange={e => setStepForm(f => ({ ...f, [key]: e.target.checked }))} />
                  {key.replace(/_/g, " ")}
                </label>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setStepForm(null)}>Cancel</Btn>
              <Btn onClick={() => addOrUpdateStep.execute()} loading={addOrUpdateStep.loading} disabled={!stepForm.step_name}>Save Step</Btn>
            </div>
          </div>
        )}
      </Modal>

      {/* Transition editor sub-modal */}
      <Modal open={!!transForm} onClose={() => setTransForm(null)} title="Add Transition" size="sm">
        {transForm && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>From Step</label>
              <select value={transForm.from_step_code ?? ""} onChange={e => setTransForm(f => ({ ...f, from_step_code: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
                <option value="">Select…</option>
                {steps.map(s => <option key={s.id} value={s.step_code}>{s.step_name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>To Step</label>
              <select value={transForm.to_step_code ?? ""} onChange={e => setTransForm(f => ({ ...f, to_step_code: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
                <option value="">Select…</option>
                {steps.map(s => <option key={s.id} value={s.step_code}>{s.step_name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Allowed Actor</label>
              <select value={transForm.allowed_actor} onChange={e => setTransForm(f => ({ ...f, allowed_actor: e.target.value }))} style={{ ...selectStyle, width: "100%" }}>
                {ACTORS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <input type="checkbox" checked={!!transForm.auto_transition} onChange={e => setTransForm(f => ({ ...f, auto_transition: e.target.checked }))} />
              Auto transition (system-driven, no actor action required)
            </label>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setTransForm(null)}>Cancel</Btn>
              <Btn onClick={() => addTransition.execute()} loading={addTransition.loading}
                   disabled={!transForm.from_step_code || !transForm.to_step_code}>Save Transition</Btn>
            </div>
          </div>
        )}
      </Modal>
    </Modal>
  );
}

// ── Mapping modal ──────────────────────────────────────────────────────────────
function MappingModal({ templateId, onClose }: { templateId: string | null; onClose: () => void }) {
  const mappings = useApi(useCallback(() => templateId ? masterDataApi.listWorkflowMappings(templateId) : Promise.resolve({ mappings: [], total: 0 }), [templateId]), [templateId]);
  const [catQuery, setCatQuery] = useState("");
  const cats = useApi(useCallback(() => catalogApi.getCategoryOptions({ q: catQuery || undefined }), [catQuery]), [catQuery]);
  const [categoryId, setCategoryId] = useState("");
  const [priority, setPriority] = useState(0);

  const create = useAction(async () => {
    if (!templateId || !categoryId) return;
    await masterDataApi.createWorkflowMapping(templateId, { category_id: categoryId, priority });
    setCategoryId(""); mappings.refetch();
  });
  const remove = useAction(async (mappingId: string) => {
    if (!templateId) return;
    await masterDataApi.deleteWorkflowMapping(templateId, mappingId);
    mappings.refetch();
  });

  return (
    <Modal open={!!templateId} onClose={onClose} title="Map Workflow to Service" size="md">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={categoryId} onChange={e => setCategoryId(e.target.value)} style={{ ...selectStyle, flex: 1 }}>
            <option value="">Select category…</option>
            {(cats.data ?? []).map((c: CategoryOption) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <input type="number" value={priority} onChange={e => setPriority(Number(e.target.value) || 0)} placeholder="Priority"
            style={{ ...selectStyle, width: 90 }} />
          <Btn size="sm" onClick={() => create.execute()} loading={create.loading} disabled={!categoryId}>Add</Btn>
        </div>
        {mappings.loading && <Skeleton height={80} />}
        {!mappings.loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(mappings.data?.mappings ?? []).map((m: WorkflowServiceMapping) => (
              <div key={m.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                <span style={{ fontSize: 12 }}>Category <code>{m.category_id.slice(0, 8)}…</code> · priority {m.priority}</span>
                <Btn size="xs" variant="ghost" onClick={() => remove.execute(m.id)}><X size={11} /></Btn>
              </div>
            ))}
            {(mappings.data?.mappings ?? []).length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No mappings yet.</p>}
          </div>
        )}
      </div>
    </Modal>
  );
}

// ── Runtime preview drawer ──────────────────────────────────────────────────────
function PreviewDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [catQuery, setCatQuery] = useState("");
  const cats = useApi(useCallback(() => open ? catalogApi.getCategoryOptions({ q: catQuery || undefined }) : Promise.resolve([]), [open, catQuery]), [open, catQuery]);
  const [categoryId, setCategoryId] = useState("");
  const [result, setResult] = useState<import("../../../lib/api").WorkflowRuntimePreview | null>(null);
  const run = useAction(async () => {
    const res = await masterDataApi.previewWorkflowRuntime({ category_id: categoryId || undefined });
    setResult(res);
  });

  return (
    <Modal open={open} onClose={onClose} title="Runtime Workflow Preview" size="lg">
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <select value={categoryId} onChange={e => setCategoryId(e.target.value)} style={{ ...selectStyle, flex: 1 }}>
          <option value="">Select category…</option>
          {(cats.data ?? []).map((c: CategoryOption) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <Btn size="sm" onClick={() => run.execute()} loading={run.loading} disabled={!categoryId}>Resolve</Btn>
      </div>
      {result && !result.resolved && (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{result.message}</p>
      )}
      {result?.resolved && result.template && (
        <div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 15, fontWeight: 700 }}>{result.template.name}</span>
            {readinessBadge(result.readiness ?? "")}
            <Badge variant="muted" size="sm">v{result.template.version_number}</Badge>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10 }}>{result.template.steps.length} steps · {result.template.transitions?.length ?? 0} transitions</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {result.template.steps.map((s, i) => (
              <div key={s.id} style={{ display: "flex", gap: 8, alignItems: "center", padding: "7px 10px", background: "var(--surface-sunken)", borderRadius: 6, fontSize: 12 }}>
                <span style={{ color: "var(--text-tertiary)" }}>{i + 1}.</span>
                <span style={{ fontWeight: 600 }}>{s.step_name}</span>
                <Badge variant="muted" size="sm">{s.actor}</Badge>
                {s.requires_photo && <Badge variant="info" size="sm">photo</Badge>}
                {s.requires_customer_approval && <Badge variant="warning" size="sm">approval</Badge>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}

// ── Audit log drawer ────────────────────────────────────────────────────────────
function AuditDrawer({ templateId, onClose }: { templateId: string | null; onClose: () => void }) {
  const audit = useApi(useCallback(() => templateId ? masterDataApi.getWorkflowTemplateAuditLogs(templateId) : Promise.resolve({ audit_log: [], total: 0 }), [templateId]), [templateId]);
  return (
    <Modal open={!!templateId} onClose={onClose} title="Workflow Audit Logs" size="lg">
      {audit.loading && <Skeleton height={100} />}
      {!audit.loading && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr>{["Time", "Action", "Summary"].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
            <tbody>
              {(audit.data?.audit_log ?? []).map(l => (
                <tr key={l.id}>
                  <td style={TD}>{l.created_at ? new Date(l.created_at).toLocaleString() : "—"}</td>
                  <td style={TD}><Badge variant="muted" size="sm">{l.action}</Badge></td>
                  <td style={TD}>{l.change_summary ?? "—"}</td>
                </tr>
              ))}
              {(audit.data?.audit_log ?? []).length === 0 && <tr><td colSpan={3} style={{ padding: 20, textAlign: "center", color: "var(--text-tertiary)" }}>No audit history yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function WorkflowTemplatesPage() {
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [readinessFilter, setReadinessFilter] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const summary = useApi(useCallback(() => masterDataApi.getWorkflowTemplatesSummary(), []), []);
  const list = useApi(useCallback(() => masterDataApi.listWorkflowTemplates({
    q: q || undefined, workflow_type: typeFilter || undefined,
    status: statusFilter || undefined, readiness: readinessFilter || undefined, limit: 100,
  }), [q, typeFilter, statusFilter, readinessFilter]), [q, typeFilter, statusFilter, readinessFilter]);

  const [modal, setModal] = useState<"none" | "create" | "edit">("none");
  const [editing, setEditing] = useState<MasterWorkflowTemplate | null>(null);
  const [seedModal, setSeedModal] = useState(false);
  const [builderId, setBuilderId] = useState<string | null>(null);
  const [mappingId, setMappingId] = useState<string | null>(null);
  const [auditId, setAuditId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };
  const refreshAll = () => { list.refetch(); summary.refetch(); };

  const activate = useAction(async (id: string) => {
    await masterDataApi.activateWorkflowTemplate(id);
    refreshAll(); notify("Workflow activated.");
  });
  const deactivate = useAction(async (id: string) => {
    await masterDataApi.deactivateWorkflowTemplate(id);
    refreshAll(); notify("Workflow deactivated.");
  });
  const clone = useAction(async (id: string) => {
    await masterDataApi.cloneWorkflowTemplate(id);
    refreshAll(); notify("Workflow cloned as new draft.");
  });
  const newVersion = useAction(async (id: string) => {
    await masterDataApi.createWorkflowNewVersion(id);
    refreshAll(); notify("New draft version created.");
  });

  const rows = list.data?.workflow_templates ?? [];
  const s = summary.data as WorkflowTemplatesSummary | null;

  return (
    <AdminLayout activeNav="workflow-templates">
      <PageShell>
        <PageHeader
          title="Workflow Templates"
          description="Configure master job workflows, step transitions, SLA, approvals, and runtime automation."
          primaryAction={<Btn size="sm" variant="primary" onClick={() => { setEditing(null); setModal("create"); }}><Plus size={14} /> New Workflow Template</Btn>}
          secondaryActions={[
            { label: "Seed Home Services Defaults", onClick: () => setSeedModal(true) },
            { label: "Runtime Preview", onClick: () => setPreviewOpen(true) },
            { label: "Refresh", onClick: refreshAll },
          ]}
        />

        {toast && (
          <div style={{ padding: "10px 16px", borderRadius: 10,
            background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
            border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
            color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
            {toast.ok ? "✓" : "✗"} {toast.msg}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {summary.loading ? (
            [...Array(8)].map((_, i) => <Card key={i} padding={18}><Skeleton height={12} width={80} style={{ marginBottom: 10 }} /><Skeleton height={28} width={50} /></Card>)
          ) : s && <>
            <StatCard label="Total Templates" value={s.total_templates} icon={<GitBranch />} />
            <StatCard label="Active Templates" value={s.active_templates} icon={<CheckCircle2 />} trend="up" />
            <StatCard label="Draft Templates" value={s.draft_templates} icon={<Pencil />} onClick={() => setStatusFilter("draft")} />
            <StatCard label="Used By Services" value={s.used_by_services} icon={<MapIcon />} />
            <StatCard label="Missing Steps" value={s.templates_missing_steps} icon={<AlertTriangle />} alert={s.templates_missing_steps > 0} onClick={() => setReadinessFilter("missing_steps")} />
            <StatCard label="SLA Enabled" value={s.sla_enabled} icon={<Zap />} />
            <StatCard label="Approval Workflows" value={s.approval_enabled} icon={<ClipboardList />} />
            <StatCard label="Runtime Ready" value={s.runtime_ready} icon={<CheckCircle2 />} onClick={() => setReadinessFilter("ready")} />
          </>}
        </div>

        <Card padding={0}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ flex: 1, minWidth: 220 }}>
              <SearchBar value={q} onChange={setQ} placeholder="Search by name or code…" />
            </div>
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={selectStyle}>
              <option value="">All Types</option>
              {WORKFLOW_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={selectStyle}>
              <option value="">All Statuses</option>
              {["draft", "active", "inactive", "deprecated", "archived"].map(v => <option key={v} value={v}>{v}</option>)}
            </select>
            <select value={readinessFilter} onChange={e => setReadinessFilter(e.target.value)} style={selectStyle}>
              <option value="">All Readiness</option>
              <option value="ready">Ready</option>
              <option value="missing_steps">Missing Steps</option>
              <option value="missing_mapping">Missing Mapping</option>
              <option value="invalid_transitions">Invalid Transitions</option>
            </select>
            <Btn size="sm" variant="secondary" onClick={refreshAll}><RefreshCw size={13} /></Btn>
          </div>

          {list.loading ? (
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 8 }}>{[...Array(5)].map((_, i) => <Skeleton key={i} height={52} style={{ borderRadius:"var(--radius-md)" }} />)}</div>
          ) : rows.length === 0 ? (
            <div style={{ padding: 48, textAlign: "center" }}>
              <Sparkles size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px", display: "block" }} />
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>No workflow templates yet.</p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 14px" }}>Create a workflow template or seed recommended Home Services workflows.</p>
              <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                <Btn size="sm" onClick={() => { setEditing(null); setModal("create"); }}>Create Template</Btn>
                <Btn size="sm" variant="secondary" onClick={() => setSeedModal(true)}>Seed Home Services Defaults</Btn>
              </div>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>{["Template", "Type", "Steps", "SLA", "Approvals", "Readiness", "Version", "Status", "Updated", "Actions"].map(h => <th key={h} style={TH}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.map(row => {
                    const steps = row.steps ?? [];
                    const customerActions = steps.filter(s => s.step_type === "customer_action").length;
                    const techActions = steps.filter(s => s.step_type === "technician_action").length;
                    const hasApproval = steps.some(s => s.approval_rule);
                    const readiness = deriveReadiness(row);
                    return (
                      <tr key={row.id}>
                        <td style={TD} title={row.description}>
                          <div style={{ fontWeight: 600 }}>{row.name}</div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{row.template_code ?? row.slug}</div>
                        </td>
                        <td style={TD}><Badge variant="muted" size="sm">{row.workflow_type}</Badge></td>
                        <td style={TD}>
                          <div>{steps.length} steps</div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{customerActions} customer · {techActions} technician</div>
                        </td>
                        <td style={TD}>
                          {row.max_sla_hours ? <Badge variant="info" size="sm">{row.max_sla_hours}h</Badge> : <span style={{ color: "var(--text-tertiary)" }}>—</span>}
                        </td>
                        <td style={TD}>{hasApproval ? <Badge variant="warning" size="sm">Yes</Badge> : <span style={{ color: "var(--text-tertiary)" }}>—</span>}</td>
                        <td style={TD}>{readinessBadge(readiness)}</td>
                        <td style={TD}><Badge variant="muted" size="sm">v{row.version_number ?? 1}</Badge></td>
                        <td style={TD}>{statusBadge(row.status)}</td>
                        <td style={TD}><span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{row.updated_at ? new Date(row.updated_at).toLocaleDateString() : "—"}</span></td>
                        <td style={TD}>
                          <ActionMenu items={[
                            { label: "Edit Template", onClick: () => { setEditing(row); setModal("edit"); } },
                            { label: "Open Workflow Builder", onClick: () => setBuilderId(row.id) },
                            { label: "Map to Service", onClick: () => setMappingId(row.id) },
                            { label: "Clone", onClick: () => clone.execute(row.id) },
                            { label: "Create New Version", onClick: () => newVersion.execute(row.id) },
                            row.status === "active"
                              ? { label: "Deactivate", onClick: () => deactivate.execute(row.id), variant: "danger" }
                              : { label: "Activate", onClick: () => activate.execute(row.id) },
                            { label: "Audit Logs", onClick: () => setAuditId(row.id) },
                          ]} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </PageShell>

      <CreateEditModal open={modal !== "none"} editing={editing} onClose={() => setModal("none")} onSaved={refreshAll} />
      <SeedDefaultsModal open={seedModal} onClose={() => setSeedModal(false)} onSeeded={refreshAll} />
      <WorkflowBuilderModal templateId={builderId} onClose={() => setBuilderId(null)} onChanged={refreshAll} />
      <MappingModal templateId={mappingId} onClose={() => setMappingId(null)} />
      <PreviewDrawer open={previewOpen} onClose={() => setPreviewOpen(false)} />
      <AuditDrawer templateId={auditId} onClose={() => setAuditId(null)} />
    </AdminLayout>
  );
}
