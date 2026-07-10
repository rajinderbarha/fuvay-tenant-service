"use client";
import React, { useRef, useState } from "react";
import { Upload, Loader2, AlertCircle } from "lucide-react";
import { mediaAssetApi, friendlyMediaError, type MediaAsset, type ServiceOSError } from "../../lib/api";
import { MediaPreview } from "./MediaPreview";

type MediaUploaderProps = {
  mediaContext: string;
  ownerType: string;
  ownerId: string;
  accept?: string;
  maxSizeMB?: number;
  multiple?: boolean;
  existingMedia?: MediaAsset[];
  isPublic?: boolean;
  label?: string;
  hint?: string;
  canDelete?: boolean;
  onUploaded?: (asset: MediaAsset) => void;
  onDeleted?: (id: string) => void;
  onError?: (msg: string) => void;
  disabled?: boolean;
};

export function MediaUploader({
  mediaContext,
  ownerType,
  ownerId,
  accept = "image/*,application/pdf",
  maxSizeMB = 10,
  multiple = false,
  existingMedia = [],
  isPublic = false,
  label = "Upload file",
  hint,
  canDelete = true,
  onUploaded,
  onDeleted,
  onError,
  disabled = false,
}: MediaUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError]         = useState("");
  const [assets, setAssets]       = useState<MediaAsset[]>(existingMedia);

  function clearError() { setError(""); }

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    clearError();

    const toUpload = multiple ? Array.from(files) : [files[0]];

    for (const file of toUpload) {
      if (file.size > maxSizeMB * 1024 * 1024) {
        const msg = `File too large. Maximum size is ${maxSizeMB} MB.`;
        setError(msg);
        onError?.(msg);
        return;
      }

      setUploading(true);
      try {
        const asset = await mediaAssetApi.upload(mediaContext, ownerType, ownerId, file, isPublic);
        setAssets(prev => [...prev, asset]);
        onUploaded?.(asset);
      } catch (e) {
        const code = (e as ServiceOSError).code ?? "";
        const msg  = friendlyMediaError(code) || (e as ServiceOSError).message || "Upload failed.";
        setError(msg);
        onError?.(msg);
      } finally {
        setUploading(false);
      }
    }

    // Reset input so same file can be re-uploaded after delete
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleDeleted(id: string) {
    setAssets(prev => prev.filter(a => a.id !== id));
    onDeleted?.(id);
  }

  const [dragging, setDragging] = useState(false);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Dropzone */}
      <div
        onDragOver={e  => { e.preventDefault(); if (!disabled) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) handleFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && !uploading && inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? "var(--brand)" : error ? "var(--danger)" : "var(--border)"}`,
          borderRadius: 10,
          padding: "20px 16px",
          textAlign: "center",
          cursor: disabled || uploading ? "not-allowed" : "pointer",
          background: dragging ? "var(--info-bg)" : "var(--surface-sunken)",
          opacity: disabled ? 0.5 : 1,
          transition: "border-color 0.15s, background 0.15s",
        }}
      >
        {uploading ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <Loader2 size={24} style={{ color: "var(--brand)", animation: "spin 1s linear infinite" }}/>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Uploading…</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <Upload size={24} style={{ color: "var(--text-tertiary)" }}/>
            <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>{label}</p>
            {hint && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{hint}</p>}
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
              Click to browse or drag & drop · Max {maxSizeMB} MB
            </p>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        style={{ display: "none" }}
        onChange={e => handleFiles(e.target.files)}
        disabled={disabled || uploading}
      />

      {/* Error */}
      {error && (
        <div style={{
          display: "flex", alignItems: "center", gap: 8, padding: "10px 12px",
          background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          borderRadius: 8, fontSize: 13, color: "var(--danger-text)",
        }}>
          <AlertCircle size={14} style={{ flexShrink: 0 }}/>
          <span style={{ flex: 1 }}>{error}</span>
          <button onClick={() => { setError(""); }} style={{
            background: "none", border: "none", cursor: "pointer", color: "var(--danger-text)",
            fontSize: 12, padding: "0 4px", fontFamily: "inherit", fontWeight: 600,
          }}>Retry</button>
        </div>
      )}

      {/* Uploaded assets */}
      {assets.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {assets.map(asset => (
            <MediaPreview
              key={asset.id}
              asset={asset}
              onDeleted={canDelete ? handleDeleted : undefined}
              canDelete={canDelete}
              compact
            />
          ))}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
