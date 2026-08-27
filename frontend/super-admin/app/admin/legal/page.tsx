"use client";
/**
 * Legal Documents — authoring console.
 *
 * The Terms of Service and Privacy Notice used to live as hardcoded JSX in
 * the tenant portal, so changing a clause meant a frontend deploy, no other
 * app could show them, and the consent ledger could not say which wording a
 * person had accepted. Everything is authored and published here now.
 *
 * Two rules the UI has to make obvious, because they are enforced server-side
 * and a surprise 409 is a bad way to learn them:
 *   1. A published version is immutable — corrections ship as a new version.
 *   2. Publishing with a future date SCHEDULES the change; the incumbent
 *      version stays live until that moment.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, Archive, Check, Clock, FileText, Plus, Send, Trash2, X,
} from "lucide-react";

import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Badge, Btn, Card, Input, SectionHeader, Select, Skeleton, Textarea,
} from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import {
  legalAdminApi, type LegalDocVersion, type LegalStatus,
} from "../../../lib/api-legal";

const PUBLIC_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATUS_TONE: Record<LegalStatus, "success" | "warning" | "muted"> = {
  published: "success",
  draft: "warning",
  archived: "muted",
};

function fmt(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/** A published row whose effective_at is still in the future is scheduled,
 *  not live — the list must not imply it is what people are reading. */
function isScheduled(v: LegalDocVersion): boolean {
  return v.status === "published"
    && !!v.effective_at
    && new Date(v.effective_at).getTime() > Date.now();
}

const emptyDraft = {
  doc_type: "terms_of_service",
  version: "",
  title: "",
  summary: "",
  body: "",
  audience: "all",
  locale: "en",
  requires_reacceptance: false,
  change_note: "",
};

