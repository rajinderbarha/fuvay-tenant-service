'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useApi, useAction } from '../../../../../hooks/useApi';
import { workflowTemplateApi, WorkflowTemplate, WTValidationResult } from '../../../../../lib/api';
import { Btn } from '../../../../../components/shared/ui';

const safeNum = (v: unknown): number => {
  const n = Number(v);
  return isNaN(n) ? 0 : n;
};

const TABS = [
  'Overview', 'Visual Builder', 'Steps', 'Transitions', 'SLA Matrix',
  'Role Ownership', 'Approval Gates', 'Automation Rules', 'Service Mapping',
  'Validation', 'Runtime Analytics', 'Version History', 'Audit Logs',
];

type TabIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;

function ReadinessBadge({ value }: { value: string }) {
  const map: Record<string, string> = { ready: 'badge-success', missing_mapping: 'badge-warning', validation_failed: 'badge-danger', draft: 'badge-muted' };
  return <span className={`badge ${map[value] ?? 'badge-muted'}`}>{value.replace(/_/g, ' ')}</span>;
}

function StatusBadge({ value }: { value: string }) {
  const map: Record<string, string> = { published: 'badge-success', draft: 'badge-muted', archived: 'badge-secondary' };
  return <span className={`badge ${map[value] ?? 'badge-muted'}`}>{value}</span>;
}

function StepTypeBadge({ type }: { type: string }) {
  const map: Record<string, string> = {
    customer_action: 'badge-primary',
    tenant_action: 'badge-secondary',
    staff_action: 'badge-warning',
    system_action: 'badge-muted',
  };
  return <span className={`badge ${map[type] ?? 'badge-muted'}`}>{type.replace(/_/g, ' ')}</span>;
}

