"use client";
import React, { useState, useRef } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { mediaApi, type MediaFile, type MediaQuota } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Upload, HardDrive, FolderOpen, Cloud, CheckCircle2, Image, FileText, Film, Paperclip, Eye, Trash2 } from "lucide-react";
import { PageHeader, Card, Button, Skeleton, Alert } from "@serviceos/design-system";

function fmtBytes(b: number) {
  if (b >= 1e9) return `${(b/1e9).toFixed(1)} GB`;
  if (b >= 1e6) return `${(b/1e6).toFixed(1)} MB`;
  if (b >= 1e3) return `${(b/1e3).toFixed(0)} KB`;
  return `${b} B`;
}

const PURPOSE_OPTS = ["job_photo", "invoice", "document", "profile", "other"];

function StatTile({ label, value, sub, icon, alert }: { label: string; value: string | number; sub: string; icon: React.ReactNode; alert?: boolean }) {
  return (
    <Card padding="md">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
        <span style={{ color: alert ? "var(--danger-text)" : "var(--text-tertiary)" }}>{icon}</span>
      </div>
      <p style={{ fontSize: 22, fontWeight: 800, color: alert ? "var(--danger-text)" : "var(--text-primary)", margin: 0 }}>{value}</p>
      <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "4px 0 0" }}>{sub}</p>
    </Card>
  );
}

