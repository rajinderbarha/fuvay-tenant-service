"use client";
import { useEffect, useState } from "react";
import { Badge, Btn, Modal } from "../shared/ui";
import { loadAdminDocument } from "../../lib/open-admin-media-preview";

type Document = Record<string, unknown>;
const title = (doc: Document) => String(doc.label || doc.doc_type || "Document").replace(/_/g, " ");
const date = (value: unknown) => value ? new Date(String(value)).toLocaleString("en-IN") : "—";

export function ProviderDocuments({ documents }: { documents: Document[] }) {
  const [selected, setSelected] = useState<Document | null>(null);
  const [preview, setPreview] = useState<{ url: string; type: string } | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setPreview(null); setError("");
    if (!selected?.media_asset_id) return;
    const controller = new AbortController();
    let url: string | undefined;
    loadAdminDocument(String(selected.media_asset_id), controller.signal).then(blob => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob);
      setPreview({ url, type: blob.type });
    }).catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Could not load document."); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [selected, retry]);

  return <>
    <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Current uploaded versions. Upload completion is separate from admin verification. Open a document to read it; review decisions remain in the Onboarding Queue.</p>
    {documents.length === 0 && <p>No documents uploaded yet.</p>}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(280px,100%),1fr))", gap: 12 }}>
      {documents.map(doc => <article key={String(doc.id)} style={{ border: "1px solid var(--border)", padding: 16, borderRadius: 12 }}>
        <h4 style={{ margin: "0 0 8px", textTransform: "capitalize" }}>{title(doc)}</h4>
        <Badge variant={doc.status === "verified" ? "success" : doc.status === "rejected" ? "danger" : "warning"}>{String(doc.status).replace(/_/g, " ")}</Badge>
        <p style={{ fontSize: 12 }}>Version {String(doc.version ?? 1)} · {doc.staff_member_id ? "Team document" : "Business document"}</p>
        <p style={{ fontSize: 12 }}>Uploaded: {date(doc.uploaded_at)}<br/>Verified: {date(doc.verified_at)}<br/>Expires: {date(doc.expiry_date)}</p>
        {doc.rejection_reason ? <p style={{ color: "var(--danger-text)", fontSize: 12 }}>Review note: {String(doc.rejection_reason)}</p> : null}
        {doc.media_asset_id ? <Btn variant="secondary" onClick={() => setSelected(doc)}>View {title(doc)}</Btn>
          : <p style={{ fontSize: 12 }}>No previewable attachment linked. Ask the provider to upload a replacement.</p>}
      </article>)}
    </div>
    <Modal open={!!selected} onClose={() => setSelected(null)} title={selected ? title(selected) : "Document"} size="xl">
      {selected && <>
        <p>Version {String(selected.version ?? 1)} · {String(selected.status).replace(/_/g, " ")} · Document number: {String(selected.document_number || "Not supplied")}</p>
        {error ? <div role="alert"><p>{error}</p><Btn onClick={() => setRetry(n => n+1)}>Retry preview</Btn></div>
          : !preview ? <p role="status">Loading secure document preview…</p>
          : <>
            <a href={preview.url} target="_blank" rel="noopener noreferrer">Open full size</a>
            {preview.type.startsWith("image/") ? <img src={preview.url} alt={title(selected)} style={{ display: "block", maxWidth: "100%", maxHeight: "65vh", objectFit: "contain", margin: "12px auto" }}/>
              : <iframe title={`${title(selected)} preview`} src={preview.url} style={{ width: "100%", height: "65vh", border: "1px solid var(--border)", marginTop: 12 }}/>
            }
          </>}
      </>}
    </Modal>
  </>;
}
