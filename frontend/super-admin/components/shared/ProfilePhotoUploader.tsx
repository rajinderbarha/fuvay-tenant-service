"use client";
/**
 * ProfilePhotoUploader — Phase 0B
 *
 * Renders a circular avatar with upload/replace/remove controls.
 * Calls the Media Engine API. No inline fetch — all calls via profilePhotoApi.
 *
 * ownerType determines which API endpoint is called:
 *   "admin"             → POST /v1/me/profile-photo
 *   "provider_user"     → POST /v1/me/profile-photo
 *   "staff"             → POST /v1/me/profile-photo
 *   "customer"          → POST /v1/customer/profile/photo (not used in admin portal)
 *   "provider_business" → POST /v1/provider/profile/logo
 *   "provider_shop"     → POST /v1/provider/profile/shop-photo
 */
import React, { useRef, useState } from "react";
import { Camera, Trash2, Upload, X, Loader } from "lucide-react";
import { profilePhotoApi, type MediaAsset } from "../../lib/api";

const _MEDIA_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("/")) return `${_MEDIA_BASE}${url}`;
  return url;
}

const PALETTE = [
  { bg: "#dbeafe", text: "#1e40af" },
  { bg: "#dcfce7", text: "#166534" },
  { bg: "#fef9c3", text: "#854d0e" },
  { bg: "#fce7f3", text: "#9d174d" },
  { bg: "#ede9fe", text: "#5b21b6" },
  { bg: "#ffedd5", text: "#9a3412" },
];

function hashPalette(name: string) {
  return [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % PALETTE.length, 0);
}

