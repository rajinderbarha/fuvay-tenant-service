"use client";
/**
 * Documents — tabs by status, signing CTA, signing URL fetch, generate modal.
 * PROVEN: documentsApi.list() + getSigningUrl() + generate() connected.
 * PROVEN: useAction on generate + getSigningUrl.
 */
import React, { useCallback, useState } from "react";
import { TenantLayout }                 from "../../../components/layout/TenantLayout";
import { Card, Btn, Badge, Skeleton, SectionHeader, Modal, Input } from "../../../components/shared/ui";
import { documentsApi }                 from "../../../lib/api";
import { useApi, useAction }            from "../../../hooks/useApi";
import type { TenantDocument }          from "../../../lib/api";
import { Plus, FileText, CheckCircle2, XCircle, Circle, Download, Clock } from "lucide-react";

const STATUS_TABS = [
  { key:"",                    label:"All"        },
  { key:"pending_signature",   label:"To Sign"    },
  { key:"signed",              label:"Signed"     },
  { key:"expired",             label:"Expired"    },
  { key:"draft",               label:"Draft"      },
] as const;

const STATUS_META: Record<string, { variant: "success"|"warning"|"danger"|"muted"|"info"; icon: React.ReactNode }> = {
  signed:            { variant:"success", icon:<CheckCircle2 size={11}/> },
  pending_signature: { variant:"warning", icon:<Clock size={11}/> },
  expired:           { variant:"danger",  icon:<XCircle size={11}/> },
  draft:             { variant:"muted",   icon:<Circle size={11}/> },
};

