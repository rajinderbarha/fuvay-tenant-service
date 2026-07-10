'use client'
import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AdminLayout } from '../../../../../components/layout/AdminLayout'
import { Badge, Btn } from '../../../../../components/shared/ui'
import { kbApi } from '../../../../../lib/api'
import { useApi, useAction } from '../../../../../hooks/useApi'

// ── Types ─────────────────────────────────────────────────────────────────────
type TabId =
  | 'overview' | 'documents' | 'articles' | 'chunks'
  | 'query-logs' | 'retrieval-quality' | 'access-rules'
  | 'rag-settings' | 'safety-rules' | 'audit-logs'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview',          label: 'Overview' },
  { id: 'documents',         label: 'Documents' },
  { id: 'articles',          label: 'Manual Articles' },
  { id: 'chunks',            label: 'Chunks & Indexing' },
  { id: 'query-logs',        label: 'Query Logs' },
  { id: 'retrieval-quality', label: 'Retrieval Quality' },
  { id: 'access-rules',      label: 'Access Rules' },
  { id: 'rag-settings',      label: 'RAG Settings' },
  { id: 'safety-rules',      label: 'Safety Rules' },
  { id: 'audit-logs',        label: 'Audit Logs' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────
const safeVal = (v: unknown, suffix = ''): string => {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return isNaN(n) ? String(v) : `${n}${suffix}`
}
const fmt = (v: unknown): string => {
  if (!v) return '—'
  try { return new Date(String(v)).toLocaleString('en-IN') } catch { return String(v) }
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 18px' }}>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

function EmptyState({ msg }: { msg: string }) {
  return (
    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
      {msg}
    </div>
  )
}

function TableHead({ cols }: { cols: string[] }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: `repeat(${cols.length}, 1fr)`,
      gap: 6, padding: '8px 14px',
      background: 'var(--surface-sunken)', borderBottom: '1px solid var(--border)',
      fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase',
    }}>
      {cols.map(c => <div key={c}>{c}</div>)}
    </div>
  )
}

