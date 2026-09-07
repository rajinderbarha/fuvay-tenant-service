"use client";
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { Badge, Btn, Card, Modal, Skeleton } from "../shared/ui";
import { checklistCatalogApi, type ChecklistSectionRow } from "../../lib/api";
import { useAction, useApi } from "../../hooks/useApi";
import { ChecklistItemEditor } from "./ChecklistItemEditor";

const input: React.CSSProperties = { padding: "9px 11px", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)", minWidth: 0 };

export function ChecklistTemplateEditor({ templateId, retired = false, onChanged = () => {} }: {
  templateId: string; retired?: boolean; onChanged?: () => void;
}) {
  const content = useApi(useCallback(() => checklistCatalogApi.getLatestVersion(templateId), [templateId]), [templateId]);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [message, setMessage] = useState("");
  const version = content.data;
  const editable = !retired && version?.status === "DRAFT";
  const refresh = () => { content.refetch(); onChanged(); };
  const draft = useAction(async () => { await checklistCatalogApi.getOrCreateDraftVersion(templateId); refresh(); });
  const section = useAction(async () => {
    if (!version) return;
    await checklistCatalogApi.addSection(version.id, title.trim(), version.sections.length);
    setTitle(""); refresh();
  });
  const publish = useAction(async () => {
    if (!version) return;
    await checklistCatalogApi.publishVersion(version.id, summary.trim() || undefined);
    setMessage(`Version ${version.version_number} published. Map this version to the intended job type. Existing mappings and jobs keep their previous version.`);
    setSummary(""); refresh();
  });
  if (content.loading) return <Skeleton height={220}/>;
  if (content.error || !version) return <Card><p role="alert">{content.error ?? "Checklist content is unavailable."}</p><Btn onClick={content.refetch}>Retry</Btn></Card>;
  const count = version.sections.reduce((total, row) => total + row.items.length, 0);
  return <div style={{ display: "grid", gap: 16 }}>
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
      <Badge variant={version.status === "PUBLISHED" ? "success" : "warning"}>v{version.version_number} · {version.status}</Badge>
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{version.sections.length} sections · {count} items</span>
      {!editable && !retired && <Btn size="sm" variant="secondary" loading={draft.loading} onClick={() => draft.execute()}>Create editable draft</Btn>}
    </div>
    <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
      {retired ? "Retired template. Restore it from Details before making changes."
        : editable ? "1. Add sections and items below. 2. Publish the finished version. 3. Map it to a job type in the blueprint workspace."
        : "Published content is read-only. An editable draft copies this version without changing live jobs."}
    </p>
    {message && <div role="status" style={{ padding: 12, background: "var(--success-bg)", borderRadius: 8 }}>{message}</div>}
    {(draft.error || publish.error || section.error) && <p role="alert" style={{ color: "var(--danger-text)" }}>{draft.error || publish.error || section.error}</p>}
    {!version.sections.length && <div style={{ padding: 24, border: "1px dashed var(--border)", borderRadius: 10 }}>Start with a section, such as “Before work” or “Final checks”.</div>}
    {version.sections.map(row => <Card key={row.id} padding={16}>
      <SectionHeading section={row} editable={editable} onChanged={refresh}/>
      {!row.items.length && <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>No items yet. Add a check, question or evidence request.</p>}
      {row.items.map((item, index) => <div key={item.id} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", padding: "12px 0", borderTop: "1px solid var(--border)" }}>
        <span style={{ color: "var(--text-tertiary)" }}>{index + 1}.</span>
        <div style={{ flex: "1 1 200px" }}><strong style={{ fontSize: 13 }}>{item.label}</strong>{item.help_text && <p style={{ fontSize: 12, margin: "4px 0", color: "var(--text-secondary)" }}>{item.help_text}</p>}
          <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}><Badge variant="info">{item.item_type.replaceAll("_", " ")}</Badge>{item.is_required && <Badge variant="warning">Required</Badge>}{item.evidence_required && <Badge variant="muted">Evidence required</Badge>}{item.customer_visible && <Badge variant="success">Customer visible</Badge>}</div>
          {item.select_options?.length ? <small>{item.select_options.map(option => option.label).join(" · ")}</small> : null}
        </div>
        {editable && <ChecklistItemEditor sectionId={row.id} item={item} onSaved={refresh}/>}
      </div>)}
      {editable && <ChecklistItemEditor sectionId={row.id} order={row.items.length} onSaved={refresh}/>}
    </Card>)}
    {editable && <>
      <div style={{ display: "flex", gap: 8 }}><input aria-label="New section title" placeholder="New section title" maxLength={200} style={{ ...input, flex: 1 }} value={title} onChange={event => setTitle(event.target.value)}/><Btn variant="secondary" disabled={!title.trim()} loading={section.loading} onClick={() => section.execute()}>Add section</Btn></div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", borderTop: "1px solid var(--border)", paddingTop: 16 }}>
        <input aria-label="Publication change summary" placeholder="Change summary (optional)" style={{ ...input, flex: "1 1 220px" }} value={summary} onChange={event => setSummary(event.target.value)}/>
        <Btn variant="primary" disabled={count === 0 || section.loading} loading={publish.loading} onClick={() => publish.execute()}>Publish version</Btn>
      </div>
    </>}
    {!editable && !retired && <Link href="/admin/catalog-workspace">Map this published checklist in Job-Type Blueprints → Checklist</Link>}
  </div>;
}

function SectionHeading({ section, editable, onChanged }: { section: ChecklistSectionRow; editable: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(section.title);
  const [confirm, setConfirm] = useState(false);
  const save = useAction(async () => { await checklistCatalogApi.updateSection(section.id, { title: title.trim() }); setEditing(false); onChanged(); });
  const remove = useAction(async () => { await checklistCatalogApi.deleteSection(section.id); setConfirm(false); onChanged(); });
  return <>
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
      {editing ? <><input aria-label="Section title" style={{ ...input, flex: 1 }} value={title} onChange={event => setTitle(event.target.value)}/><Btn size="xs" disabled={!title.trim()} loading={save.loading} onClick={() => save.execute()}>Save section</Btn></> : <strong style={{ flex: 1 }}>{section.title}</strong>}
      {editable && <><Btn size="xs" variant="ghost" onClick={() => setEditing(value => !value)}>{editing ? "Cancel" : "Rename"}</Btn><Btn size="xs" variant="ghost" onClick={() => setConfirm(true)}>Remove section</Btn></>}
    </div>
    {save.error && <p role="alert">{save.error}</p>}
    <Modal open={confirm} onClose={() => setConfirm(false)} title="Remove draft section?">
      <p>This removes “{section.title}” and its {section.items.length} draft items. Published versions and existing jobs are unchanged.</p>
      {remove.error && <p role="alert">{remove.error}</p>}
      <Btn variant="danger" loading={remove.loading} onClick={() => remove.execute()}>Remove section and draft items</Btn>
    </Modal>
  </>;
}
