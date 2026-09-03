"use client";
/**
 * ProfilePhotoUploader — Phase 0B (Tenant Portal)
 *
 * ownerType:
 *   "admin" | "provider_user" | "staff" → POST /v1/me/profile-photo
 *   "provider_business"                 → POST /v1/provider/profile/logo
 *   "provider_shop"                     → POST /v1/provider/profile/shop-photo
 *   "staff_own"                         → POST /v1/staff/profile/photo
 *   "staff_managed"                     → POST /v1/media/upload (staff_profile_photo)
 *   "customer"                          → POST /v1/customer/profile/photo
 *
 * Every owner type goes through the same picker → validate → crop → upload
 * flow (see ImageCropModal): the file the server receives is always a cropped,
 * correctly sized image, never the raw camera original.
 */
import React, { useRef, useState } from "react";
import { Camera, Trash2, Upload, X, Loader } from "lucide-react";
import { mediaAssetApi, type MediaAsset } from "../../lib/api";
import {
  ImageCropModal, CROP_PRESETS, CROP_ACCEPT, validateImageFile, type CropSpec,
} from "../media/ImageCropModal";

const _MEDIA_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("/")) return `${_MEDIA_BASE}${url}`;
  return url;
}

const PALETTE = [
  { bg: "#CCFBF1", text: "#0F766E" },
  { bg: "#dcfce7", text: "#166534" },
  { bg: "#fef9c3", text: "#854d0e" },
  { bg: "#fce7f3", text: "#9d174d" },
  { bg: "#ede9fe", text: "#5b21b6" },
  { bg: "#ffedd5", text: "#9a3412" },
];
function hashPalette(s: string) { return [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % PALETTE.length, 0); }
function initials(name?: string | null) {
  if (!name) return "?";
  return name.split(/\s+/).map(w => w[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
}

const SIZE_PX: Record<string, number> = { sm: 56, md: 80, lg: 110, xl: 140 };

const ERROR_MAP: Record<string, string> = {
  MEDIA_FILE_REQUIRED: "Please choose a file.",
  MEDIA_FILE_TOO_LARGE: "File is too large. Please choose a smaller image.",
  MEDIA_TYPE_NOT_ALLOWED: "This file type is not allowed. Use JPEG or PNG.",
  MEDIA_EXTENSION_NOT_ALLOWED: "This file extension is not allowed.",
  MEDIA_STORAGE_NOT_CONFIGURED: "Upload service is not configured. Contact support.",
  MEDIA_ACCESS_DENIED: "You do not have permission to update this photo.",
  MEDIA_TENANT_SCOPE_VIOLATION: "You do not have permission to update this photo.",
  MEDIA_CUSTOMER_SCOPE_VIOLATION: "You do not have permission to update this photo.",
};
function friendlyError(code?: string, fallback = "Upload failed. Please try again.") {
  return code ? (ERROR_MAP[code] ?? fallback) : fallback;
}

export type OwnerType =
  | "admin" | "provider_user" | "provider_business" | "provider_shop"
  | "staff" | "staff_own" | "staff_managed" | "customer";

/**
 * Crop rules per destination. The size ceilings match the server-side
 * CONTEXT_RULES entries these uploads land in, so a file the picker accepts is
 * never rejected later by the media engine.
 */
function cropSpecFor(ownerType: OwnerType): CropSpec {
  if (ownerType === "provider_shop")     return CROP_PRESETS.cover;   // 10 MB, 3:1 banner
  if (ownerType === "provider_business") return CROP_PRESETS.logo;    // 5 MB, square
  return CROP_PRESETS.avatar;                                         // 5 MB, square
}

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
  const [previewUrl, setPreviewUrl] = useState<string | null>(resolveMediaUrl(currentPreviewUrl) ?? null);
  const [mediaId,    setMediaId]    = useState<string | null>(currentMediaId ?? null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [hover,      setHover]      = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const spec    = cropSpecFor(ownerType);
  const isCover = spec.shape === "wide";

  // Sync when parent async-loads profile data and passes down a real URL
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
      switch (ownerType) {
        case "provider_business":
          asset = await mediaAssetApi.uploadBusinessLogo(file); break;
        case "provider_shop":
          asset = await mediaAssetApi.uploadShopPhoto(file); break;
        case "staff_own":
          asset = await mediaAssetApi.uploadStaffPhoto(file); break;
        case "staff_managed":
          // A manager uploading on a team member's behalf — the photo is owned
          // by the tenant until the member record is saved with its URL.
          //
          // Uploaded PUBLIC on purpose. A private asset gets no public_url, so
          // its preview_url falls back to /v1/media/{id}/view, which is behind
          // get_current_user — and an <img> tag cannot send a bearer token, so
          // the avatar 401s and silently renders as initials forever. Every
          // other avatar setter (user photo, business logo, shop photo) already
          // uploads with is_public=True for exactly this reason.
          asset = await mediaAssetApi.upload("staff_profile_photo", "tenant", ownerId ?? "", file, true); break;
        case "customer":
          asset = await mediaAssetApi.upload("customer_profile_photo", "user", ownerId ?? "self", file, false); break;
        default:
          asset = await mediaAssetApi.uploadProfilePhoto(file);
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
    setError(null);
    setLoading(true);
    try {
      switch (ownerType) {
        case "provider_business":
          if (mediaId) await mediaAssetApi.removeBusinessLogo(mediaId); break;
        case "provider_shop":
          if (mediaId) await mediaAssetApi.removeShopPhoto(mediaId); break;
        case "staff_own":
          await mediaAssetApi.removeStaffPhoto(); break;
        case "staff_managed":
          // No dedicated endpoint: the asset itself is what was created.
          if (mediaId) await mediaAssetApi.delete(mediaId); break;
        default:
          await mediaAssetApi.removeProfilePhoto();
      }
      setPreviewUrl(null);
      setMediaId(null);
      onRemoved?.();
    } catch (err: unknown) {
      const e = err as { code?: string; message?: string };
      // The asset is already gone (stale tab, or it was removed elsewhere).
      // Reporting that as a failure leaves the image on screen with a Remove
      // button that can never succeed -- treat it as removed instead.
      if (e.code === "NOT_FOUND") {
        setPreviewUrl(null);
        setMediaId(null);
        onRemoved?.();
      } else {
        setError(friendlyError(e.code, e.message));
      }
    } finally {
      setLoading(false);
    }
  }

  /**
   * Picker gate: reject unusable files here, with a specific reason, instead of
   * uploading them and surfacing a generic server error.
   */
  async function handlePicked(file: File) {
    setError(null);
    const check = await validateImageFile(file, spec);
    if (!check.ok) { setError(check.error ?? "That image cannot be used."); return; }
    setPendingFile(file);
  }

  // A cover photo is a banner, so preview it as one rather than as a circle.
  const frameW = isCover ? Math.round(px * spec.aspect) : px;
  const frameH = px;

  const frameStyle: React.CSSProperties = {
    width: frameW, height: frameH,
    borderRadius: isCover ? 10 : "50%",
    position: "relative", flexShrink: 0,
    border: "2px solid var(--border)",
    overflow: "hidden", cursor: disabled ? "default" : "pointer",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
    transition: "box-shadow 0.15s",
    ...(hover && !disabled ? { boxShadow: "0 2px 10px rgba(0,0,0,0.18)" } : {}),
  };

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
      <div
        style={frameStyle}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={() => !disabled && !loading && fileRef.current?.click()}
        title={disabled ? undefined : "Click to change photo"}
      >
        {hasPhoto && previewUrl ? (
          <img
            src={previewUrl}
            alt={displayName ?? "Photo"}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            // Silently blanking here made a stored-but-unreachable photo look
            // identical to "no photo uploaded", which hid a real bug for a long
            // time. Say so instead.
            onError={() => {
              setPreviewUrl(null);
              setError("The photo uploaded but could not be displayed. Please try again or contact support.");
            }}
          />
        ) : isCover ? (
          // Initials read as an avatar; a banner placeholder needs to say what
          // it is instead.
          <div style={{
            width: "100%", height: "100%",
            background: `linear-gradient(135deg, ${pal.bg} 0%, ${pal.text}22 100%)`,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6,
            color: pal.text,
          }}>
            <Camera size={px * 0.22}/>
            <span style={{ fontSize: 12, fontWeight: 600 }}>Add a cover photo</span>
          </div>
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
        {loading && (
          <div style={{
            position: "absolute", inset: 0, background: "rgba(255,255,255,0.75)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Loader size={px * 0.28} style={{ animation: "spin 0.9s linear infinite", color: "var(--accent)" }}/>
          </div>
        )}
        {!loading && !disabled && hover && (
          <div style={{
            position: "absolute", inset: 0, background: "rgba(0,0,0,0.42)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Camera size={px * 0.28} color="white"/>
          </div>
        )}
      </div>

      {!disabled && (
        <div style={{ display: "flex", gap: 6 }}>
          <button
            onClick={() => !loading && fileRef.current?.click()}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: 4, padding: "5px 10px",
              fontSize: 12, fontWeight: 500, borderRadius: 7,
              border: "1px solid var(--border)", background: "var(--surface)",
              color: "var(--text-secondary)", cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.12s",
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "var(--surface-sunken)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "var(--surface)"; }}
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
                border: "1px solid var(--danger-border)",
                background: "var(--danger-bg)", color: "var(--danger)",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              <Trash2 size={11}/>Remove
            </button>
          )}
        </div>
      )}

      {error && (
        <div style={{
          display: "flex", alignItems: "flex-start", gap: 6,
          background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          borderRadius: 7, padding: "6px 10px", maxWidth: 240,
        }}>
          <X size={12} style={{ flexShrink: 0, marginTop: 1, color: "var(--danger)" }}/>
          <span style={{ fontSize: 12, color: "var(--danger)", lineHeight: 1.4 }}>{error}</span>
        </div>
      )}

      <input
        ref={fileRef}
        type="file"
        accept={CROP_ACCEPT}
        style={{ display: "none" }}
        onChange={e => { const f = e.target.files?.[0]; if (f) handlePicked(f); e.target.value = ""; }}
      />

      <ImageCropModal
        open={Boolean(pendingFile)}
        file={pendingFile}
        spec={spec}
        title={isCover ? "Adjust cover photo" : "Adjust photo"}
        onCancel={() => setPendingFile(null)}
        onConfirm={async cropped => { setPendingFile(null); await handleFile(cropped); }}
      />
    </div>
  );
}

export function DefaultAvatar({ name, src, size = 36 }: { name?: string | null; src?: string | null; size?: number }) {
  const [imgErr, setImgErr] = useState(false);
  const pal = PALETTE[hashPalette(name ?? "?")];
  const ini = initials(name);
  const resolvedSrc = resolveMediaUrl(src);
  if (resolvedSrc && !imgErr) {
    return (
      <div style={{ width: size, height: size, borderRadius: "50%", overflow: "hidden", flexShrink: 0, border: "2px solid var(--border)" }}>
        <img src={resolvedSrc} alt={name ?? ""} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={() => setImgErr(true)}/>
      </div>
    );
  }
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: `linear-gradient(135deg, ${pal.bg} 0%, ${pal.text}33 100%)`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.35, fontWeight: 700, color: pal.text, letterSpacing: "-0.02em",
      border: "2px solid var(--border)",
    }}>
      {ini}
    </div>
  );
}