function Chip({ label, color }: { label: string; color?: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 12,
      fontSize: 11, fontWeight: 500,
      background: color ?? 'var(--surface-sunken)',
      border: '1px solid var(--border)', color: 'var(--text-secondary)',
      marginRight: 4, marginBottom: 4,
    }}>{label}</span>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function KBDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = String(params.id)

  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [toast, setToast] = useState('')
  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000) }

  // ── KB fetch ─────────────────────────────────────────────────────────────
  const { data: kbRaw, loading: kbLoading } = useApi(() => kbApi.get(id), [id])
  const kb = (kbRaw as { data?: Record<string, unknown> } | Record<string, unknown> | null)

  function getField(field: string): unknown {
    if (!kb) return undefined
    if ('data' in (kb as Record<string, unknown>) && (kb as Record<string, unknown>).data) {
      return ((kb as Record<string, unknown>).data as Record<string, unknown>)[field]
    }
    return (kb as Record<string, unknown>)[field]
  }

  // ── Tab data ──────────────────────────────────────────────────────────────
  const { data: docsRaw, loading: docsLoading, refetch: refetchDocs } = useApi(
    () => activeTab === 'documents' ? kbApi.listDocuments(id) : Promise.resolve(null), [activeTab]
  )
  const { data: articlesRaw, loading: articlesLoading, refetch: refetchArticles } = useApi(
    () => activeTab === 'articles' ? kbApi.listArticles(id) : Promise.resolve(null), [activeTab]
  )
  const { data: chunksRaw, loading: chunksLoading } = useApi(
    () => activeTab === 'chunks' ? kbApi.listChunks(id) : Promise.resolve(null), [activeTab]
  )
  const { data: jobsRaw, loading: jobsLoading, refetch: refetchJobs } = useApi(
    () => activeTab === 'chunks' ? kbApi.listIndexingJobs(id) : Promise.resolve(null), [activeTab]
  )
  const { data: logsRaw, loading: logsLoading } = useApi(
    () => activeTab === 'query-logs' ? kbApi.listQueryLogs(id) : Promise.resolve(null), [activeTab]
  )
  const { data: qualityRaw, loading: qualityLoading } = useApi(
    () => activeTab === 'retrieval-quality' ? kbApi.getRetrievalQuality(id) : Promise.resolve(null), [activeTab]
  )
  const { data: auditRaw, loading: auditLoading } = useApi(
    () => activeTab === 'audit-logs' ? kbApi.getAuditLogs(id) : Promise.resolve(null), [activeTab]
  )

  // ── Actions ───────────────────────────────────────────────────────────────
  const { execute: doActivate, loading: activating } = useAction(async () => {
    await kbApi.activate(id); notify('KB activated')
  })
  const { execute: doDisable } = useAction(async () => {
    await kbApi.disable(id); notify('KB disabled')
  })
  const { execute: doReindex, loading: reindexing } = useAction(async () => {
    await kbApi.triggerReindex(id); refetchJobs(); notify('Reindex job queued')
  })
  const { execute: doPublishArticle } = useAction(async (articleId: string) => {
    await kbApi.publishArticle(id, articleId); refetchArticles(); notify('Article published')
  })
  const { execute: doDeleteDoc } = useAction(async (docId: string) => {
    await kbApi.deleteDocument(id, docId); refetchDocs(); notify('Document deleted')
  })

  // ── Upload / Create modals (inline state) ─────────────────────────────────
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadForm, setUploadForm] = useState({ document_name: '', source_type: 'uploaded', file_type: '' })
  const { execute: doUpload, loading: uploading } = useAction(async () => {
    await kbApi.uploadDocument(id, uploadForm); setUploadOpen(false); refetchDocs(); notify('Document uploaded')
  })

  const [articleOpen, setArticleOpen] = useState(false)
  const [articleForm, setArticleForm] = useState({ article_title: '', article_slug: '', body_markdown: '', visibility: 'internal', status: 'draft' })
  const { execute: doCreateArticle, loading: creatingArticle } = useAction(async () => {
    await kbApi.createArticle(id, articleForm); setArticleOpen(false); refetchArticles(); notify('Article created')
  })

  const [queryText, setQueryText] = useState('')
  const [queryScope, setQueryScope] = useState('admin_app')
  const [queryResult, setQueryResult] = useState<Record<string, unknown> | null>(null)
  const { execute: doQuery, loading: querying } = useAction(async () => {
    const r = await kbApi.testQuery(id, queryText, queryScope)
    setQueryResult(r as Record<string, unknown>)
  })

  const [previewRole, setPreviewRole] = useState('customer')
  const [previewApp, setPreviewApp] = useState('customer_app')
  const [previewResult, setPreviewResult] = useState<Record<string, unknown> | null>(null)
  const { execute: doPreview } = useAction(async () => {
    const r = await kbApi.previewAccess(id, previewRole, previewApp)
    setPreviewResult(r as unknown as Record<string, unknown>)
  })

  // ── RAG Settings edit ─────────────────────────────────────────────────────
  const [editingRag, setEditingRag] = useState(false)
  const [ragForm, setRagForm] = useState<Record<string, unknown>>({})
  const { execute: doSaveRag, loading: savingRag } = useAction(async () => {
    await kbApi.update(id, ragForm); setEditingRag(false); notify('RAG settings saved')
  })

  // ── Status badge helper ───────────────────────────────────────────────────
  const status = String(getField('status') ?? '')
  const indexingStatus = String(getField('indexing_status') ?? '')

  if (kbLoading) {
    return (
      <AdminLayout>
        <div style={{ padding: 32 }}>
          <div className="skeleton" style={{ height: 40, width: 300, borderRadius: 8 }} />
        </div>
      </AdminLayout>
    )
  }

  return (
    <AdminLayout>
      <div style={{ maxWidth: 1400, margin: '0 auto', padding: '24px 24px' }}>
        {toast && (
          <div style={{ padding: '8px 14px', background: 'var(--success-bg)', border: '1px solid var(--success-border)', borderRadius: 8, color: 'var(--success-text)', fontSize: 12, marginBottom: 14 }}>
            ✓ {toast}
          </div>
        )}

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
          <button
            onClick={() => router.push('/admin/intelligence')}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--brand)', fontSize: 13, padding: 0, marginTop: 4 }}
          >
            ← Intelligence
          </button>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                {String(getField('name') ?? 'Knowledge Base')}
              </h1>
              {getField('kb_code') && (
                <span style={{ fontFamily: 'monospace', fontSize: 12, padding: '2px 8px', background: 'var(--surface-sunken)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-tertiary)' }}>
                  {String(getField('kb_code'))}
                </span>
              )}
              <Badge variant={status === 'active' ? 'success' : status === 'draft' ? 'muted' : 'warning'} size="sm">{status || '—'}</Badge>
              <Badge variant={indexingStatus === 'indexed' ? 'success' : 'muted'} size="sm">{indexingStatus || 'not_indexed'}</Badge>
            </div>
            {getField('description') && (
              <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>{String(getField('description'))}</p>
            )}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {status !== 'active' && <Btn size="sm" variant="primary" loading={activating} onClick={() => doActivate()}>Activate</Btn>}
            {status === 'active' && <Btn size="sm" variant="ghost" onClick={() => doDisable()}>Disable</Btn>}
          </div>
        </div>

        {/* ── Tab Bar ────────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20, overflowX: 'auto' }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '10px 16px', whiteSpace: 'nowrap', fontSize: 13,
                fontWeight: activeTab === t.id ? 600 : 400,
                color: activeTab === t.id ? 'var(--brand)' : 'var(--text-secondary)',
                borderBottom: activeTab === t.id ? '2px solid var(--brand)' : '2px solid transparent',
                marginBottom: -1,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Tab Content ─────────────────────────────────────────────────── */}

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
              <MetricCard label="Documents" value={0} />
              <MetricCard label="Chunks" value={0} />
              <MetricCard label="Total Queries" value={0} />
              <MetricCard label="Avg Latency" value="— ms" />
              <MetricCard label="Last Indexed" value={fmt(getField('last_indexed_at_kb'))} />
              <MetricCard label="Status" value={status || '—'} />
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 14px' }}>Settings Summary</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                {[
                  ['Scope', getField('scope_type')],
                  ['Knowledge Type', getField('knowledge_type')],
                  ['Owner Team', getField('owner_team')],
                  ['Embedding Model', getField('embedding_model')],
                  ['Chunk Size', getField('chunk_size')],
                  ['Retrieval Top K', getField('retrieval_top_k')],
                  ['Similarity Threshold', getField('similarity_threshold')],
                  ['Customer Visible', getField('customer_visible') ? 'Yes' : 'No'],
                  ['Admin Only', getField('admin_only') ? 'Yes' : 'No'],
                  ['RAG Enabled', getField('rag_enabled') ? 'Yes' : 'No'],
                  ['Citations Required', getField('citations_required') ? 'Yes' : 'No'],
                  ['Auto Reindex', getField('auto_reindex') ? 'Yes' : 'No'],
                ].map(([label, val]) => (
                  <div key={String(label)} style={{ padding: '10px 14px', background: 'var(--surface-sunken)', borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>{String(label)}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{safeVal(val)}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6 }}>Allowed Apps</div>
                {((getField('allowed_apps_json') as string[]) ?? []).map((a: string) => <Chip key={a} label={a} />)}
                {!((getField('allowed_apps_json') as string[])?.length) && <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>None configured</span>}
              </div>
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6 }}>Allowed Roles</div>
                {((getField('allowed_roles_json') as string[]) ?? []).map((r: string) => <Chip key={r} label={r} />)}
                {!((getField('allowed_roles_json') as string[])?.length) && <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>None configured</span>}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Documents */}
        {activeTab === 'documents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Btn size="sm" variant="primary" onClick={() => setUploadOpen(true)}>+ Upload Document</Btn>
            </div>

            {uploadOpen && (
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 14px' }}>Upload Document</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Document Name *</label>
                    <input
                      value={uploadForm.document_name}
                      onChange={e => setUploadForm(p => ({ ...p, document_name: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)', boxSizing: 'border-box' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Source Type</label>
                    <select
                      value={uploadForm.source_type}
                      onChange={e => setUploadForm(p => ({ ...p, source_type: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}
                    >
                      <option value="uploaded">Uploaded</option>
                      <option value="url">URL</option>
                      <option value="media">Media Library</option>
                      <option value="catalog_sync">Catalog Sync</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>File Type</label>
                    <select
                      value={uploadForm.file_type}
                      onChange={e => setUploadForm(p => ({ ...p, file_type: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}
                    >
                      <option value="">— None —</option>
                      <option value="pdf">PDF</option>
                      <option value="docx">DOCX</option>
                      <option value="txt">TXT</option>
                      <option value="html">HTML</option>
                      <option value="md">Markdown</option>
                    </select>
                  </div>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-tertiary)', margin: '8px 0 14px' }}>
                  Note: Actual file upload requires storage integration. This creates a document record for tracking.
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Btn size="sm" variant="ghost" onClick={() => setUploadOpen(false)}>Cancel</Btn>
                  <Btn size="sm" variant="primary" loading={uploading} onClick={() => doUpload()}>Upload</Btn>
                </div>
              </div>
            )}

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              {docsLoading ? (
                <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 120, borderRadius: 6 }} /></div>
              ) : !((docsRaw as { data?: unknown[] } | unknown[] | null)) || (Array.isArray(docsRaw) ? docsRaw.length === 0 : !((docsRaw as { data?: unknown[] })?.data?.length)) ? (
                <EmptyState msg="No documents uploaded yet. Upload or link documents to start indexing." />
              ) : (
                <>
                  <TableHead cols={['Document Name', 'Source', 'File Type', 'Chunks', 'Indexing Status', 'Created', 'Actions']} />
                  {(Array.isArray(docsRaw) ? docsRaw : ((docsRaw as { data?: Record<string, unknown>[] })?.data ?? [])).map((doc: Record<string, unknown>) => (
                    <div key={String(doc.id)} style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 }}>
                      <div style={{ fontWeight: 500 }}>{String(doc.document_name ?? '—')}</div>
                      <div style={{ color: 'var(--text-secondary)' }}>{String(doc.source_type ?? '—')}</div>
                      <div style={{ color: 'var(--text-secondary)' }}>{String(doc.file_type ?? '—')}</div>
                      <div>{String(doc.chunk_count ?? 0)}</div>
                      <Badge variant={doc.indexing_status === 'indexed' ? 'success' : 'muted'} size="sm">{String(doc.indexing_status ?? '—')}</Badge>
                      <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{fmt(doc.created_at)}</div>
                      <Btn size="xs" variant="danger" onClick={() => doDeleteDoc(String(doc.id))}>Delete</Btn>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Manual Articles */}
        {activeTab === 'articles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Btn size="sm" variant="primary" onClick={() => setArticleOpen(true)}>+ Create Article</Btn>
            </div>

            {articleOpen && (
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 14px' }}>Create Article</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Title *</label>
                    <input
                      value={articleForm.article_title}
                      onChange={e => {
                        const t = e.target.value
                        const slug = t.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
                        setArticleForm(p => ({ ...p, article_title: t, article_slug: slug }))
                      }}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)', boxSizing: 'border-box' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Slug</label>
                    <input
                      value={articleForm.article_slug}
                      onChange={e => setArticleForm(p => ({ ...p, article_slug: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)', boxSizing: 'border-box', fontFamily: 'monospace' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Body (Markdown)</label>
                    <textarea
                      value={articleForm.body_markdown}
                      onChange={e => setArticleForm(p => ({ ...p, body_markdown: e.target.value }))}
                      rows={6}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)', boxSizing: 'border-box', resize: 'vertical', fontFamily: 'monospace' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div>
                      <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Visibility</label>
                      <select value={articleForm.visibility} onChange={e => setArticleForm(p => ({ ...p, visibility: e.target.value }))}
                        style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}>
                        <option value="internal">Internal</option>
                        <option value="admin_only">Admin Only</option>
                        <option value="public">Public</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Status</label>
                      <select value={articleForm.status} onChange={e => setArticleForm(p => ({ ...p, status: e.target.value }))}
                        style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}>
                        <option value="draft">Draft</option>
                        <option value="published">Published</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                  <Btn size="sm" variant="ghost" onClick={() => setArticleOpen(false)}>Cancel</Btn>
                  <Btn size="sm" variant="primary" loading={creatingArticle} onClick={() => doCreateArticle()}>Create</Btn>
                </div>
              </div>
            )}

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              {articlesLoading ? (
                <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 120, borderRadius: 6 }} /></div>
              ) : (
                (() => {
                  const arts = Array.isArray(articlesRaw) ? articlesRaw : ((articlesRaw as { data?: Record<string, unknown>[] })?.data ?? [])
                  if (!arts.length) return <EmptyState msg="No articles yet. Create a manual article to add knowledge." />
                  return <>
                    <TableHead cols={['Title', 'Slug', 'Status', 'Visibility', 'Created', 'Published At', 'Actions']} />
                    {(arts as Record<string, unknown>[]).map(a => (
                      <div key={String(a.id)} style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 }}>
                        <div style={{ fontWeight: 500 }}>{String(a.article_title ?? '—')}</div>
                        <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-tertiary)' }}>{String(a.article_slug ?? '—')}</div>
                        <Badge variant={a.status === 'published' ? 'success' : 'muted'} size="sm">{String(a.status ?? '—')}</Badge>
                        <div style={{ color: 'var(--text-secondary)' }}>{String(a.visibility ?? '—')}</div>
                        <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{fmt(a.created_at)}</div>
                        <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{a.published_at ? fmt(a.published_at) : '—'}</div>
                        <div style={{ display: 'flex', gap: 4 }}>
                          {a.status !== 'published' && <Btn size="xs" variant="secondary" onClick={() => doPublishArticle(String(a.id))}>Publish</Btn>}
                        </div>
                      </div>
                    ))}
                  </>
                })()
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Chunks & Indexing */}
        {activeTab === 'chunks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Indexing Jobs */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Indexing Jobs</h3>
                <Btn size="sm" variant="secondary" loading={reindexing} onClick={() => doReindex()}>Reindex</Btn>
              </div>
              {jobsLoading ? (
                <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 80, borderRadius: 6 }} /></div>
              ) : (
                (() => {
                  const jobs = Array.isArray(jobsRaw) ? jobsRaw : ((jobsRaw as { data?: Record<string, unknown>[] })?.data ?? [])
                  if (!jobs.length) return <EmptyState msg="No indexing jobs yet." />
                  return <>
                    <TableHead cols={['Job Type', 'Status', 'Docs', 'Chunks', 'Failed', 'Started', 'Completed']} />
                    {(jobs as Record<string, unknown>[]).map(j => (
                      <div key={String(j.id)} style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 }}>
                        <div style={{ fontFamily: 'monospace', fontSize: 11 }}>{String(j.job_type ?? '—')}</div>
                        <Badge variant={j.status === 'completed' ? 'success' : j.status === 'failed' ? 'danger' : 'muted'} size="sm">{String(j.status ?? '—')}</Badge>
                        <div>{String(j.documents_processed ?? 0)}</div>
                        <div>{String(j.chunks_created ?? 0)}</div>
                        <div style={{ color: Number(j.failed_count) > 0 ? 'var(--danger)' : undefined }}>{String(j.failed_count ?? 0)}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{fmt(j.started_at)}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{fmt(j.completed_at)}</div>
                      </div>
                    ))}
                  </>
                })()
              )}
            </div>

            {/* Chunks */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Chunks</h3>
              </div>
              {chunksLoading ? (
                <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 80, borderRadius: 6 }} /></div>
              ) : (
                (() => {
                  const items = (chunksRaw as { data?: { items?: Record<string, unknown>[] }; items?: Record<string, unknown>[] } | null)
                  const chunks = items?.data?.items ?? items?.items ?? []
                  if (!chunks.length) return <EmptyState msg="No chunks yet. Trigger indexing to generate chunks from documents." />
                  return <>
                    <TableHead cols={['Index', 'Source', 'Preview', 'Tokens', 'Status']} />
                    {chunks.map((c: Record<string, unknown>) => (
                      <div key={String(c.id)} style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 }}>
                        <div style={{ fontFamily: 'monospace', fontSize: 11 }}>{String(c.chunk_index ?? 0)}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{c.document_id ? 'doc' : c.article_id ? 'article' : '—'}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {String(c.chunk_text ?? '').slice(0, 80)}{String(c.chunk_text ?? '').length > 80 ? '…' : ''}
                        </div>
                        <div>{String(c.token_count ?? 0)}</div>
                        <Badge variant={c.embedding_status === 'done' ? 'success' : 'muted'} size="sm">{String(c.embedding_status ?? '—')}</Badge>
                      </div>
                    ))}
                  </>
                })()
              )}
            </div>
          </div>
        )}

        {/* Tab 5: Query Logs */}
        {activeTab === 'query-logs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Test Query Panel */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 14px' }}>Test Query</h3>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  value={queryText}
                  onChange={e => setQueryText(e.target.value)}
                  placeholder="Enter test query…"
                  style={{ flex: 1, minWidth: 200, padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}
                />
                <select
                  value={queryScope}
                  onChange={e => setQueryScope(e.target.value)}
                  style={{ padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}
                >
                  <option value="admin_app">Admin App</option>
                  <option value="tenant_app">Tenant App</option>
                  <option value="customer_app">Customer App</option>
                  <option value="staff_app">Staff App</option>
                </select>
                <Btn size="sm" variant="primary" loading={querying} onClick={() => doQuery()}>Run Query</Btn>
              </div>
              {queryResult && (
                <div style={{ marginTop: 14, padding: 14, background: 'var(--surface-sunken)', borderRadius: 8, fontSize: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                    <div><span style={{ color: 'var(--text-tertiary)' }}>Retrieved Chunks:</span> {String((queryResult as Record<string, unknown>).retrieved_chunks ? ((queryResult as Record<string, unknown>).retrieved_chunks as unknown[]).length : 0)}</div>
                    <div><span style={{ color: 'var(--text-tertiary)' }}>Latency:</span> {String((queryResult as Record<string, unknown>).latency_ms ?? '—')}ms</div>
                    <div><span style={{ color: 'var(--text-tertiary)' }}>Answer Status:</span> {String((queryResult as Record<string, unknown>).answer_status ?? '—')}</div>
                    <div><span style={{ color: 'var(--text-tertiary)' }}>Citations:</span> {String(((queryResult as Record<string, unknown>).citations as unknown[])?.length ?? 0)}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Query Logs Table */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              {logsLoading ? (
                <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 100, borderRadius: 6 }} /></div>
              ) : (
                (() => {
                  const logs = (logsRaw as { data?: { items?: Record<string, unknown>[] }; items?: Record<string, unknown>[] } | null)
                  const items = logs?.data?.items ?? logs?.items ?? []
                  if (!items.length) return <EmptyState msg="No queries yet. Run test queries to see logs." />
                  return <>
                    <TableHead cols={['Time', 'App', 'Query', 'Retrieved', 'Latency', 'Status']} />
                    {items.map((log: Record<string, unknown>) => (
                      <div key={String(log.id)} style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 }}>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{fmt(log.created_at)}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{String(log.app_scope ?? '—')}</div>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(log.query_text ?? '—')}</div>
                        <div>{String(log.retrieved_chunks_count ?? 0)}</div>
                        <div>{log.latency_ms != null ? `${log.latency_ms}ms` : '—'}</div>
                        <Badge variant={log.answer_status === 'answered' ? 'success' : 'muted'} size="sm">{String(log.answer_status ?? '—')}</Badge>
                      </div>
                    ))}
                  </>
                })()
              )}
            </div>
          </div>
        )}

        {/* Tab 6: Retrieval Quality */}
        {activeTab === 'retrieval-quality' && (
          (() => {
            const q = (qualityRaw as { data?: Record<string, unknown> } | Record<string, unknown> | null)
            const qd: Record<string, unknown> = (q && 'data' in (q as Record<string, unknown>) ? (q as Record<string, unknown>).data : q) as Record<string, unknown> ?? {}
            const total = Number(qd.total_queries ?? 0)
            if (!qualityLoading && total === 0) {
              return <EmptyState msg="No query data yet. Run test queries to see quality metrics." />
            }
            return (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                <MetricCard label="Total Queries" value={total} />
                <MetricCard label="Helpful Rate" value={qd.helpful_rate != null ? `${(qd.helpful_rate as number).toFixed(1)}%` : '—'} />
                <MetricCard label="No Answer Rate" value={qd.no_answer_rate != null ? `${(qd.no_answer_rate as number).toFixed(1)}%` : '—'} />
                <MetricCard label="Avg Latency" value={qd.avg_latency_ms != null ? `${(qd.avg_latency_ms as number).toFixed(0)}ms` : '—'} />
                <MetricCard label="Flagged" value={String(qd.flagged_count ?? 0)} />
              </div>
            )
          })()
        )}

        {/* Tab 7: Access Rules */}
        {activeTab === 'access-rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px' }}>Allowed Apps</h3>
              <div>
                {((getField('allowed_apps_json') as string[]) ?? []).map((a: string) => <Chip key={a} label={a} />)}
                {!((getField('allowed_apps_json') as string[])?.length) && <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>None configured</span>}
              </div>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '16px 0 12px' }}>Allowed Roles</h3>
              <div>
                {((getField('allowed_roles_json') as string[]) ?? []).map((r: string) => <Chip key={r} label={r} />)}
                {!((getField('allowed_roles_json') as string[])?.length) && <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>None configured</span>}
              </div>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '16px 0 12px' }}>Visibility Settings</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Badge variant={getField('customer_visible') ? 'success' : 'muted'} size="sm">Customer Visible: {getField('customer_visible') ? 'Yes' : 'No'}</Badge>
                <Badge variant={getField('tenant_visible') ? 'success' : 'muted'} size="sm">Tenant Visible: {getField('tenant_visible') ? 'Yes' : 'No'}</Badge>
                <Badge variant={getField('staff_visible') ? 'success' : 'muted'} size="sm">Staff Visible: {getField('staff_visible') ? 'Yes' : 'No'}</Badge>
                <Badge variant={getField('admin_only') ? 'info' : 'muted'} size="sm">Admin Only: {getField('admin_only') ? 'Yes' : 'No'}</Badge>
                <Badge variant={getField('sensitive_content') ? 'warning' : 'muted'} size="sm">Sensitive: {getField('sensitive_content') ? 'Yes' : 'No'}</Badge>
              </div>
            </div>

            {/* Preview Access Panel */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 14px' }}>Preview Access</h3>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <select value={previewRole} onChange={e => setPreviewRole(e.target.value)}
                  style={{ padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}>
                  <option value="customer">Customer</option>
                  <option value="technician">Technician</option>
                  <option value="tenant_owner">Tenant Owner</option>
                  <option value="platform_admin">Platform Admin</option>
                  <option value="super_admin">Super Admin</option>
                  <option value="compliance_officer">Compliance Officer</option>
                </select>
                <select value={previewApp} onChange={e => setPreviewApp(e.target.value)}
                  style={{ padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)' }}>
                  <option value="admin_app">Admin App</option>
                  <option value="tenant_app">Tenant App</option>
                  <option value="customer_app">Customer App</option>
                  <option value="staff_app">Staff App</option>
                </select>
                <Btn size="sm" variant="secondary" onClick={() => doPreview()}>Preview</Btn>
              </div>
              {previewResult && (
                <div style={{ marginTop: 14, padding: 14, background: 'var(--surface-sunken)', borderRadius: 8, fontSize: 13 }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Badge variant={(previewResult as Record<string, unknown>).can_access ? 'success' : 'danger'} size="sm">
                      {(previewResult as Record<string, unknown>).can_access ? 'YES' : 'NO'}
                    </Badge>
                    <span style={{ color: 'var(--text-secondary)' }}>{String((previewResult as Record<string, unknown>).reason ?? '')}</span>
                    {(previewResult as Record<string, unknown>).blocked_by && (
                      <span style={{ fontSize: 11, color: 'var(--danger)' }}>Blocked by: {String((previewResult as Record<string, unknown>).blocked_by)}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 8: RAG Settings */}
        {activeTab === 'rag-settings' && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>RAG Configuration</h3>
              {!editingRag
                ? <Btn size="sm" variant="secondary" onClick={() => {
                    setRagForm({
                      rag_enabled: getField('rag_enabled'),
                      embedding_model: getField('embedding_model'),
                      chunk_size: getField('chunk_size'),
                      chunk_overlap: getField('chunk_overlap'),
                      retrieval_top_k: getField('retrieval_top_k'),
                      similarity_threshold: getField('similarity_threshold'),
                      reranking_enabled: getField('reranking_enabled'),
                      citations_required: getField('citations_required'),
                      max_context_documents: getField('max_context_documents'),
                      fallback_message: getField('fallback_message'),
                    })
                    setEditingRag(true)
                  }}>Edit RAG Settings</Btn>
                : <div style={{ display: 'flex', gap: 8 }}>
                    <Btn size="sm" variant="ghost" onClick={() => setEditingRag(false)}>Cancel</Btn>
                    <Btn size="sm" variant="primary" loading={savingRag} onClick={() => doSaveRag()}>Save</Btn>
                  </div>
              }
            </div>
            {!editingRag ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                {[
                  ['RAG Enabled', getField('rag_enabled') ? 'Yes' : 'No'],
                  ['Embedding Model', getField('embedding_model')],
                  ['Chunk Size', getField('chunk_size')],
                  ['Chunk Overlap', getField('chunk_overlap')],
                  ['Retrieval Top K', getField('retrieval_top_k')],
                  ['Similarity Threshold', getField('similarity_threshold')],
                  ['Max Context Docs', getField('max_context_documents')],
                  ['Reranking', getField('reranking_enabled') ? 'Enabled' : 'Disabled'],
                  ['Citations Required', getField('citations_required') ? 'Yes' : 'No'],
                ].map(([label, val]) => (
                  <div key={String(label)} style={{ padding: '10px 14px', background: 'var(--surface-sunken)', borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>{String(label)}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{safeVal(val)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                {[
                  { key: 'embedding_model', label: 'Embedding Model', type: 'text' },
                  { key: 'chunk_size', label: 'Chunk Size', type: 'number' },
                  { key: 'chunk_overlap', label: 'Chunk Overlap', type: 'number' },
                  { key: 'retrieval_top_k', label: 'Retrieval Top K', type: 'number' },
                  { key: 'similarity_threshold', label: 'Similarity Threshold', type: 'number' },
                  { key: 'max_context_documents', label: 'Max Context Docs', type: 'number' },
                  { key: 'fallback_message', label: 'Fallback Message', type: 'text' },
                ].map(({ key, label, type }) => (
                  <div key={key}>
                    <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>{label}</label>
                    <input
                      type={type}
                      value={String(ragForm[key] ?? '')}
                      onChange={e => setRagForm(p => ({ ...p, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--text-primary)', boxSizing: 'border-box' }}
                    />
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 16, padding: 14, background: 'var(--surface-sunken)', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 6 }}>Fallback Message</div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                {String(getField('fallback_message') ?? 'I do not have enough verified information to answer this. Please contact ServiceOS support.')}
              </p>
            </div>
          </div>
        )}

        {/* Tab 9: Safety Rules */}
        {activeTab === 'safety-rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 14px' }}>Configured Safety Rules</h3>
              {(() => {
                const rules = (getField('safety_rules_json') as Record<string, boolean> | null) ?? {}
                const entries = Object.entries(rules)
                if (!entries.length) return <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>No custom safety rules configured.</p>
                return (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {entries.map(([k, v]) => (
                      <Badge key={k} variant={v ? 'success' : 'muted'} size="sm">{k.replace(/_/g, ' ')}: {v ? 'ON' : 'OFF'}</Badge>
                    ))}
                  </div>
                )
              })()}
            </div>
            <div style={{ background: 'var(--surface)', border: '2px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 6px' }}>Mandatory Guardrails</h3>
              <p style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: '0 0 14px' }}>These are always enforced regardless of KB configuration.</p>
              <ul style={{ margin: 0, padding: '0 0 0 18px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  'AI cannot decide price',
                  'AI cannot assign provider',
                  'AI cannot create booking by itself',
                  'AI cannot apply ServiceOS credit',
                  'AI cannot approve tenant',
                  'AI cannot change security deposit',
                  'AI cannot expose internal risk score to customer',
                  'AI cannot expose tenant private documents to other tenants',
                ].map(g => (
                  <li key={g} style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{g}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Tab 10: Audit Logs */}
        {activeTab === 'audit-logs' && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            {auditLoading ? (
              <div style={{ padding: 16 }}><div className="skeleton" style={{ height: 120, borderRadius: 6 }} /></div>
            ) : (
              (() => {
                const logs = Array.isArray(auditRaw) ? auditRaw : ((auditRaw as { data?: Record<string, unknown>[] })?.data ?? [])
                if (!logs.length) return <EmptyState msg="No audit logs yet." />
                return <>
                  <TableHead cols={['Time', 'Action', 'Actor', 'Details']} />
                  {(logs as Record<string, unknown>[]).map(log => (
                    <div key={String(log.id)} style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{fmt(log.created_at)}</div>
                      <Badge variant="muted" size="sm">{String(log.action_type ?? '—')}</Badge>
                      <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{String(log.actor_user_id ?? 'system')}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{log.reason ? String(log.reason) : '—'}</div>
                    </div>
                  ))}
                </>
              })()
            )}
          </div>
        )}
      </div>
    </AdminLayout>
  )
}