function initials(name?: string | null): string {
  if (!name) return "?";
  return name.split(/\s+/).map(w => w[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
}

const SIZE_PX: Record<string, number> = { sm: 56, md: 80, lg: 110, xl: 140 };

// Map backend error codes to friendly messages
const ERROR_MESSAGES: Record<string, string> = {
  MEDIA_FILE_REQUIRED: "Please choose a file.",
  MEDIA_FILE_TOO_LARGE: "File is too large. Please choose a smaller image.",
  MEDIA_TYPE_NOT_ALLOWED: "This file type is not allowed. Please choose a JPEG or PNG.",
  MEDIA_EXTENSION_NOT_ALLOWED: "This file extension is not allowed.",
  MEDIA_STORAGE_NOT_CONFIGURED: "Upload service is not configured. Contact support.",
  MEDIA_STORAGE_TIMEOUT:       "Upload timed out. Please try again with a smaller file.",
  MEDIA_STORAGE_ERROR:         "Storage service returned an error. Please try again.",
  MEDIA_STORAGE_UNAVAILABLE:   "Storage service is unavailable. Please try again shortly.",
  UPLOAD_TIMEOUT:              "Upload timed out. Please try again.",
  MEDIA_ACCESS_DENIED: "You do not have permission to update this photo.",
  MEDIA_TENANT_SCOPE_VIOLATION: "You do not have permission to update this photo.",
  MEDIA_CUSTOMER_SCOPE_VIOLATION: "You do not have permission to update this photo.",
};

function friendlyError(code?: string, fallback = "Upload failed. Please try again."): string {
  if (!code) return fallback;
  return ERROR_MESSAGES[code] ?? fallback;
}

export type OwnerType = "admin" | "provider_user" | "provider_business" | "provider_shop" | "staff" | "customer";

export interface ProfilePhotoUploaderProps {
  ownerType: OwnerType;
  ownerId?: string;
  currentMediaId?: string | null;
  currentPreviewUrl?: string | null;
  displayName?: string | null;
  size?: "sm" | "md" | "lg" | "xl";
  disabled?: boolean;
  onUploaded?: (media: MediaAsset) => void;
  onRemoved?: () => void;
}

export function ProfilePhotoUploader({
  ownerType,
  ownerId,
  currentPreviewUrl,
  currentMediaId,
  displayName,
  size = "md",
  disabled = false,
  onUploaded,
  onRemoved,
}: ProfilePhotoUploaderProps) {
  const [previewUrl, setPreviewUrl]   = useState<string | null>(resolveMediaUrl(currentPreviewUrl) ?? null);
  const [mediaId,    setMediaId]      = useState<string | null>(currentMediaId ?? null);
  const [loading,    setLoading]      = useState(false);
  const [error,      setError]        = useState<string | null>(null);
  const [hover,      setHover]        = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Sync when parent async-loads the profile and passes down a real URL
  React.useEffect(() => {
    setPreviewUrl(resolveMediaUrl(currentPreviewUrl) ?? null);
  }, [currentPreviewUrl]);
  React.useEffect(() => {
    setMediaId(currentMediaId ?? null);
  }, [currentMediaId]);

  const px        = SIZE_PX[size] ?? 80;
  const pal       = PALETTE[hashPalette(displayName ?? ownerType)];
  const ini       = initials(displayName);
  const hasPhoto  = Boolean(previewUrl);

  async function handleFile(file: File) {
    setError(null);
    setLoading(true);
    try {
      let asset: MediaAsset;
      if (ownerType === "provider_business") {
        asset = await profilePhotoApi.uploadAsset(file, "provider_business_logo", "tenant", ownerId, true);
      } else if (ownerType === "provider_shop") {
        asset = await profilePhotoApi.uploadAsset(file, "provider_shop_photo", "tenant", ownerId, true);
      } else {
        asset = await profilePhotoApi.uploadOwnPhoto(file);
      }
      setPreviewUrl(resolveMediaUrl(asset.preview_url ?? asset.public_url) ?? null);
      setMediaId(asset.id);
      onUploaded?.(asset);
    } catch (err: unknown) {
      const e = err as { code?: string; message?: string };
      setError(friendlyError(e.code, e.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleRemove() {
    if (!mediaId) return;
    setError(null);
    setLoading(true);
    try {
      if (ownerType === "provider_business" || ownerType === "provider_shop") {
        await profilePhotoApi.deleteAsset(mediaId);
      } else {
        await profilePhotoApi.removeOwnPhoto();
      }
      setPreviewUrl(null);
      setMediaId(null);
      onRemoved?.();
    } catch (err: unknown) {
      const e = err as { code?: string; message?: string };
      setError(friendlyError(e.code, e.message));
    } finally {
      setLoading(false);
    }
  }

  const circleStyle: React.CSSProperties = {
    width: px, height: px, borderRadius: "50%",
    position: "relative", flexShrink: 0,
    border: "2px solid var(--border, #e5e7eb)",
    overflow: "hidden", cursor: disabled ? "default" : "pointer",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
    transition: "box-shadow 0.15s",
    ...(hover && !disabled ? { boxShadow: "0 2px 10px rgba(0,0,0,0.18)" } : {}),
  };

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
      {/* Circle */}
      <div
        style={circleStyle}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={() => !disabled && !loading && fileRef.current?.click()}
        title={disabled ? undefined : "Click to change photo"}
      >
        {/* Photo or initials */}
        {hasPhoto && previewUrl ? (
          <img
            src={previewUrl}
            alt={displayName ?? "Profile photo"}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            onError={() => setPreviewUrl(null)}
          />
        ) : (
          <div style={{
            width: "100%", height: "100%",
            background: `linear-gradient(135deg, ${pal.bg} 0%, ${pal.text}22 100%)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: px * 0.3, fontWeight: 700, color: pal.text, letterSpacing: "-0.02em",
          }}>
            {ini}
          </div>
        )}

        {/* Loading spinner overlay */}
        {loading && (
          <div style={{
            position: "absolute", inset: 0,
            background: "rgba(255,255,255,0.75)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Loader size={px * 0.28} style={{ animation: "spin 0.9s linear infinite", color: "var(--accent, #3b82f6)" }}/>
          </div>
        )}

        {/* Hover camera overlay */}
        {!loading && !disabled && hover && (
          <div style={{
            position: "absolute", inset: 0,
            background: "rgba(0,0,0,0.42)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Camera size={px * 0.28} color="white"/>
          </div>
        )}
      </div>

      {/* Action buttons */}
      {!disabled && (
        <div style={{ display: "flex", gap: 6 }}>
          <button
            onClick={() => !loading && fileRef.current?.click()}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: 4, padding: "5px 10px",
              fontSize: 12, fontWeight: 500, borderRadius: 7,
              border: "1px solid var(--border, #e5e7eb)",
              background: "var(--surface, #fff)", color: "var(--text-secondary, #6b7280)",
              cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.12s, border-color 0.12s",
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "var(--surface-sunken, #f9fafb)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "var(--surface, #fff)"; }}
          >
            <Upload size={11}/>{hasPhoto ? "Replace" : "Upload"}
          </button>
          {hasPhoto && (
            <button
              onClick={handleRemove}
              disabled={loading}
              style={{
                display: "flex", alignItems: "center", gap: 4, padding: "5px 10px",
                fontSize: 12, fontWeight: 500, borderRadius: 7,
                border: "1px solid var(--danger-border, #fecaca)",
                background: "var(--danger-bg, #fef2f2)", color: "var(--danger, #dc2626)",
                cursor: loading ? "not-allowed" : "pointer",
                transition: "background 0.12s",
              }}
            >
              <Trash2 size={11}/>Remove
            </button>
          )}
        </div>
      )}

      {/* Inline error */}
      {error && (
        <div style={{
          display: "flex", alignItems: "flex-start", gap: 6,
          background: "var(--danger-bg, #fef2f2)", border: "1px solid var(--danger-border, #fecaca)",
          borderRadius: 7, padding: "6px 10px", maxWidth: 240,
        }}>
          <X size={12} style={{ flexShrink: 0, marginTop: 1, color: "var(--danger, #dc2626)" }}/>
          <span style={{ fontSize: 12, color: "var(--danger, #dc2626)", lineHeight: 1.4 }}>{error}</span>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        style={{ display: "none" }}
        onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }}
      />
    </div>
  );
}

/** Standalone default avatar (no upload). Useful in lists and topbars. */
export function DefaultAvatar({
  name,
  src,
  size = 36,
}: { name?: string | null; src?: string | null; size?: number }) {
  const [imgErr, setImgErr] = useState(false);
  const pal = PALETTE[hashPalette(name ?? "?")];
  const ini = initials(name);
  const resolvedSrc = resolveMediaUrl(src);

  if (resolvedSrc && !imgErr) {
    return (
      <div style={{ width: size, height: size, borderRadius: "50%", overflow: "hidden", flexShrink: 0, border: "2px solid var(--border, #e5e7eb)" }}>
        <img
          src={resolvedSrc}
          alt={name ?? ""}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          onError={() => setImgErr(true)}
        />
      </div>
    );
  }

  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: `linear-gradient(135deg, ${pal.bg} 0%, ${pal.text}33 100%)`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.35, fontWeight: 700, color: pal.text, letterSpacing: "-0.02em",
      border: "2px solid var(--border, #e5e7eb)",
    }}>
      {ini}
    </div>
  );
}