export default function MediaPage() {
  const files = useApi(() => mediaApi.listFiles({ limit: 50 }), []);
  const quota = useApi(() => mediaApi.getQuota(), []);

  const [filter,    setFilter]    = useState("all");
  const [toast,     setToast]     = useState("");
  const [uploading, setUploading] = useState(false);
  const [purpose,   setPurpose]   = useState("job_photo");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const deleteFile = useAction(async (fileId: string) => {
    await mediaApi.deleteFile(fileId);
    await files.refetch();
    await quota.refetch();
    notify("File deleted.");
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const session = await mediaApi.initiateUpload(file.name, file.type, file.size);
      await fetch(session.upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });
      await mediaApi.confirmUpload(session.session_id);
      await files.refetch();
      await quota.refetch();
      notify(`${file.name} uploaded successfully.`);
    } catch (err: unknown) {
      notify(`Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const q = quota.data as MediaQuota | null;
  const usedPct  = q ? Math.round((q.used_bytes / q.limit_bytes) * 100) : 0;
  const freePct  = 100 - usedPct;
  const freeBytes = q ? q.limit_bytes - q.used_bytes : 0;

  const filtered = (files.data?.files ?? []).filter(f => filter === "all" || f.purpose === filter);

  const iconFor = (ct: string): React.ReactNode => {
    if (ct.startsWith("image/")) return <Image size={44}/>;
    if (ct === "application/pdf") return <FileText size={44}/>;
    if (ct.startsWith("video/")) return <Film size={44}/>;
    return <Paperclip size={44}/>;
  };

  return (
    <TenantLayout activeNav="media">
      <div style={{ display:"flex", flexDirection:"column", gap:24 }}>
        <PageHeader
          title="Media Vault"
          description="Upload, manage and organise your business files"
          actions={
            <div style={{ display:"flex", gap:10, alignItems:"center" }}>
              <select value={purpose} onChange={e => setPurpose(e.target.value)}
                style={{ padding:"6px 12px", border:"1px solid var(--border)", borderRadius:9,
                  background:"var(--surface)", color:"var(--text-primary)", fontSize:13,
                  height:36, outline:"none", cursor:"pointer" }}>
                {PURPOSE_OPTS.map(p => <option key={p} value={p}>{p.replace(/_/g," ")}</option>)}
              </select>
              <Button size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading} leftIcon={<Upload size={14}/>}>
                Upload File
              </Button>
              <input ref={fileInputRef} type="file" style={{ display:"none" }}
                onChange={handleUpload} accept="image/*,application/pdf,video/*" />
            </div>
          }
        />

        {toast && <Alert tone="success">{toast}</Alert>}

        {/* Quota stat cards */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14 }}>
          {quota.loading ? (
            [...Array(3)].map((_,i) => <Skeleton key={i} height="6.5rem" radius="12px"/>)
          ) : <>
            <StatTile
              label="Storage Used"
              value={q ? fmtBytes(q.used_bytes) : "—"}
              sub={`of ${q ? fmtBytes(q.limit_bytes) : "?"} total`}
              icon={<HardDrive size={16}/>}
              alert={usedPct > 90}
            />
            <StatTile
              label="Files Stored"
              value={q?.file_count ?? 0}
              sub={`of ${q?.file_limit ?? "?"} limit`}
              icon={<FolderOpen size={16}/>}
            />
            <StatTile
              label="Free Space"
              value={freeBytes > 0 ? fmtBytes(freeBytes) : "Full"}
              sub={`${freePct}% remaining`}
              icon={<Cloud size={16}/>}
              alert={freePct < 10}
            />
          </>}
        </div>

        {/* Quota bar */}
        {q && (
          <Card padding="md">
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
              <span style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Storage Usage</span>
              <span style={{ fontSize:12, fontWeight:700,
                color: usedPct > 90 ? "var(--danger-text)" : usedPct > 70 ? "var(--warning-text)" : "var(--success-text)" }}>
                {usedPct}%
              </span>
            </div>
            <div style={{ background:"var(--surface-sunken)", borderRadius:999, height:8, overflow:"hidden" }}>
              <div style={{ height:"100%", width:`${usedPct}%`, borderRadius:999,
                background: usedPct > 90 ? "var(--danger)" : usedPct > 70 ? "var(--warning)" : "var(--brand)",
                transition:"width 0.4s ease" }} />
            </div>
          </Card>
        )}

        {/* Purpose filter pills */}
        <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
          {["all", ...PURPOSE_OPTS].map(p => (
            <Button key={p} variant={filter === p ? "primary" : "secondary"} size="sm" onClick={() => setFilter(p)}>
              {p.replace(/_/g, " ")}
            </Button>
          ))}
        </div>

        {/* File grid */}
        <Card padding="md">
          {files.loading ? (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(220px,1fr))", gap:12 }}>
              {[...Array(8)].map((_,i) => (
                <div key={i} style={{ border:"1px solid var(--border)", borderRadius:10, overflow:"hidden" }}>
                  <Skeleton height="7.5rem" radius="0"/>
                  <div style={{ padding:"10px 12px" }}>
                    <Skeleton height="0.75rem" width="80%" />
                    <div style={{ marginTop: 6 }}><Skeleton height="0.625rem" width="50%"/></div>
                  </div>
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign:"center", padding:56 }}>
              <div style={{ display:"flex", justifyContent:"center", color:"var(--text-tertiary)", margin:"0 0 10px" }}>
                <FolderOpen size={42}/>
              </div>
              <p style={{ color:"var(--text-secondary)", fontSize:14, fontWeight:500 }}>No files yet.</p>
              <p style={{ color:"var(--text-tertiary)", fontSize:13, margin:"4px 0 16px" }}>
                Upload your first file using the button above.
              </p>
              <Button size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading} leftIcon={<Upload size={14}/>}>
                Upload File
              </Button>
            </div>
          ) : (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(220px,1fr))", gap:12 }}>
              {filtered.map((f: MediaFile) => (
                <FileCard key={f.file_id} file={f}
                  onDelete={() => deleteFile.execute(f.file_id)}
                  deleting={deleteFile.loading}
                  iconFor={iconFor}
                />
              ))}
            </div>
          )}
        </Card>
      </div>
    </TenantLayout>
  );
}

function FileCard({ file, onDelete, deleting, iconFor }: {
  file: MediaFile;
  onDelete: () => void;
  deleting: boolean;
  iconFor: (ct: string) => React.ReactNode;
}) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{ border:`1px solid ${hov ? "var(--border-strong)" : "var(--border)"}`,
        borderRadius:12, overflow:"hidden", display:"flex", flexDirection:"column",
        transition:"all 0.15s", boxShadow: hov ? "var(--shadow-md)" : "var(--shadow-sm)",
        transform: hov ? "translateY(-1px)" : "none" }}>
      {/* Preview */}
      <div style={{ height:130, background:"var(--surface-sunken)",
        display:"flex", alignItems:"center", justifyContent:"center", overflow:"hidden" }}>
        {file.content_type.startsWith("image/") && file.url ? (
          <img src={file.url} alt={file.filename}
            style={{ width:"100%", height:"100%", objectFit:"cover" }} />
        ) : (
          <span style={{ color:"var(--text-tertiary)", display:"flex" }}>{iconFor(file.content_type)}</span>
        )}
      </div>
      {/* Info */}
      <div style={{ padding:"10px 12px", flex:1, display:"flex", flexDirection:"column", gap:6 }}>
        <p style={{ margin:0, fontSize:13, fontWeight:600, whiteSpace:"nowrap",
          overflow:"hidden", textOverflow:"ellipsis", color:"var(--text-primary)" }}>
          {file.filename}
        </p>
        <div style={{ display:"flex", gap:6, alignItems:"center", flexWrap:"wrap" }}>
          <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
            background: "var(--surface-sunken)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            {file.purpose.replace(/_/g," ")}
          </span>
          <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>
            {fmtBytes(file.size_bytes)}
          </span>
        </div>
        <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
          {new Date(file.created_at).toLocaleDateString()}
        </p>
      </div>
      {/* Actions */}
      <div style={{ padding:"8px 12px", borderTop:"1px solid var(--border)",
        display:"flex", gap:6, alignItems:"center" }}>
        {file.url && (
          <a href={file.url} target="_blank" rel="noopener noreferrer" style={{ flex:1 }}>
            <Button variant="secondary" size="sm" leftIcon={<Eye size={13}/>} style={{ width: "100%", justifyContent: "center" }}>View</Button>
          </a>
        )}
        <Button variant="icon" size="sm" aria-label={deleting ? "Deleting…" : "Delete"} onClick={onDelete}>
          <Trash2 size={13}/>
        </Button>
      </div>
    </div>
  );
}