export default function DocumentsPage() {
  const [statusTab,    setStatusTab]    = useState("");
  const [generateOpen, setGenerateOpen] = useState(false);
  const [signingModal, setSigningModal] = useState<{ url:string; expires:string } | null>(null);

  // Generate form state
  const [templateId, setTemplateId] = useState("");
  const [jobId,      setJobId]      = useState("");

  const params = useCallback(() =>
    documentsApi.list({
      limit:"30",
      ...(statusTab ? { status: statusTab } : {}),
    }), [statusTab]);

  const docs          = useApi(params);
  const generateAction = useAction(useCallback(
    (tid: string, jid: string) => documentsApi.generate(tid, jid, {}), []
  ));
  const signingAction  = useAction(useCallback(
    (docId: string) => documentsApi.getSigningUrl(docId), []
  ));

  async function handleGenerate() {
    if (!templateId || !jobId) return;
    const res = await generateAction.execute(templateId, jobId);
    if (res) { docs.refetch(); setGenerateOpen(false); setTemplateId(""); setJobId(""); }
  }

  async function handleSign(doc: TenantDocument) {
    if (doc.signing_url) {
      window.open(doc.signing_url, "_blank");
      return;
    }
    const res = await signingAction.execute(doc.id);
    if (res) {
      setSigningModal({ url: res.signing_url, expires: res.expires_at });
    }
  }

  const allDocs    = docs.data?.documents ?? [];
  const pending    = allDocs.filter(d => d.status === "pending_signature").length;

  return (
    <TenantLayout activeNav="documents">
      <SectionHeader
        title="Documents"
        subtitle="Service agreements, warranties, e-signed documents"
        icon={<FileText/>}
        actions={
          <Btn variant="primary" size="sm" icon={<Plus size={14}/>} onClick={() => setGenerateOpen(true)}>
            Generate Document
          </Btn>
        }
      />

      {/* Status tabs */}
      <div style={{ display:"flex", gap:4, marginBottom:14,
        padding:"4px", background:"var(--surface-sunken)",
        borderRadius:10, border:"1px solid var(--border)", width:"fit-content",
        flexWrap:"wrap" }}>
        {STATUS_TABS.map(t => (
          <button key={t.key} onClick={() => setStatusTab(t.key)}
            style={{ padding:"6px 14px", borderRadius:"var(--radius-md)", border:"none", cursor:"pointer",
              fontFamily:"inherit", fontSize:12, fontWeight: statusTab===t.key ? 700 : 500,
              background: statusTab===t.key ? "var(--surface-base)" : "transparent",
              color: statusTab===t.key ? "var(--brand)" : "var(--text-secondary)",
              boxShadow: statusTab===t.key ? "var(--shadow-xs)" : "none",
              position:"relative", transition:"all 0.12s" }}>
            {t.label}
            {t.key === "pending_signature" && pending > 0 && (
              <span style={{ position:"absolute", top:2, right:4, width:14, height:14,
                borderRadius:"50%", background:"var(--danger)", color:"white",
                fontSize:9, fontWeight:700, display:"flex", alignItems:"center",
                justifyContent:"center", lineHeight:1 }}>{pending}</span>
            )}
          </button>
        ))}
      </div>

      {/* Document list */}
      {docs.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {[...Array(4)].map((_,i) =>
            <Skeleton key={i} height={80} style={{ borderRadius:"var(--radius-lg)" }} />)}
        </div>
      ) : allDocs.length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <div style={{ display:"flex", justifyContent:"center", color:"var(--text-tertiary)", margin:"0 0 12px" }}>
            <FileText size={36}/>
          </div>
          <p style={{ fontSize:15, fontWeight:600, color:"var(--text-primary)",
            margin:"0 0 6px" }}>No documents yet</p>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 20px" }}>
            {statusTab ? `No ${statusTab.replace(/_/g," ")} documents`
                       : "Generate your first document to get started"}
          </p>
          <Btn variant="primary" size="sm" icon={<Plus size={14}/>} onClick={() => setGenerateOpen(true)}>
            Generate Document
          </Btn>
        </Card>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {allDocs.map(d => {
            const meta    = STATUS_META[d.status] ?? { variant:"muted" as const, icon:<Circle size={11}/> };
            const isSign  = d.status === "pending_signature";
            const isSigned= d.status === "signed";
            return (
              <Card key={d.id} padding={0} style={{ overflow:"hidden" }}>
                <div style={{ display:"flex", alignItems:"stretch", gap:0 }}>
                  {/* Status stripe */}
                  <div style={{ width:5, flexShrink:0,
                    background: isSign  ? "var(--warning)"
                              : isSigned ? "var(--success)"
                              : d.status==="expired" ? "var(--danger)"
                              : "var(--border)" }} />

                  <div style={{ display:"flex", alignItems:"center", gap:14, padding:"14px 18px",
                    flex:1, minWidth:0 }}>
                    {/* Doc icon */}
                    <div style={{ width:44, height:44, borderRadius:10,
                      background: isSign ? "var(--warning-bg)" : "var(--surface-sunken)",
                      display:"flex", alignItems:"center", justifyContent:"center",
                      color: isSign ? "var(--warning-text)" : "var(--text-tertiary)", flexShrink:0 }}>
                      <FileText size={22}/>
                    </div>

                    {/* Info */}
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:3 }}>
                        <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)",
                          margin:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                          {d.title}
                        </p>
                        <Badge variant={meta.variant} size="sm">
                          {meta.icon} {d.status.replace(/_/g," ")}
                        </Badge>
                      </div>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                        {d.document_number}
                        {d.job_id && ` · Job: ${d.job_id.slice(0,8)}…`}
                        {" · "}
                        {new Date(d.created_at).toLocaleDateString("en-IN",
                          { day:"numeric", month:"short", year:"numeric" })}
                        {d.signed_at && ` · Signed ${new Date(d.signed_at).toLocaleDateString("en-IN",{day:"numeric",month:"short"})}`}
                      </p>
                      {/* Signing expiry warning */}
                      {isSign && d.signing_url_expires_at && (
                        <p style={{ fontSize:11, color:"var(--warning-text)", margin:"3px 0 0", fontWeight:600, display:"flex", alignItems:"center", gap:4 }}>
                          <Clock size={11}/> Signing link expires{" "}
                          {new Date(d.signing_url_expires_at).toLocaleString("en-IN",
                            { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" })}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div style={{ display:"flex", gap:8, flexShrink:0 }}>
                      {isSign && (
                        <Btn variant="primary" size="sm"
                          loading={signingAction.loading}
                          onClick={() => handleSign(d)}>
                          Sign Now
                        </Btn>
                      )}
                      {isSigned && (
                        <Btn variant="secondary" size="sm" icon={<Download size={14}/>}
                          onClick={() => documentsApi.get(d.id)}>
                          Download
                        </Btn>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ── Generate Document Modal ── */}
      <Modal open={generateOpen} onClose={() => setGenerateOpen(false)}
        title="Generate Document">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0, lineHeight:1.5 }}>
            Generate a document from a template. The document will be added to the signing queue.
          </p>
          <Input label="Template ID" value={templateId}
            onChange={setTemplateId} placeholder="e.g. service_agreement_v2"
            hint="Contact support to get your template IDs" />
          <Input label="Job ID" value={jobId}
            onChange={setJobId} placeholder="e.g. job_abc123"
            hint="The job this document is linked to" />
          {generateAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0,
              padding:"8px 12px", borderRadius:6, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              {generateAction.error}
            </p>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end", marginTop:4 }}>
            <Btn variant="ghost" size="sm" onClick={() => setGenerateOpen(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm"
              loading={generateAction.loading}
              disabled={!templateId || !jobId}
              onClick={handleGenerate}>
              Generate
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Signing URL Modal ── */}
      <Modal open={!!signingModal} onClose={() => setSigningModal(null)}
        title="Document Ready to Sign">
        {signingModal && (
          <div style={{ display:"flex", flexDirection:"column", gap:14, textAlign:"center" }}>
            <div style={{ display:"flex", justifyContent:"center", color:"var(--accent)" }}>
              <CheckCircle2 size={32}/>
            </div>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
              Your signing link is ready. It expires on{" "}
              {new Date(signingModal.expires).toLocaleString("en-IN",
                { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" })}.
            </p>
            <a href={signingModal.url} target="_blank" rel="noreferrer"
              style={{ display:"block" }}>
              <Btn variant="primary" size="md" fullWidth>
                Open Signing Portal
              </Btn>
            </a>
            <Btn variant="ghost" size="sm" onClick={() => setSigningModal(null)}>
              Close
            </Btn>
          </div>
        )}
      </Modal>
    </TenantLayout>
  );
}