// ── Add Step Modal ────────────────────────────────────────────────────────────
function AddStepModal({ wid, onClose, onSaved }: { wid: string; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    step_key: '', step_name: '', step_type: 'staff_action', owner_app: 'staff_app', owner_role: 'technician', display_order: 1,
    requires_photo: false, requires_payment_record: false, customer_visible: false,
  });
  const { execute, loading, error } = useAction(() => workflowTemplateApi.addStep(wid, form as Record<string, unknown>));

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <h3>Add Step</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">Step Name</label>
              <input className="form-input" value={form.step_name} onChange={e => { const n = e.target.value; setForm(f => ({ ...f, step_name: n, step_key: n.toLowerCase().replace(/[^a-z0-9]+/g, '_') })); }} />
            </div>
            <div className="form-group">
              <label className="form-label">Step Key</label>
              <input className="form-input" value={form.step_key} onChange={e => setForm(f => ({ ...f, step_key: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Step Type</label>
              <select className="form-select" value={form.step_type} onChange={e => setForm(f => ({ ...f, step_type: e.target.value }))}>
                <option value="customer_action">Customer Action</option>
                <option value="tenant_action">Tenant Action</option>
                <option value="staff_action">Staff Action</option>
                <option value="system_action">System Action</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Owner Role</label>
              <input className="form-input" value={form.owner_role} onChange={e => setForm(f => ({ ...f, owner_role: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Display Order</label>
              <input type="number" className="form-input" value={form.display_order} onChange={e => setForm(f => ({ ...f, display_order: parseInt(e.target.value) || 1 }))} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
            <label style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.customer_visible} onChange={e => setForm(f => ({ ...f, customer_visible: e.target.checked }))} />
              Customer Visible
            </label>
            <label style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.requires_photo} onChange={e => setForm(f => ({ ...f, requires_photo: e.target.checked }))} />
              Requires Photo
            </label>
            <label style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.requires_payment_record} onChange={e => setForm(f => ({ ...f, requires_payment_record: e.target.checked }))} />
              Requires Payment
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={async () => { await execute(); onSaved(); onClose(); }} disabled={loading || !form.step_key}>
            {loading ? 'Adding...' : 'Add Step'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Add Transition Modal ──────────────────────────────────────────────────────
function AddTransitionModal({ wid, steps, onClose, onSaved }: { wid: string; steps: Array<Record<string, unknown>>; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ from_step_key: '', to_step_key: '', action_label: '', allowed_role: 'system', requires_reason: false, triggers_notification: false });
  const { execute, loading, error } = useAction(() => workflowTemplateApi.addTransition(wid, form as Record<string, unknown>));

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 460 }}>
        <div className="modal-header">
          <h3>Add Transition</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <div className="form-group">
            <label className="form-label">From Step</label>
            <select className="form-select" value={form.from_step_key} onChange={e => setForm(f => ({ ...f, from_step_key: e.target.value }))}>
              <option value="">Select...</option>
              {steps.map((s, i) => <option key={i} value={String(s.step_key)}>{String(s.step_name)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">To Step</label>
            <select className="form-select" value={form.to_step_key} onChange={e => setForm(f => ({ ...f, to_step_key: e.target.value }))}>
              <option value="">Select...</option>
              {steps.map((s, i) => <option key={i} value={String(s.step_key)}>{String(s.step_name)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Action Label</label>
            <input className="form-input" value={form.action_label} onChange={e => setForm(f => ({ ...f, action_label: e.target.value }))} placeholder="Accept Booking" />
          </div>
          <div className="form-group">
            <label className="form-label">Allowed Role</label>
            <input className="form-input" value={form.allowed_role} onChange={e => setForm(f => ({ ...f, allowed_role: e.target.value }))} />
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
            <label style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.triggers_notification} onChange={e => setForm(f => ({ ...f, triggers_notification: e.target.checked }))} />
              Triggers Notification
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={async () => { await execute(); onSaved(); onClose(); }} disabled={loading || !form.from_step_key || !form.to_step_key}>
            {loading ? 'Adding...' : 'Add Transition'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Add Mapping Modal ─────────────────────────────────────────────────────────
function AddMappingModal({ wid, onClose, onSaved }: { wid: string; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ vertical_key: 'home_services', category_name: '', master_service_name: '' });
  const { execute, loading, error } = useAction(() => workflowTemplateApi.addServiceMapping(wid, form as Record<string, unknown>));

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h3>Add Service Mapping</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <div className="form-group">
            <label className="form-label">Category Name</label>
            <input className="form-input" value={form.category_name} onChange={e => setForm(f => ({ ...f, category_name: e.target.value }))} placeholder="AC Repair" />
          </div>
          <div className="form-group">
            <label className="form-label">Master Service Name</label>
            <input className="form-input" value={form.master_service_name} onChange={e => setForm(f => ({ ...f, master_service_name: e.target.value }))} placeholder="Split AC Service" />
          </div>
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={async () => { await execute(); onSaved(); onClose(); }} disabled={loading}>
            {loading ? 'Saving...' : 'Add Mapping'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Rollback Modal ────────────────────────────────────────────────────────────
function RollbackModal({ wid, versionNumber, onClose, onRolledBack }: { wid: string; versionNumber: number; onClose: () => void; onRolledBack: () => void }) {
  const [reason, setReason] = useState('');
  const { execute, loading, error } = useAction(() => workflowTemplateApi.rollback(wid, versionNumber, reason));

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h3>Rollback to v{versionNumber}</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <p style={{ color: 'var(--color-text-secondary)' }}>This will restore the workflow to version {versionNumber} and set status to draft.</p>
          <div className="form-group">
            <label className="form-label">Reason</label>
            <textarea className="form-input" rows={2} value={reason} onChange={e => setReason(e.target.value)} placeholder="Reason for rollback..." />
          </div>
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="danger" size="sm" onClick={async () => { await execute(); onRolledBack(); onClose(); }} disabled={loading}>
            {loading ? 'Rolling back...' : 'Rollback'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Publish Dialog ────────────────────────────────────────────────────────────
function PublishDialog({ tmpl, onClose, onPublished }: { tmpl: WorkflowTemplate; onClose: () => void; onPublished: () => void }) {
  const [reason, setReason] = useState('');
  const { execute, loading, error } = useAction(() => workflowTemplateApi.publish(tmpl.id, reason));

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h3>Publish Workflow</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <p>Publish <strong>{tmpl.name}</strong>?</p>
          <textarea className="form-input" rows={2} value={reason} onChange={e => setReason(e.target.value)} placeholder="Change notes..." />
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="success" size="sm" onClick={async () => { await execute(); onPublished(); onClose(); }} disabled={loading}>
            {loading ? 'Publishing...' : 'Publish'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Main Detail Page ──────────────────────────────────────────────────────────
export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>();
  const wid = params.id;
  const [activeTab, setActiveTab] = useState<TabIndex>(0);
  const [showAddStep, setShowAddStep] = useState(false);
  const [showAddTransition, setShowAddTransition] = useState(false);
  const [showAddMapping, setShowAddMapping] = useState(false);
  const [rollbackVer, setRollbackVer] = useState<number | null>(null);
  const [showPublish, setShowPublish] = useState(false);
  const [validationResult, setValidationResult] = useState<WTValidationResult | null>(null);
  const [simulationResult, setSimulationResult] = useState<Record<string, unknown> | null>(null);

  const { data: tmpl, loading, refetch } = useApi(() => workflowTemplateApi.get(wid), [wid]);
  const { data: analytics } = useApi(() => workflowTemplateApi.getRuntimeAnalytics(wid), [wid]);
  const { data: versions, refetch: refetchVersions } = useApi(() => workflowTemplateApi.getVersions(wid), [wid, activeTab === 11]);
  const { data: auditLogs } = useApi(() => workflowTemplateApi.getAuditLogs(wid), [wid, activeTab === 12]);

  const { execute: doValidate, loading: validating } = useAction(() => workflowTemplateApi.validate(wid));
  const { execute: doSimulate, loading: simulating } = useAction(() =>
    workflowTemplateApi.simulate(wid, { scenario: 'normal_completion', role: 'system' })
  );
  const { execute: doDeleteStep } = useAction((sid: string) => workflowTemplateApi.deleteStep(wid, sid));
  const { execute: doDeleteTransition } = useAction((tid: string) => workflowTemplateApi.deleteTransition(wid, tid));
  const { execute: doDeleteMapping } = useAction((mid: string) => workflowTemplateApi.deleteServiceMapping(wid, mid));

  if (loading) return <div className="page-container"><div className="empty-state">Loading...</div></div>;
  if (!tmpl) return <div className="page-container"><div className="empty-state">Workflow not found.</div></div>;

  const t = tmpl as WorkflowTemplate;
  const steps = (Array.isArray(t.steps_json) ? t.steps_json : []) as Array<Record<string, unknown>>;
  const transitions = (Array.isArray(t.transitions_json) ? t.transitions_json : []) as Array<Record<string, unknown>>;
  const mappings = (Array.isArray(t.service_mappings_json) ? t.service_mappings_json : []) as Array<Record<string, unknown>>;
  const slaRules = (Array.isArray(t.sla_rules_json) ? t.sla_rules_json : []) as Array<Record<string, unknown>>;
  const approvalGates = (Array.isArray(t.approval_gates_json) ? t.approval_gates_json : []) as Array<Record<string, unknown>>;
  const automationRules = (Array.isArray(t.automation_rules_json) ? t.automation_rules_json : []) as Array<Record<string, unknown>>;

  const handleValidate = async () => {
    const r = await doValidate();
    if (r) { setValidationResult(r as WTValidationResult); refetch(); }
  };

  const handleSimulate = async () => {
    const r = await doSimulate();
    if (r) setSimulationResult(r as unknown as Record<string, unknown>);
  };

  const ROLES = ['Customer', 'Tenant Owner', 'Tenant Manager', 'Technician', 'Support Admin', 'System'];

  const renderTab = () => {
    switch (activeTab) {
      // ── Overview ────────────────────────────────────────────────────────────
      case 0:
        return (
          <div>
            {t.readiness_status === 'missing_mapping' && (
              <div className="alert alert-warning" style={{ marginBottom: 'var(--space-4)' }}>
                This workflow has no service mappings. Go to the Service Mapping tab to add one.
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
              {[
                ['Name', t.name],
                ['Workflow Key', t.workflow_key],
                ['Vertical', t.vertical_key],
                ['Type', t.workflow_type],
                ['Status', <StatusBadge key="s" value={t.status} />],
                ['Version', `v${t.current_version}`],
                ['Readiness', <ReadinessBadge key="r" value={t.readiness_status} />],
                ['Runtime Health', t.runtime_health],
                ['Steps', steps.length],
                ['Transitions', transitions.length],
                ['Published At', t.published_at ? new Date(t.published_at).toLocaleString() : '—'],
                ['Created', new Date(t.created_at).toLocaleString()],
              ].map(([label, value], i) => (
                <div key={i} style={{ padding: 'var(--space-3)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-1)' }}>{label}</div>
                  <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{value}</div>
                </div>
              ))}
            </div>
          </div>
        );

      // ── Visual Builder ───────────────────────────────────────────────────────
      case 1:
        return (
          <div>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Btn variant="primary" size="sm" onClick={() => setShowAddStep(true)}>+ Add Step</Btn>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {steps.sort((a, b) => safeNum(a.display_order) - safeNum(b.display_order)).map((s, i) => {
                const stepType = String(s.step_type ?? 'staff_action');
                const borderMap: Record<string, string> = {
                  customer_action: 'var(--color-primary)',
                  tenant_action: 'var(--color-secondary)',
                  staff_action: 'var(--color-warning)',
                  system_action: 'var(--color-text-disabled)',
                };
                return (
                  <div key={i}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-3)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)', borderLeft: `4px solid ${borderMap[stepType] ?? 'var(--color-border)'}` }}>
                      <div style={{ fontWeight: 700, minWidth: 28, color: 'var(--color-text-secondary)' }}>{safeNum(s.display_order)}.</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{String(s.step_name)}</div>
                        <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
                          <StepTypeBadge type={stepType} />
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{String(s.owner_role)}</span>
                          {s.requires_photo && <span className="badge badge-warning">photo</span>}
                          {s.customer_visible && <span className="badge badge-primary">customer visible</span>}
                        </div>
                      </div>
                      <Btn variant="danger" size="xs" onClick={async () => { await doDeleteStep(String(s.id)); refetch(); }}>Delete</Btn>
                    </div>
                    {i < steps.length - 1 && (
                      <div style={{ textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: 'var(--text-lg)', padding: 'var(--space-1)' }}>↓</div>
                    )}
                  </div>
                );
              })}
            </div>
            {steps.length === 0 && <div className="empty-state">No steps defined. Click Add Step to begin.</div>}
            {transitions.length > 0 && (
              <div style={{ marginTop: 'var(--space-4)' }}>
                <h4 style={{ marginBottom: 'var(--space-2)' }}>Transitions</h4>
                {transitions.map((tr, i) => (
                  <div key={i} style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', padding: 'var(--space-1) 0' }}>
                    <code>{String(tr.from_step_key)}</code> → <code>{String(tr.to_step_key)}</code>
                    <span style={{ marginLeft: 'var(--space-2)' }}>({String(tr.action_label)})</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      // ── Steps ────────────────────────────────────────────────────────────────
      case 2:
        return (
          <div>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Btn variant="primary" size="sm" onClick={() => setShowAddStep(true)}>+ Add Step</Btn>
            </div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Step Key</th><th>Name</th><th>Type</th><th>Owner App</th><th>Owner Role</th>
                    <th>Customer</th><th>Staff</th><th>Photo</th><th>Payment</th><th>SLA</th><th>Order</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {steps.sort((a, b) => safeNum(a.display_order) - safeNum(b.display_order)).map((s, i) => (
                    <tr key={i}>
                      <td><code style={{ fontSize: 'var(--text-xs)' }}>{String(s.step_key)}</code></td>
                      <td>{String(s.step_name)}</td>
                      <td><StepTypeBadge type={String(s.step_type ?? '')} /></td>
                      <td>{String(s.owner_app ?? '—')}</td>
                      <td>{String(s.owner_role ?? '—')}</td>
                      <td>{s.customer_visible ? '✓' : '—'}</td>
                      <td>{s.staff_visible ? '✓' : '—'}</td>
                      <td>{s.requires_photo ? '✓' : '—'}</td>
                      <td>{s.requires_payment_record ? '✓' : '—'}</td>
                      <td>{s.sla_enabled ? '✓' : '—'}</td>
                      <td>{safeNum(s.display_order)}</td>
                      <td>
                        <Btn variant="danger" size="xs" onClick={async () => { await doDeleteStep(String(s.id)); refetch(); }}>Delete</Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {steps.length === 0 && <div className="empty-state">No steps defined.</div>}
          </div>
        );

      // ── Transitions ──────────────────────────────────────────────────────────
      case 3:
        return (
          <div>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Btn variant="primary" size="sm" onClick={() => setShowAddTransition(true)}>+ Add Transition</Btn>
            </div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr><th>From Step</th><th>To Step</th><th>Action Label</th><th>Allowed Role</th><th>Notification</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {transitions.map((tr, i) => (
                    <tr key={i}>
                      <td><code style={{ fontSize: 'var(--text-xs)' }}>{String(tr.from_step_key)}</code></td>
                      <td><code style={{ fontSize: 'var(--text-xs)' }}>{String(tr.to_step_key)}</code></td>
                      <td>{String(tr.action_label ?? '—')}</td>
                      <td>{String(tr.allowed_role ?? '—')}</td>
                      <td>{tr.triggers_notification ? '✓' : '—'}</td>
                      <td>
                        <Btn variant="danger" size="xs" onClick={async () => { await doDeleteTransition(String(tr.id)); refetch(); }}>Delete</Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {transitions.length === 0 && <div className="empty-state">No transitions defined.</div>}
          </div>
        );

      // ── SLA Matrix ───────────────────────────────────────────────────────────
      case 4:
        return (
          <div>
            {slaRules.length === 0 ? (
              <div className="empty-state">No SLA rules defined. SLA rules will control escalation timing per step.</div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead><tr><th>Step</th><th>SLA Duration</th><th>Warning Before</th><th>Breach Action</th><th>Escalation Role</th></tr></thead>
                  <tbody>
                    {slaRules.map((r, i) => (
                      <tr key={i}>
                        <td>{String(r.step_key ?? '—')}</td>
                        <td>{String(r.sla_duration ?? '—')}</td>
                        <td>{String(r.warning_before ?? '—')}</td>
                        <td>{String(r.breach_action ?? '—')}</td>
                        <td>{String(r.escalation_role ?? '—')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );

      // ── Role Ownership ───────────────────────────────────────────────────────
      case 5:
        return (
          <div className="table-container" style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Step</th>
                  {ROLES.map(r => <th key={r}>{r}</th>)}
                </tr>
              </thead>
              <tbody>
                {steps.sort((a, b) => safeNum(a.display_order) - safeNum(b.display_order)).map((s, i) => (
                  <tr key={i}>
                    <td><span style={{ fontWeight: 600 }}>{String(s.step_name)}</span><br /><code style={{ fontSize: 'var(--text-xs)' }}>{String(s.step_key)}</code></td>
                    {ROLES.map(r => {
                      const ownerRole = String(s.owner_role ?? '').toLowerCase().replace(/ /g, '_');
                      const rKey = r.toLowerCase().replace(/ /g, '_');
                      const isOwner = ownerRole === rKey;
                      return <td key={r} style={{ textAlign: 'center' }}>{isOwner ? <span className="badge badge-primary">Owner</span> : '—'}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      // ── Approval Gates ───────────────────────────────────────────────────────
      case 6:
        return (
          <div>
            {approvalGates.length === 0 ? (
              <div className="empty-state">No approval gates configured.</div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead><tr><th>Gate Name</th><th>Trigger Step</th><th>Approver Role</th><th>Auto Approve</th><th>SLA</th></tr></thead>
                  <tbody>
                    {approvalGates.map((g, i) => (
                      <tr key={i}>
                        <td>{String(g.name ?? '—')}</td>
                        <td>{String(g.trigger_step ?? '—')}</td>
                        <td>{String(g.approver_role ?? '—')}</td>
                        <td>{g.auto_approve ? 'Yes' : 'No'}</td>
                        <td>{String(g.sla_hours ?? '—')}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );

      // ── Automation Rules ─────────────────────────────────────────────────────
      case 7:
        return (
          <div>
            <div style={{ marginBottom: 'var(--space-3)', padding: 'var(--space-3)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)', borderLeft: '4px solid var(--color-primary)' }}>
              <strong>Mandatory Rule:</strong> Usage credit deduction triggers only after <code>job_completed</code> step.
            </div>
            {automationRules.length === 0 ? (
              <div className="empty-state">No automation rules configured.</div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead><tr><th>Trigger Event</th><th>Action</th><th>Target</th><th>Condition</th><th>Status</th></tr></thead>
                  <tbody>
                    {automationRules.map((r, i) => (
                      <tr key={i}>
                        <td>{String(r.trigger_event ?? '—')}</td>
                        <td>{String(r.action ?? '—')}</td>
                        <td>{String(r.target ?? '—')}</td>
                        <td>{String(r.condition ?? '—')}</td>
                        <td><span className="badge badge-muted">{String(r.status ?? 'active')}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );

      // ── Service Mapping ──────────────────────────────────────────────────────
      case 8:
        return (
          <div>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Btn variant="primary" size="sm" onClick={() => setShowAddMapping(true)}>+ Add Mapping</Btn>
            </div>
            {mappings.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-title">No service mappings</div>
                <div className="empty-state-desc">This workflow will not be triggered automatically until at least one service mapping is added.</div>
                <Btn variant="primary" size="sm" onClick={() => setShowAddMapping(true)} style={{ marginTop: 'var(--space-3)' }}>Add Mapping</Btn>
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead><tr><th>Vertical</th><th>Category</th><th>Master Service</th><th>Status</th><th>Actions</th></tr></thead>
                  <tbody>
                    {mappings.map((m, i) => (
                      <tr key={i}>
                        <td>{String(m.vertical_key ?? '—')}</td>
                        <td>{String(m.category_name ?? '—')}</td>
                        <td>{String(m.master_service_name ?? '—')}</td>
                        <td><span className="badge badge-success">{String(m.status ?? 'active')}</span></td>
                        <td>
                          <Btn variant="danger" size="xs" onClick={async () => { await doDeleteMapping(String(m.id)); refetch(); }}>Remove</Btn>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );

      // ── Validation ───────────────────────────────────────────────────────────
      case 9: {
        const vr = validationResult ?? (t.validation_result_json as unknown as WTValidationResult | null);
        return (
          <div>
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Btn variant="primary" size="sm" onClick={handleValidate} disabled={validating}>
                {validating ? 'Validating...' : 'Run Validation'}
              </Btn>
            </div>
            {vr && (
              <div>
                <div style={{ marginBottom: 'var(--space-3)' }}>
                  {vr.passed
                    ? <div className="alert alert-success">✓ Validation Passed — Readiness: {vr.readiness_status}</div>
                    : <div className="alert alert-danger">✗ Validation Failed — {(vr.errors ?? []).length} error(s)</div>
                  }
                </div>
                {(vr.errors ?? []).length > 0 && (
                  <div className="table-container" style={{ marginBottom: 'var(--space-3)' }}>
                    <table className="data-table">
                      <thead><tr><th>Severity</th><th>Field</th><th>Message</th></tr></thead>
                      <tbody>
                        {(vr.errors ?? []).map((e, i) => (
                          <tr key={i}><td><span className="badge badge-danger">{e.severity}</span></td><td>{e.field}</td><td>{e.message}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {(vr.warnings ?? []).length > 0 && (
                  <div className="table-container">
                    <table className="data-table">
                      <thead><tr><th>Field</th><th>Warning</th></tr></thead>
                      <tbody>
                        {(vr.warnings ?? []).map((w, i) => (
                          <tr key={i}><td>{w.field}</td><td>{w.message}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
            {!vr && <div className="empty-state">Click Run Validation to check this workflow.</div>}
          </div>
        );
      }

      // ── Runtime Analytics ────────────────────────────────────────────────────
      case 10: {
        const a = analytics as Record<string, unknown> | null ?? {};
        const jobsProcessed = safeNum(a.jobs_processed);
        if (jobsProcessed === 0) {
          return <div className="empty-state">No runtime usage yet. This workflow has not been used in any active jobs.</div>;
        }
        return (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-3)' }}>
            {[
              ['Jobs Processed', safeNum(a.jobs_processed)],
              ['Completion Rate', `${safeNum(a.completion_rate)}%`],
              ['Avg Duration', String(a.avg_duration ?? 'N/A')],
              ['SLA Breach Rate', `${safeNum(a.sla_breach_rate)}%`],
              ['Failed Transitions', safeNum(a.failed_transitions)],
            ].map(([label, value], i) => (
              <div key={i} style={{ padding: 'var(--space-4)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--color-text-primary)' }}>{value}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>{label}</div>
              </div>
            ))}
          </div>
        );
      }

      // ── Version History ──────────────────────────────────────────────────────
      case 11: {
        const vList = (Array.isArray(versions) ? versions : []) as unknown as Array<Record<string, unknown>>;
        return (
          <div>
            {vList.length === 0 ? (
              <div className="empty-state">No versions published yet.</div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead><tr><th>Version</th><th>Status</th><th>Published At</th><th>Rollback</th><th>Change Summary</th><th>Actions</th></tr></thead>
                  <tbody>
                    {vList.map((v, i) => (
                      <tr key={i}>
                        <td>v{safeNum(v.version_number)}</td>
                        <td><StatusBadge value={String(v.status ?? 'draft')} /></td>
                        <td>{v.published_at ? new Date(String(v.published_at)).toLocaleString() : '—'}</td>
                        <td>{v.is_rollback ? 'Yes' : 'No'}</td>
                        <td>{String(v.change_summary ?? '—')}</td>
                        <td>
                          <Btn variant="warning" size="xs" onClick={() => setRollbackVer(safeNum(v.version_number))}>Rollback</Btn>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      }

      // ── Audit Logs ───────────────────────────────────────────────────────────
      case 12: {
        const logs = (Array.isArray(auditLogs) ? auditLogs : []) as Array<Record<string, unknown>>;
        return (
          <div className="table-container">
            <table className="data-table">
              <thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Details</th></tr></thead>
              <tbody>
                {logs.map((l, i) => (
                  <tr key={i}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 'var(--text-xs)' }}>{l.created_at ? new Date(String(l.created_at)).toLocaleString() : '—'}</td>
                    <td><span className="badge badge-muted">{String(l.action_type ?? '—')}</span></td>
                    <td>{String(l.actor_user_id ?? 'system')}</td>
                    <td style={{ fontSize: 'var(--text-xs)' }}>{l.reason ? String(l.reason) : '—'}</td>
                  </tr>
                ))}
                {logs.length === 0 && <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No audit logs yet.</td></tr>}
              </tbody>
            </table>
          </div>
        );
      }

      default:
        return <div className="empty-state">Select a tab</div>;
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <Btn variant="ghost" size="sm" onClick={() => window.location.href = '/admin/workflows/templates'}>← Back</Btn>
          <div>
            <h1 className="page-title" style={{ marginBottom: 'var(--space-1)' }}>{t.name}</h1>
            <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
              <StatusBadge value={t.status} />
              <ReadinessBadge value={t.readiness_status} />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>v{t.current_version}</span>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <Btn variant="ghost" size="sm" onClick={handleValidate} disabled={validating}>Validate</Btn>
          <Btn variant="ghost" size="sm" onClick={handleSimulate} disabled={simulating}>Simulate</Btn>
          {t.status !== 'published' && t.readiness_status === 'ready' && (
            <Btn variant="success" size="sm" onClick={() => setShowPublish(true)}>Publish</Btn>
          )}
          <Btn variant="secondary" size="sm" onClick={async () => { await workflowTemplateApi.clone(t.id); window.location.href = '/admin/workflows/templates'; }}>Clone</Btn>
        </div>
      </div>

      {/* Simulation result banner */}
      {simulationResult && (
        <div className="alert alert-primary" style={{ marginBottom: 'var(--space-3)' }}>
          Simulation: <strong>{(simulationResult.steps as unknown[])?.length ?? 0} steps</strong> → Final state: <strong>{String(simulationResult.final_state)}</strong>
          <Btn variant="ghost" size="xs" onClick={() => setSimulationResult(null)} style={{ marginLeft: 'var(--space-2)' }}>×</Btn>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 'var(--space-1)', overflowX: 'auto', borderBottom: '2px solid var(--color-border)', marginBottom: 'var(--space-4)', paddingBottom: 2 }}>
        {TABS.map((tab, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(i as TabIndex)}
            style={{
              padding: 'var(--space-2) var(--space-3)',
              whiteSpace: 'nowrap',
              fontWeight: activeTab === i ? 700 : 400,
              color: activeTab === i ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              borderBottom: activeTab === i ? '2px solid var(--color-primary)' : '2px solid transparent',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 'var(--text-sm)',
              marginBottom: -2,
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>{renderTab()}</div>

      {/* Modals */}
      {showAddStep && <AddStepModal wid={wid} onClose={() => setShowAddStep(false)} onSaved={refetch} />}
      {showAddTransition && <AddTransitionModal wid={wid} steps={steps} onClose={() => setShowAddTransition(false)} onSaved={refetch} />}
      {showAddMapping && <AddMappingModal wid={wid} onClose={() => setShowAddMapping(false)} onSaved={refetch} />}
      {rollbackVer !== null && <RollbackModal wid={wid} versionNumber={rollbackVer} onClose={() => setRollbackVer(null)} onRolledBack={() => { refetch(); refetchVersions(); }} />}
      {showPublish && <PublishDialog tmpl={t} onClose={() => setShowPublish(false)} onPublished={refetch} />}
    </div>
  );
}
