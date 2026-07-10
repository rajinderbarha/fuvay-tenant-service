'use client';

import { useState, useCallback } from 'react';
import { useApi, useAction } from '../../../../hooks/useApi';
import { workflowTemplateApi, WorkflowTemplate, WorkflowTemplateSummary } from '../../../../lib/api';
import { Btn } from '../../../../components/shared/ui';

const safeNum = (v: unknown): number => {
  const n = Number(v);
  return isNaN(n) ? 0 : n;
};

const VERTICALS = ['universal', 'home_services', 'coaching', 'real_estate', 'restaurant', 'product_marketplace', 'professional_services'];
const WORKFLOW_TYPES = ['repair', 'installation', 'uninstallation', 'inspection', 'cleaning', 'emergency', 'inquiry', 'demo', 'admission', 'followup', 'visit', 'approval', 'order', 'preparation', 'cancellation', 'complaint', 'fulfillment', 'reservation', 'shipping', 'return', 'consultation', 'review', 'appointment'];
const STATUSES = ['draft', 'published', 'archived'];
const READINESS_VALUES = ['draft', 'ready', 'missing_mapping', 'validation_failed'];

function ReadinessBadge({ value }: { value: string }) {
  const map: Record<string, string> = {
    ready: 'badge-success',
    missing_mapping: 'badge-warning',
    validation_failed: 'badge-danger',
    draft: 'badge-muted',
  };
  return <span className={`badge ${map[value] ?? 'badge-muted'}`}>{value.replace(/_/g, ' ')}</span>;
}

function StatusBadge({ value }: { value: string }) {
  const map: Record<string, string> = {
    published: 'badge-success',
    draft: 'badge-muted',
    archived: 'badge-secondary',
  };
  return <span className={`badge ${map[value] ?? 'badge-muted'}`}>{value}</span>;
}

function HealthBadge({ value }: { value: string }) {
  const map: Record<string, string> = {
    healthy: 'badge-success',
    not_used: 'badge-muted',
    warning: 'badge-warning',
    failed: 'badge-danger',
  };
  return <span className={`badge ${map[value] ?? 'badge-muted'}`}>{value.replace(/_/g, ' ')}</span>;
}

