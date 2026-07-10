"use client";
import React, { useState, useRef } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Skeleton, StatCard, DeleteBtn } from "../../../components/shared/ui";
import { mediaApi, type MediaFile, type MediaQuota } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Upload, HardDrive, FolderOpen, Cloud, CheckCircle2, Image, FileText, Film, Paperclip, Eye } from "lucide-react";

function fmtBytes(b: number) {
  if (b >= 1e9) return `${(b/1e9).toFixed(1)} GB`;
  if (b >= 1e6) return `${(b/1e6).toFixed(1)} MB`;
  if (b >= 1e3) return `${(b/1e3).toFixed(0)} KB`;
  return `${b} B`;
}

const PURPOSE_OPTS = ["job_photo", "invoice", "document", "profile", "other"];

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
        <SectionHeader
          title="Media Vault"
          subtitle="Upload, manage and organise your business files"
          icon={<Image/>}
          actions={
            <div style={{ display:"flex", gap:10, alignItems:"center" }}>
              <select value={purpose} onChange={e => setPurpose(e.target.value)}
                style={{ padding:"6px 12px", border:"1px solid var(--border)", borderRadius:9,
                  background:"var(--surface)", color:"var(--text-primary)", fontSize:13,
                  height:36, outline:"none", cursor:"pointer" }}>
                {PURPOSE_OPTS.map(p => <option key={p} value={p}>{p.replace(/_/g," ")}</option>)}
              </select>
              <Btn size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading} icon={<Upload size={14}/>}>
                Upload File
              </Btn>
              <input ref={fileInputRef} type="file" style={{ display:"none" }}
                onChange={handleUpload} accept="image/*,application/pdf,video/*" />
            </div>
          }
        />

        {toast && (
          <div style={{ padding:"12px 16px", background:"var(--success-bg)", border:"1px solid var(--success-border)",
            borderRadius:10, color:"var(--success-text)", fontSize:13, display:"flex", alignItems:"center", gap:8 }}>
            <CheckCircle2 size={14}/> {toast}
          </div>
        )}

        {/* Quota stat cards */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14 }}>
          {quota.loading ? (
            [...Array(3)].map((_,i) => (
              <Card key={i} padding={18}>
                <Skeleton height={12} width={80} style={{ marginBottom:10 }}/>
                <Skeleton height={24} width={60}/>
              </Card>
            ))
          ) : <>
            <StatCard
              label="Storage Used"
              value={q ? fmtBytes(q.used_bytes) : "—"}
              change={`of ${q ? fmtBytes(q.limit_bytes) : "?"} total`}
              trend={usedPct > 80 ? "down" : "neutral"}
              icon={<HardDrive/>}
              alert={usedPct > 90}
            />
            <StatCard
              label="Files Stored"
              value={q?.file_count ?? 0}
              change={`of ${q?.file_limit ?? "?"} limit`}
              trend="neutral"
              icon={<FolderOpen/>}
            />
            <StatCard
              label="Free Space"
              value={freeBytes > 0 ? fmtBytes(freeBytes) : "Full"}
              change={`${freePct}% remaining`}
              trend={freePct < 20 ? "down" : "up"}
              icon={<Cloud/>}
              alert={freePct < 10}
            />
          </>}
        </div>

        {/* Quota bar */}
        {q && (
          <Card padding={16}>
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
            <button key={p} onClick={() => setFilter(p)}
              style={{ padding:"5px 14px", borderRadius:999,
                border: `1px solid ${filter === p ? "var(--brand)" : "var(--border)"}`,
                cursor:"pointer", fontSize:12, fontWeight:600,
                background: filter === p ? "var(--brand)" : "var(--surface)",
                color: filter === p ? "white" : "var(--text-secondary)",
                transition:"all 0.12s" }}>
              {p.replace(/_/g, " ")}
            </button>
          ))}
        </div>

        {/* File grid */}
        <Card padding={16}>
          {files.loading ? (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(220px,1fr))", gap:12 }}>
              {[...Array(8)].map((_,i) => (
                <div key={i} style={{ border:"1px solid var(--border)", borderRadius:10, overflow:"hidden" }}>
                  <Skeleton height={120} radius={0}/>
                  <div style={{ padding:"10px 12px" }}>
                    <Skeleton height={12} width="80%" style={{ marginBottom:6 }}/>
                    <Skeleton height={10} width="50%"/>
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
              <Btn size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading} icon={<Upload size={14}/>}>
                Upload File
              </Btn>
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
          <Badge variant="muted" size="sm">{file.purpose.replace(/_/g," ")}</Badge>
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
            <Btn variant="secondary" size="xs" icon={<Eye size={13}/>} fullWidth>View</Btn>
          </a>
        )}
        <DeleteBtn onClick={onDelete} size="sm" tooltip={deleting ? "Deleting…" : "Delete"}/>
      </div>
    </div>
  );
}
