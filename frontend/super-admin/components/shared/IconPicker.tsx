"use client";
// Shared icon/logo picker -- replaces the plain "paste a URL" text inputs
// that used to be the only way to set icon_url/image_url/logo_url on
// Category, Subcategory, Master Service, Service Type and Brand. Click the
// thumbnail -> a modal opens with two tabs: upload a new file from disk
// (goes straight to Cloudinary via the Media engine, see
// iconLibraryApi.upload), or pick an existing icon already uploaded for
// this context (Redis-cached list, see iconLibraryApi.list).
import { useCallback, useRef, useState } from "react";
import { Upload, Image as ImageIcon } from "lucide-react";
import { Modal, Btn } from "./ui";
import { iconLibraryApi, type IconLibraryContext, type MediaAsset } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

export function IconPicker({
  value, onChange, context, label, shape = "square",
}: {
  value: string | null | undefined;
  onChange: (url: string | null) => void;
  context: IconLibraryContext;
  label?: string;
  shape?: "square" | "circle";
}) {
  const [open, setOpen] = useState(false);
  const size = 56;
  const radius = shape === "circle" ? "50%" : "var(--radius-lg)";

  return (
    <div>
      {label && (
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 6 }}>{label}</label>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          type="button"
          onClick={() => setOpen(true)}
          title="Click to choose or upload an icon"
          style={{
            width: size, height: size, borderRadius: radius, padding: 0, cursor: "pointer",
            border: "1px dashed var(--border-strong)", background: "var(--surface-sunken)",
            display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", flexShrink: 0,
          }}
        >
          {value ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={value} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <ImageIcon size={20} color="var(--text-tertiary)" />
          )}
        </button>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <Btn variant="ghost" size="sm" onClick={() => setOpen(true)}>{value ? "Change" : "Add icon"}</Btn>
          {value && (
            <Btn variant="ghost" size="sm" onClick={() => onChange(null)} style={{ color: "var(--danger-text)" }}>
              Remove
            </Btn>
          )}
        </div>
      </div>
      {open && (
        <IconPickerModal
          context={context}
          onClose={() => setOpen(false)}
          onSelect={url => { onChange(url); setOpen(false); }}
        />
      )}
    </div>
  );
}

function IconPickerModal({
  context, onClose, onSelect,
}: {
  context: IconLibraryContext;
  onClose: () => void;
  onSelect: (url: string) => void;
}) {
  const [tab, setTab] = useState<"upload" | "existing">("upload");
  return (
    <Modal open onClose={onClose} title="Choose an icon" size="md">
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 14 }}>
        {(["upload", "existing"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{
              padding: "8px 12px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer",
            }}>
            {t === "upload" ? "Upload New" : "Choose Existing"}
          </button>
        ))}
      </div>
      {tab === "upload"
        ? <UploadTab context={context} onSelect={onSelect} />
        : <ExistingTab context={context} onSelect={onSelect} />}
    </Modal>
  );
}

function UploadTab({ context, onSelect }: { context: IconLibraryContext; onSelect: (url: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    if (!file.type.startsWith("image/")) { setError("Please choose an image file."); return; }
    if (file.size > 2 * 1024 * 1024) { setError("Image must be 2 MB or smaller."); return; }
    setUploading(true);
    try {
      const asset: MediaAsset = await iconLibraryApi.upload(file, context);
      const url = asset.public_url || asset.preview_url;
      if (!url) throw new Error("Upload succeeded but no URL was returned.");
      onSelect(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => {
          e.preventDefault(); setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "var(--brand)" : "var(--border-strong)"}`,
          borderRadius: "var(--radius-lg)", padding: "32px 16px", textAlign: "center", cursor: "pointer",
          background: dragOver ? "var(--accent-muted)" : "var(--surface-sunken)",
        }}
      >
        <Upload size={22} color="var(--text-tertiary)" style={{ marginBottom: 8 }} />
        <p style={{ fontSize: 13, fontWeight: 600, margin: "0 0 2px" }}>
          {uploading ? "Uploading…" : "Drag & drop an image, or click to browse"}
        </p>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>PNG, JPG, WEBP or GIF — up to 2 MB</p>
        <input
          ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }}
        />
      </div>
      {error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "10px 0 0" }}>{error}</p>}
    </div>
  );
}

function ExistingTab({ context, onSelect }: { context: IconLibraryContext; onSelect: (url: string) => void }) {
  const lib = useApi(useCallback(() => iconLibraryApi.list(context), [context]));
  const items = lib.data?.items ?? [];

  if (lib.loading) return <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>;
  if (items.length === 0) {
    return <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No icons uploaded yet for this type — use "Upload New".</p>;
  }
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(64px, 1fr))", gap: 10, maxHeight: 320, overflowY: "auto" }}>
      {items.map(a => {
        const url = a.public_url || a.preview_url;
        if (!url) return null;
        return (
          <button
            key={a.id} type="button" onClick={() => onSelect(url)} title={a.file_name_original}
            style={{
              width: 64, height: 64, padding: 0, borderRadius: "var(--radius-lg)", cursor: "pointer",
              border: "1px solid var(--border)", background: "var(--surface)", overflow: "hidden", position: "relative",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </button>
        );
      })}
    </div>
  );
}