export default function LegalDocumentsConsole() {
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [selected, setSelected] = useState<LegalDocVersion | null>(null);
  const [composing, setComposing] = useState(false);
  const [draft, setDraft] = useState({ ...emptyDraft });
  const [effectiveAt, setEffectiveAt] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const meta = useApi(useCallback(() => legalAdminApi.meta(), []));
  const list = useApi(
    useCallback(
      () => legalAdminApi.listVersions({ doc_type: filterType, status: filterStatus, limit: 100 }),
      [filterType, filterStatus],
    ),
    [filterType, filterStatus],
  );

  const versions = list.data?.versions ?? [];

  // Which version each document type is actually serving right now. Drives
  // the "Currently live" strip so an author can see the effect of a publish
  // without leaving the page.
  const liveByType = useMemo(() => {
    const out: Record<string, LegalDocVersion> = {};
    for (const v of versions) {
      if (v.status !== "published" || isScheduled(v)) continue;
      const prev = out[v.doc_type];
      if (!prev || (v.effective_at ?? "") > (prev.effective_at ?? "")) out[v.doc_type] = v;
    }
    return out;
  }, [versions]);

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(t);
  }, [notice]);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(true); setErr(null);
    try {
      await fn();
      setNotice(label);
      list.refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function openVersion(v: LegalDocVersion) {
    setErr(null);
    try {
      // The list omits bodies, so fetch the full row before showing the editor.
      setSelected(await legalAdminApi.getVersion(v.id));
      setComposing(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  function startDraft(fromVersion?: LegalDocVersion) {
    setSelected(null);
    setErr(null);
    setComposing(true);
    if (fromVersion) {
      // "New version from this" — the usual way a correction is made, since
      // a published version cannot be edited in place.
      setDraft({
        doc_type: fromVersion.doc_type,
        version: "",
        title: fromVersion.title,
        summary: fromVersion.summary ?? "",
        body: fromVersion.body ?? "",
        audience: fromVersion.audience,
        locale: fromVersion.locale,
        requires_reacceptance: false,
        change_note: "",
      });
    } else {
      setDraft({ ...emptyDraft });
    }
  }

  async function createDraft() {
    await run("Draft created", async () => {
      const created = await legalAdminApi.createDraft({
        doc_type: draft.doc_type,
        version: draft.version.trim(),
        title: draft.title.trim(),
        body: draft.body,
        summary: draft.summary.trim() || null,
        audience: draft.audience,
        locale: draft.locale,
        requires_reacceptance: draft.requires_reacceptance,
        change_note: draft.change_note.trim() || null,
      });
      setComposing(false);
      setSelected(created);
    });
  }

  async function saveDraft() {
    if (!selected) return;
    await run("Draft saved", async () => {
      const saved = await legalAdminApi.updateDraft(selected.id, {
        version: selected.version,
        title: selected.title,
        summary: selected.summary,
        body: selected.body,
        requires_reacceptance: selected.requires_reacceptance,
        change_note: selected.change_note,
      });
      setSelected(saved);
    });
  }

  async function publishSelected() {
    if (!selected) return;
    const when = effectiveAt ? new Date(effectiveAt).toISOString() : null;
    await run(when ? "Publication scheduled" : "Published", async () => {
      const published = await legalAdminApi.publish(selected.id, when);
      setSelected(published);
      setEffectiveAt("");
    });
  }

  const canEdit = selected?.status === "draft";

  return (
    <AdminLayout>
      <SectionHeader
        title="Legal Documents"
        subtitle="Author and publish the Terms, Privacy Notice and related policies. Every app reads them from here."
        actions={
          <Btn onClick={() => startDraft()} disabled={busy}>
            <Plus size={15} /> New draft
          </Btn>
        }
      />

      {err && (
        <Card padding={0} style={{ marginBottom: 14, borderColor: "var(--danger)" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: 12 }}>
            <AlertTriangle size={16} style={{ color: "var(--danger)", flexShrink: 0, marginTop: 2 }} />
            <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{err}</div>
            <button onClick={() => setErr(null)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer" }}>
              <X size={14} />
            </button>
          </div>
        </Card>
      )}
      {notice && (
        <Card padding={0} style={{ marginBottom: 14, borderColor: "var(--success)" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 12, fontSize: 13 }}>
            <Check size={16} style={{ color: "var(--success)" }} /> {notice}
          </div>
        </Card>
      )}

      {/* ── Currently live ─────────────────────────────────────────────── */}
      <Card padding={0} style={{ marginBottom: 16 }}>
        <div style={{ padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".04em", color: "var(--text-tertiary)", marginBottom: 10 }}>
            Currently in force
          </div>
          {meta.loading || list.loading ? (
            <Skeleton />
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {(meta.data?.doc_types ?? []).map(dt => {
                const live = liveByType[dt.value];
                return (
                  <div key={dt.value} style={{
                    border: "1px solid var(--border)", borderRadius: 10,
                    padding: "10px 13px", minWidth: 210, background: "var(--surface-sunken)",
                  }}>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{dt.label}</div>
                    {live ? (
                      <>
                        <div style={{ fontSize: 14, fontWeight: 600, marginTop: 3 }}>
                          v{live.version}
                        </div>
                        <a href={`${PUBLIC_BASE}/v1/public/legal/${dt.value}`}
                           target="_blank" rel="noreferrer"
                           style={{ fontSize: 11, color: "var(--brand)", textDecoration: "none" }}>
                          view public JSON →
                        </a>
                      </>
                    ) : (
                      <div style={{ fontSize: 13, color: "var(--warning)", marginTop: 3 }}>
                        Not published
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 420px) minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
        {/* ── Version list ─────────────────────────────────────────────── */}
        <Card padding={0}>
          <div style={{ padding: 12, display: "flex", gap: 8, borderBottom: "1px solid var(--border)" }}>
            <Select
              value={filterType}
              onChange={setFilterType}
              placeholder="All documents"
              options={(meta.data?.doc_types ?? []).map(d => ({ value: d.value, label: d.label }))}
            />
            <Select
              value={filterStatus}
              onChange={setFilterStatus}
              placeholder="All statuses"
              options={(meta.data?.statuses ?? []).map(st => ({ value: st, label: st }))}
            />
          </div>

          <div style={{ maxHeight: 560, overflowY: "auto" }}>
            {list.loading && <div style={{ padding: 14 }}><Skeleton /></div>}
            {!list.loading && versions.length === 0 && (
              <div style={{ padding: 26, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                No versions match these filters.
              </div>
            )}
            {versions.map(v => (
              <button
                key={v.id}
                onClick={() => openVersion(v)}
                style={{
                  display: "block", width: "100%", textAlign: "left", cursor: "pointer",
                  padding: "11px 14px", border: "none",
                  borderBottom: "1px solid var(--border)",
                  background: selected?.id === v.id ? "var(--surface-sunken)" : "transparent",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileText size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{v.doc_type_label}</span>
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>v{v.version}</span>
                  <span style={{ marginLeft: "auto", display: "flex", gap: 5 }}>
                    {isScheduled(v) && (
                      <Badge tone="warning"><Clock size={10} /> scheduled</Badge>
                    )}
                    <Badge tone={STATUS_TONE[v.status]}>{v.status}</Badge>
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4, paddingLeft: 22 }}>
                  {v.audience} · {v.locale} · effective {fmt(v.effective_at)}
                </div>
              </button>
            ))}
          </div>
        </Card>

        {/* ── Editor ───────────────────────────────────────────────────── */}
        <Card padding={0}>
          {composing ? (
            <div style={{ padding: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>New draft</div>
              <div style={{ display: "grid", gap: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                  <Select
                    label="Document"
                    value={draft.doc_type}
                    onChange={v => setDraft({ ...draft, doc_type: v })}
                    options={(meta.data?.doc_types ?? []).map(d => ({ value: d.value, label: d.label }))}
                  />
                  <Select
                    label="Audience"
                    value={draft.audience}
                    onChange={v => setDraft({ ...draft, audience: v })}
                    options={(meta.data?.audiences ?? ["all"]).map(a => ({ value: a, label: a }))}
                  />
                  <Input label="Version" value={draft.version} placeholder="1.1"
                         onChange={v => setDraft({ ...draft, version: v })} />
                </div>
                <Input label="Title" value={draft.title} placeholder="Terms of Service"
                       onChange={v => setDraft({ ...draft, title: v })} />
                <Input label="Summary" value={draft.summary}
                       placeholder="One line shown above the document."
                       onChange={v => setDraft({ ...draft, summary: v })} />
                <Textarea label="Body (Markdown)" rows={16} value={draft.body}
                          onChange={v => setDraft({ ...draft, body: v })} />
                <Input label="Change note (internal)" value={draft.change_note}
                       onChange={v => setDraft({ ...draft, change_note: v })} />
                <label style={{ fontSize: 12, display: "flex", gap: 8, alignItems: "center" }}>
                  <input type="checkbox" checked={draft.requires_reacceptance}
                         onChange={e => setDraft({ ...draft, requires_reacceptance: e.target.checked })} />
                  Existing users must re-accept this version
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <Btn onClick={createDraft}
                       disabled={busy || !draft.version.trim() || !draft.title.trim() || !draft.body.trim()}>
                    Create draft
                  </Btn>
                  <Btn variant="secondary" onClick={() => setComposing(false)} disabled={busy}>Cancel</Btn>
                </div>
              </div>
            </div>
          ) : selected ? (
            <div style={{ padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <div style={{ fontSize: 15, fontWeight: 700 }}>
                  {selected.doc_type_label} · v{selected.version}
                </div>
                <Badge tone={STATUS_TONE[selected.status]}>{selected.status}</Badge>
                {isScheduled(selected) && <Badge tone="warning"><Clock size={10} /> scheduled</Badge>}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 14 }}>
                {selected.audience} · {selected.locale} · created {fmt(selected.created_at)}
                {selected.published_at ? ` · published ${fmt(selected.published_at)}` : ""}
              </div>

              {!canEdit && (
                <div style={{
                  display: "flex", gap: 9, alignItems: "flex-start", padding: 11,
                  borderRadius: 8, background: "var(--surface-sunken)",
                  border: "1px solid var(--border)", marginBottom: 14, fontSize: 12,
                  color: "var(--text-secondary)", lineHeight: 1.55,
                }}>
                  <AlertTriangle size={14} style={{ color: "var(--warning)", flexShrink: 0, marginTop: 1 }} />
                  <span>
                    This version is {selected.status} and cannot be edited — people have
                    accepted this exact text and rewriting it would break the consent
                    record. Publish a corrected version instead.
                  </span>
                </div>
              )}

              <div style={{ display: "grid", gap: 12 }}>
                <Input label="Title" value={selected.title} disabled={!canEdit}
                       onChange={v => setSelected({ ...selected, title: v })} />
                <Input label="Summary" value={selected.summary ?? ""} disabled={!canEdit}
                       onChange={v => setSelected({ ...selected, summary: v })} />
                <Textarea label="Body (Markdown)" rows={18} value={selected.body ?? ""} disabled={!canEdit}
                          onChange={v => setSelected({ ...selected, body: v })} />
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14, alignItems: "center" }}>
                {canEdit && (
                  <>
                    <Btn onClick={saveDraft} disabled={busy}>Save draft</Btn>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <Input type="datetime-local" value={effectiveAt}
                             onChange={setEffectiveAt} />
                      <Btn onClick={publishSelected} disabled={busy}>
                        <Send size={14} /> {effectiveAt ? "Schedule" : "Publish now"}
                      </Btn>
                    </div>
                    <Btn variant="danger" onClick={() => run("Draft deleted", async () => {
                      await legalAdminApi.deleteDraft(selected.id);
                      setSelected(null);
                    })} disabled={busy}>
                      <Trash2 size={14} /> Delete draft
                    </Btn>
                  </>
                )}
                {selected.status === "published" && (
                  <>
                    <Btn variant="secondary" onClick={() => startDraft(selected)} disabled={busy}>
                      <Plus size={14} /> New version from this
                    </Btn>
                    <Btn variant="secondary" onClick={() => run("Archived", async () => {
                      const r = await legalAdminApi.archive(selected.id);
                      setSelected(r);
                    })} disabled={busy}>
                      <Archive size={14} /> Archive
                    </Btn>
                  </>
                )}
                {selected.status === "archived" && (
                  <Btn variant="secondary" onClick={() => startDraft(selected)} disabled={busy}>
                    <Plus size={14} /> New version from this
                  </Btn>
                )}
              </div>

              {canEdit && (
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10, lineHeight: 1.6 }}>
                  Leave the date empty to publish immediately, which archives the version
                  currently in force. Setting a future date schedules the change and leaves
                  the current version live until then.
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
              Select a version to read or edit it, or create a new draft.
            </div>
          )}
        </Card>
      </div>
    </AdminLayout>
  );
}