function KpiCard({ label, value, onClick, active }: { label: string; value: number; onClick?: () => void; active?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={`kpi-card${active ? ' kpi-card--active' : ''}`}
      style={{ textAlign: 'left', cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className="kpi-value">{safeNum(value)}</div>
      <div className="kpi-label">{label}</div>
    </button>
  );
}

// ── Create Workflow Modal ─────────────────────────────────────────────────────
function CreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ name: '', workflow_key: '', vertical_key: 'home_services', workflow_type: 'repair', description: '', status: 'draft' });
  const { execute, loading, error } = useAction(() =>
    workflowTemplateApi.create(form)
  );

  const handleNameChange = (name: string) => {
    const key = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    setForm(f => ({ ...f, name, workflow_key: key }));
  };

  const handleSubmit = async () => {
    await execute();
    onCreated();
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <h3>New Workflow Template</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <div className="form-group">
            <label className="form-label">Name</label>
            <input className="form-input" value={form.name} onChange={e => handleNameChange(e.target.value)} placeholder="Standard Repair Workflow" />
          </div>
          <div className="form-group">
            <label className="form-label">Workflow Key</label>
            <input className="form-input" value={form.workflow_key} onChange={e => setForm(f => ({ ...f, workflow_key: e.target.value }))} placeholder="standard_repair_workflow" />
          </div>
          <div className="form-group">
            <label className="form-label">Vertical</label>
            <select className="form-select" value={form.vertical_key} onChange={e => setForm(f => ({ ...f, vertical_key: e.target.value }))}>
              {VERTICALS.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Workflow Type</label>
            <input className="form-input" value={form.workflow_type} onChange={e => setForm(f => ({ ...f, workflow_type: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-input" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          </div>
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={handleSubmit} disabled={loading || !form.name || !form.workflow_key}>
            {loading ? 'Creating...' : 'Create Workflow'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Service Mapping Modal ─────────────────────────────────────────────────────
function MappingModal({ templateId, verticalKey, onClose, onSaved }: { templateId: string; verticalKey: string; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ vertical_key: verticalKey, category_name: '', master_service_name: '' });
  const { execute, loading, error } = useAction(() =>
    workflowTemplateApi.addServiceMapping(templateId, form)
  );

  const handleSubmit = async () => {
    await execute();
    onSaved();
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 460 }}>
        <div className="modal-header">
          <h3>Add Service Mapping</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <div className="form-group">
            <label className="form-label">Vertical</label>
            <select className="form-select" value={form.vertical_key} onChange={e => setForm(f => ({ ...f, vertical_key: e.target.value }))}>
              {VERTICALS.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
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
          <Btn variant="primary" size="sm" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Saving...' : 'Add Mapping'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Simulator Modal ───────────────────────────────────────────────────────────
function SimulatorModal({ template, onClose }: { template: WorkflowTemplate; onClose: () => void }) {
  const [form, setForm] = useState({ scenario: 'normal_completion', role: 'system', start_step: '' });
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const { execute, loading, error } = useAction(() =>
    workflowTemplateApi.simulate(template.id, form)
  );

  const handleSimulate = async () => {
    const r = await execute();
    if (r) setResult(r as unknown as Record<string, unknown>);
  };

  const steps = Array.isArray(template.steps_json) ? template.steps_json as Array<Record<string, unknown>> : [];

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 600 }}>
        <div className="modal-header">
          <h3>Simulate — {template.name}</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">Scenario</label>
              <select className="form-select" value={form.scenario} onChange={e => setForm(f => ({ ...f, scenario: e.target.value }))}>
                <option value="normal_completion">Normal Completion</option>
                <option value="provider_rejects">Provider Rejects</option>
                <option value="sla_breach">SLA Breach</option>
                <option value="complaint_raised">Complaint Raised</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Start Step</label>
              <select className="form-select" value={form.start_step} onChange={e => setForm(f => ({ ...f, start_step: e.target.value }))}>
                <option value="">First Step</option>
                {steps.map((s, i) => <option key={i} value={String(s.step_key)}>{String(s.step_name)}</option>)}
              </select>
            </div>
          </div>
          <Btn variant="primary" size="sm" onClick={handleSimulate} disabled={loading}>
            {loading ? 'Simulating...' : 'Run Simulation'}
          </Btn>
          {result && (
            <div style={{ marginTop: 'var(--space-3)' }}>
              <h4 style={{ marginBottom: 'var(--space-2)', color: 'var(--color-text-primary)' }}>Simulation Result</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                {(Array.isArray(result.steps) ? result.steps : []).map((s: Record<string, unknown>, i: number) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ color: 'var(--color-text-secondary)', minWidth: 24 }}>{i + 1}.</span>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{String(s.step_name)}</div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{String(s.action)} · {String(s.role)}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 'var(--space-2)', color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)' }}>
                Final state: <strong>{String(result.final_state)}</strong>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Close</Btn>
        </div>
      </div>
    </div>
  );
}

// ── Publish Dialog ────────────────────────────────────────────────────────────
function PublishDialog({ template, onClose, onPublished }: { template: WorkflowTemplate; onClose: () => void; onPublished: () => void }) {
  const [reason, setReason] = useState('');
  const { execute, loading, error } = useAction(() =>
    workflowTemplateApi.publish(template.id, reason)
  );

  const handlePublish = async () => {
    await execute();
    onPublished();
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 440 }}>
        <div className="modal-header">
          <h3>Publish Workflow</h3>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && <div className="alert alert-danger">{String(error)}</div>}
          <p style={{ color: 'var(--color-text-primary)' }}>Publish <strong>{template.name}</strong>?</p>
          <div className="form-group">
            <label className="form-label">Reason (optional)</label>
            <textarea className="form-input" rows={2} value={reason} onChange={e => setReason(e.target.value)} placeholder="Release notes..." />
          </div>
        </div>
        <div className="modal-footer">
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="success" size="sm" onClick={handlePublish} disabled={loading}>
            {loading ? 'Publishing...' : 'Publish'}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function WorkflowTemplatesPage() {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [activeKpi, setActiveKpi] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [mappingTarget, setMappingTarget] = useState<WorkflowTemplate | null>(null);
  const [simulateTarget, setSimulateTarget] = useState<WorkflowTemplate | null>(null);
  const [publishTarget, setPublishTarget] = useState<WorkflowTemplate | null>(null);

  const { data: summary, loading: summaryLoading } = useApi(() => workflowTemplateApi.getSummary(), []);
  const { data: list, loading: listLoading, refetch } = useApi(
    () => workflowTemplateApi.list(filters as Record<string, string>),
    [JSON.stringify(filters)]
  );

  const { execute: doSeedDefaults, loading: seeding } = useAction(() => workflowTemplateApi.seedDefaults());
  const { execute: doValidateAll } = useAction(async () => {
    const items = (list as { items: WorkflowTemplate[] } | null)?.items ?? [];
    for (const t of items) {
      await workflowTemplateApi.validate(t.id);
    }
    refetch();
  });

  const { execute: doClone } = useAction((id: string) => workflowTemplateApi.clone(id));
  const { execute: doArchive } = useAction((id: string) => workflowTemplateApi.archive(id));
  const { execute: doValidate } = useAction((id: string) => workflowTemplateApi.validate(id));

  const handleSeed = async () => {
    await doSeedDefaults();
    refetch();
  };

  const handleKpiClick = (key: string, filterKey: string, filterVal: string) => {
    if (activeKpi === key) {
      setActiveKpi(null);
      setFilters({});
    } else {
      setActiveKpi(key);
      setFilters({ [filterKey]: filterVal });
    }
  };

  const items = (list as { items: WorkflowTemplate[] } | null)?.items ?? [];
  const s = (summary as WorkflowTemplateSummary | null) ?? {
    total: 0, published: 0, draft: 0, missing_mapping: 0, runtime_ready: 0,
    sla_enabled: 0, approval_workflows: 0, automation_enabled: 0, used_by_services: 0, runtime_errors: 0,
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Workflow Engine Control Center</h1>
          <p className="page-subtitle">Manage multi-step workflow templates across all verticals and service types</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <Btn variant="ghost" size="sm" onClick={() => doValidateAll()}>Validate All</Btn>
          <Btn variant="secondary" size="sm" onClick={handleSeed} disabled={seeding}>
            {seeding ? 'Seeding...' : 'Seed Defaults'}
          </Btn>
          <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ New Workflow</Btn>
        </div>
      </div>

      {/* KPI Cards — Row 1 */}
      {!summaryLoading && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
            <KpiCard label="Total Templates" value={safeNum(s.total)} onClick={() => handleKpiClick('total', '', '')} active={activeKpi === 'total'} />
            <KpiCard label="Published" value={safeNum(s.published)} onClick={() => handleKpiClick('published', 'status', 'published')} active={activeKpi === 'published'} />
            <KpiCard label="Draft" value={safeNum(s.draft)} onClick={() => handleKpiClick('draft', 'status', 'draft')} active={activeKpi === 'draft'} />
            <KpiCard label="Missing Mapping" value={safeNum(s.missing_mapping)} onClick={() => handleKpiClick('missing_mapping', 'readiness', 'missing_mapping')} active={activeKpi === 'missing_mapping'} />
            <KpiCard label="Runtime Ready" value={safeNum(s.runtime_ready)} onClick={() => handleKpiClick('runtime_ready', 'readiness', 'ready')} active={activeKpi === 'runtime_ready'} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
            <KpiCard label="SLA Enabled" value={safeNum(s.sla_enabled)} />
            <KpiCard label="Approval Gates" value={safeNum(s.approval_workflows)} />
            <KpiCard label="Automation Rules" value={safeNum(s.automation_enabled)} />
            <KpiCard label="Used By Services" value={safeNum(s.used_by_services)} />
            <KpiCard label="Runtime Errors" value={safeNum(s.runtime_errors)} />
          </div>
        </>
      )}

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          className="form-input"
          style={{ flex: 1, minWidth: 200 }}
          placeholder="Search workflows..."
          value={filters.q ?? ''}
          onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
        />
        <select className="form-select" style={{ minWidth: 160 }} value={filters.vertical ?? ''} onChange={e => setFilters(f => ({ ...f, vertical: e.target.value }))}>
          <option value="">All Verticals</option>
          {VERTICALS.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}
        </select>
        <select className="form-select" style={{ minWidth: 140 }} value={filters.status ?? ''} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="form-select" style={{ minWidth: 160 }} value={filters.readiness ?? ''} onChange={e => setFilters(f => ({ ...f, readiness: e.target.value }))}>
          <option value="">All Readiness</option>
          {READINESS_VALUES.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
        </select>
        {Object.keys(filters).some(k => filters[k]) && (
          <Btn variant="ghost" size="sm" onClick={() => { setFilters({}); setActiveKpi(null); }}>Clear</Btn>
        )}
      </div>

      {/* Table */}
      {listLoading ? (
        <div className="empty-state">Loading workflows...</div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">⚡</div>
          <div className="empty-state-title">No workflow templates yet</div>
          <div className="empty-state-desc">Seed defaults to get started with pre-built workflow templates.</div>
          <Btn variant="primary" size="sm" onClick={handleSeed} disabled={seeding} style={{ marginTop: 'var(--space-3)' }}>Seed Defaults</Btn>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Type</th>
                <th>Steps</th>
                <th>Transitions</th>
                <th>Readiness</th>
                <th>Health</th>
                <th>Version</th>
                <th>Status</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(t => (
                <tr key={t.id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{t.name}</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                      <code>{t.workflow_key}</code>
                      {' · '}
                      <span className="badge badge-muted">{t.vertical_key.replace(/_/g, ' ')}</span>
                    </div>
                  </td>
                  <td>{t.workflow_type}</td>
                  <td>{Array.isArray(t.steps_json) ? t.steps_json.length : 0}</td>
                  <td>{Array.isArray(t.transitions_json) ? t.transitions_json.length : 0}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', flexWrap: 'wrap' }}>
                      <ReadinessBadge value={t.readiness_status} />
                      {t.readiness_status === 'missing_mapping' && (
                        <Btn variant="warning" size="xs" onClick={() => setMappingTarget(t)}>Fix</Btn>
                      )}
                    </div>
                  </td>
                  <td><HealthBadge value={t.runtime_health} /></td>
                  <td>v{t.current_version}</td>
                  <td><StatusBadge value={t.status} /></td>
                  <td style={{ whiteSpace: 'nowrap', fontSize: 'var(--text-xs)' }}>{t.updated_at ? new Date(t.updated_at).toLocaleDateString() : '—'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 'var(--space-1)', flexWrap: 'wrap' }}>
                      <Btn variant="ghost" size="xs" onClick={() => window.location.href = `/admin/workflows/templates/${t.id}`}>Detail</Btn>
                      <Btn variant="ghost" size="xs" onClick={async () => { await doValidate(t.id); refetch(); }}>Validate</Btn>
                      <Btn variant="ghost" size="xs" onClick={() => setSimulateTarget(t)}>Simulate</Btn>
                      <Btn variant="ghost" size="xs" onClick={async () => { await doClone(t.id); refetch(); }}>Clone</Btn>
                      {t.status === 'draft' && t.readiness_status === 'ready' && (
                        <Btn variant="success" size="xs" onClick={() => setPublishTarget(t)}>Publish</Btn>
                      )}
                      {t.status !== 'archived' && (
                        <Btn variant="danger" size="xs" onClick={async () => { if (confirm('Archive this workflow?')) { await doArchive(t.id); refetch(); } }}>Archive</Btn>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      {showCreate && <CreateModal onClose={() => setShowCreate(false)} onCreated={refetch} />}
      {mappingTarget && <MappingModal templateId={mappingTarget.id} verticalKey={mappingTarget.vertical_key} onClose={() => setMappingTarget(null)} onSaved={refetch} />}
      {simulateTarget && <SimulatorModal template={simulateTarget} onClose={() => setSimulateTarget(null)} />}
      {publishTarget && <PublishDialog template={publishTarget} onClose={() => setPublishTarget(null)} onPublished={refetch} />}
    </div>
  );
}
