"use client";
import React, { useState } from "react";
import { FileText, Image, Trash2, Download, X } from "lucide-react";
import { mediaAssetApi, type MediaAsset, type ServiceOSError } from "../../lib/api";

const isImage = (mime: string) => mime.startsWith("image/");
const isPdf   = (mime: string) => mime === "application/pdf";

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

type MediaPreviewProps = {
  asset: MediaAsset;
  onDeleted?: (id: string) => void;
  canDelete?: boolean;
  canDownload?: boolean;
  compact?: boolean;
};

export function MediaPreview({ asset, onDeleted, canDelete = true, canDownload = true, compact = false }: MediaPreviewProps) {
  const [deleting, setDeleting] = useState(false);
  const [error,    setError]    = useState("");
  const [lightbox, setLightbox] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete "${asset.file_name_original}"?`)) return;
    setDeleting(true);
    setError("");
    try {
      await mediaAssetApi.delete(asset.id);
      onDeleted?.(asset.id);
    } catch (e) {
      setError((e as ServiceOSError).message ?? "Delete failed.");
    } finally {
      setDeleting(false);
    }
  }

  const viewUrl = mediaAssetApi.viewUrl(asset.id);
  const dlUrl   = mediaAssetApi.downloadUrl(asset.id);

  if (compact) {
    return (
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
        border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)",
        minWidth: 0,
      }}>
        <span style={{ flexShrink: 0, color: "var(--text-tertiary)" }}>
          {isImage(asset.mime_type) ? <Image size={16}/> : <FileText size={16}/>}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)", margin: 0,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {asset.file_name_original}
          </p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
            {formatBytes(asset.file_size_bytes)}
          </p>
        </div>
        {canDownload && (
          <a href={dlUrl} target="_blank" rel="noopener noreferrer"
            style={{ color: "var(--text-tertiary)", flexShrink: 0, display: "flex", alignItems: "center" }}>
            <Download size={14}/>
          </a>
        )}
        {canDelete && (
          <button onClick={handleDelete} disabled={deleting}
            style={{ background: "none", border: "none", cursor: deleting ? "not-allowed" : "pointer",
              color: "var(--danger)", padding: 0, display: "flex", alignItems: "center", flexShrink: 0 }}>
            <X size={14}/>
          </button>
        )}
      </div>
    );
  }

  return (
    <>
      <div style={{
        border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden",
        background: "var(--surface)", display: "flex", flexDirection: "column",
      }}>
        {/* Preview area */}
        <div style={{
          height: 160, background: "var(--surface-sunken)", display: "flex",
          alignItems: "center", justifyContent: "center", overflow: "hidden",
          cursor: isImage(asset.mime_type) ? "pointer" : "default",
        }}
          onClick={() => isImage(asset.mime_type) && setLightbox(true)}
        >
          {isImage(asset.mime_type) ? (
            <img
              src={viewUrl}
              alt={asset.file_name_original}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : isPdf(asset.mime_type) ? (
            <div style={{ textAlign: "center", color: "var(--text-tertiary)" }}>
              <FileText size={40}/>
              <p style={{ fontSize: 11, margin: "8px 0 0" }}>PDF</p>
            </div>
          ) : (
            <div style={{ textAlign: "center", color: "var(--text-tertiary)" }}>
              <FileText size={40}/>
              <p style={{ fontSize: 11, margin: "8px 0 0" }}>{asset.file_extension.replace(".", "").toUpperCase()}</p>
            </div>
          )}
        </div>

        {/* Meta */}
        <div style={{ padding: "10px 12px" }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)", margin: "0 0 2px",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {asset.file_name_original}
          </p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
            {formatBytes(asset.file_size_bytes)}
          </p>
          {error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: "4px 0 0" }}>{error}</p>}
        </div>

        {/* Actions */}
        {(canDownload || canDelete) && (
          <div style={{ borderTop: "1px solid var(--border)", display: "flex" }}>
            {canDownload && (
              <a href={dlUrl} target="_blank" rel="noopener noreferrer"
                style={{ flex: 1, padding: "8px 0", textAlign: "center", fontSize: 12,
                  color: "var(--text-secondary)", textDecoration: "none", display: "flex",
                  alignItems: "center", justifyContent: "center", gap: 4,
                  borderRight: canDelete ? "1px solid var(--border)" : "none" }}>
                <Download size={12}/> Download
              </a>
            )}
            {canDelete && (
              <button onClick={handleDelete} disabled={deleting}
                style={{ flex: 1, padding: "8px 0", fontSize: 12, textAlign: "center",
                  border: "none", cursor: deleting ? "not-allowed" : "pointer",
                  background: "none", color: deleting ? "var(--text-tertiary)" : "var(--danger-text)",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 4,
                  fontFamily: "inherit" }}>
                <Trash2 size={12}/> {deleting ? "Deleting…" : "Delete"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          onClick={() => setLightbox(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 9999, cursor: "zoom-out",
          }}
        >
          <img src={viewUrl} alt={asset.file_name_original}
            style={{ maxWidth: "90vw", maxHeight: "90vh", objectFit: "contain", borderRadius: 8 }}/>
        </div>
      )}
    </>
  );
}
