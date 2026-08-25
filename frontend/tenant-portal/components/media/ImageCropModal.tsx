"use client";
/**
 * ImageCropModal — shared photo picker/crop step for profile, technician and
 * cover-photo uploads.
 *
 * Every photo upload surface used to hand the raw camera file straight to the
 * server, so a 4000x3000 portrait became an off-centre, badly framed avatar and
 * the only feedback about a too-large file came back as a 4xx from the API.
 * This component puts the framing decision in front of the upload:
 *
 *   1. `validateImageFile` — type / size / dimension rules checked locally,
 *      against the same limits the media engine enforces server-side
 *      (app/engines/media/validation.py CONTEXT_RULES).
 *   2. Crop + zoom — drag to pan, slider / buttons / wheel to zoom, inside a
 *      frame shaped like the real destination (circle for people, wide banner
 *      for storefront covers).
 *   3. Instant preview — the exact pixels that will be uploaded, rendered at
 *      the sizes the photo actually appears at in the product.
 *
 * The confirmed output is a fresh, correctly sized File — never the original —
 * so the bytes that reach the server are already the thumbnail.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Loader, Move, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { Btn, Modal } from "../shared/ui";

export type CropShape = "circle" | "square" | "wide";

export interface CropSpec {
  shape: CropShape;
  /** width / height of the crop frame and of the exported image. */
  aspect: number;
  /** Exported pixel width. Height is derived from `aspect`. */
  outputWidth: number;
  /** Smallest source image we accept, so we never upscale a tiny thumbnail. */
  minWidth: number;
  minHeight: number;
  /** Mirrors the server-side per-context limit. */
  maxSizeMB: number;
}

/** Types the media engine accepts for image contexts, minus GIF (not croppable
 *  without losing animation, and never wanted for a profile photo). */
export const CROP_ACCEPT = "image/jpeg,image/png,image/webp";
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export const CROP_PRESETS = {
  /** People: staff, technicians, admins, customers. */
  avatar: { shape: "circle", aspect: 1, outputWidth: 512,  minWidth: 200, minHeight: 200, maxSizeMB: 5  },
  /** Business logo — square source, displayed in a circle. */
  logo:   { shape: "circle", aspect: 1, outputWidth: 512,  minWidth: 200, minHeight: 200, maxSizeMB: 5  },
  /** Storefront / cover banner. */
  cover:  { shape: "wide",   aspect: 3, outputWidth: 1500, minWidth: 900, minHeight: 300, maxSizeMB: 10 },
} satisfies Record<string, CropSpec>;

export type CropPresetName = keyof typeof CROP_PRESETS;

// ── Validation ────────────────────────────────────────────────────────────────

export interface ImageValidation {
  ok: boolean;
  error?: string;
  width?: number;
  height?: number;
}

function formatMB(bytes: number) {
  return (bytes / (1024 * 1024)).toFixed(bytes < 1024 * 1024 ? 2 : 1);
}

/** Reads the image header to get real dimensions. Resolves null if undecodable. */
function probeDimensions(file: File): Promise<{ width: number; height: number } | null> {
  return new Promise(resolve => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
      URL.revokeObjectURL(url);
    };
    img.onerror = () => { resolve(null); URL.revokeObjectURL(url); };
    img.src = url;
  });
}

/**
 * Enforces the picker rules before anything is uploaded: accepted image type,
 * size ceiling, and a minimum source resolution.
 */
export async function validateImageFile(file: File, spec: CropSpec): Promise<ImageValidation> {
  if (!ACCEPTED_TYPES.has(file.type)) {
    return { ok: false, error: "Unsupported file type. Choose a JPG, PNG or WebP image." };
  }
  const maxBytes = spec.maxSizeMB * 1024 * 1024;
  if (file.size > maxBytes) {
    return { ok: false, error: `This image is ${formatMB(file.size)} MB. The maximum is ${spec.maxSizeMB} MB.` };
  }
  const dims = await probeDimensions(file);
  if (!dims) {
    return { ok: false, error: "That image could not be read. It may be corrupted — try another file." };
  }
  if (dims.width < spec.minWidth || dims.height < spec.minHeight) {
    return {
      ok: false,
      error: `This image is ${dims.width}x${dims.height}px. It needs to be at least ${spec.minWidth}x${spec.minHeight}px to stay sharp.`,
      ...dims,
    };
  }
  return { ok: true, ...dims };
}

// ── Crop geometry ─────────────────────────────────────────────────────────────

interface Offset { x: number; y: number }

/** Scale at which the image exactly covers the frame — the zoom=1 baseline. */
function coverScale(img: HTMLImageElement, fw: number, fh: number) {
  return Math.max(fw / img.naturalWidth, fh / img.naturalHeight);
}

/** Keeps the frame fully covered: the image can never be dragged past an edge. */
function clampOffset(img: HTMLImageElement, zoom: number, fw: number, fh: number, off: Offset): Offset {
  const s = coverScale(img, fw, fh) * zoom;
  const dw = img.naturalWidth * s;
  const dh = img.naturalHeight * s;
  return {
    x: Math.min(0, Math.max(fw - dw, off.x)),
    y: Math.min(0, Math.max(fh - dh, off.y)),
  };
}

function centerOffset(img: HTMLImageElement, zoom: number, fw: number, fh: number): Offset {
  const s = coverScale(img, fw, fh) * zoom;
  return { x: (fw - img.naturalWidth * s) / 2, y: (fh - img.naturalHeight * s) / 2 };
}

const MAX_ZOOM = 4;

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob | null> {
  return new Promise(resolve => canvas.toBlob(resolve, type, quality));
}

function renameFile(name: string, ext: string) {
  const base = name.replace(/\.[^.]+$/, "") || "photo";
  return `${base}.${ext}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

export interface ImageCropModalProps {
  open: boolean;
  /** Source file chosen in the picker. Already passed `validateImageFile`. */
  file: File | null;
  spec: CropSpec;
  title?: string;
  /** Receives the cropped, resized File. May be async — the modal shows a
   *  spinner and stays open until it settles, so upload errors surface here. */
  onConfirm: (cropped: File) => void | Promise<void>;
  onCancel: () => void;
}

export function ImageCropModal({ open, file, spec, title, onConfirm, onCancel }: ImageCropModalProps) {
  const isWide = spec.aspect >= 2;
  const FRAME_W = isWide ? 468 : 288;
  const FRAME_H = Math.round(FRAME_W / spec.aspect);

  const [img, setImg]       = useState<HTMLImageElement | null>(null);
  const [zoom, setZoom]     = useState(1);
  const [offset, setOffset] = useState<Offset>({ x: 0, y: 0 });
  const [busy, setBusy]     = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const dragRef       = useRef<{ pointerId: number; startX: number; startY: number; origin: Offset } | null>(null);
  const bigPreviewRef = useRef<HTMLCanvasElement>(null);
  const smallPrevRef  = useRef<HTMLCanvasElement>(null);

  // Decode the chosen file. The object URL stays alive for as long as the modal
  // is showing this file; cleanup only runs on close or on a new file.
  useEffect(() => {
    if (!open || !file) { setImg(null); return; }
    setError(null);
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      setImg(image);
      setZoom(1);
      setOffset(centerOffset(image, 1, FRAME_W, FRAME_H));
    };
    image.onerror = () => setError("That image could not be read. Try another file.");
    image.src = url;
    return () => URL.revokeObjectURL(url);
  }, [open, file, FRAME_W, FRAME_H]);

  /** Zoom about the frame centre, so the subject does not drift while zooming. */
  const applyZoom = useCallback((next: number) => {
    if (!img) return;
    const z = Math.min(MAX_ZOOM, Math.max(1, next));
    setOffset(prev => {
      const ratio = z / zoom;
      const cx = FRAME_W / 2, cy = FRAME_H / 2;
      return clampOffset(img, z, FRAME_W, FRAME_H, {
        x: cx - (cx - prev.x) * ratio,
        y: cy - (cy - prev.y) * ratio,
      });
    });
    setZoom(z);
  }, [img, zoom, FRAME_W, FRAME_H]);

  /** Paints the exact crop region into `canvas` at `outW` pixels wide. */
  const paint = useCallback((canvas: HTMLCanvasElement, outW: number) => {
    if (!img) return;
    const outH = Math.round(outW / spec.aspect);
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const s = coverScale(img, FRAME_W, FRAME_H) * zoom;
    ctx.clearRect(0, 0, outW, outH);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(
      img,
      -offset.x / s, -offset.y / s, FRAME_W / s, FRAME_H / s,
      0, 0, outW, outH,
    );
  }, [img, zoom, offset, spec.aspect, FRAME_W, FRAME_H]);

  // Live preview — redraws on every pan/zoom frame.
  useEffect(() => {
    if (!img) return;
    if (bigPreviewRef.current) paint(bigPreviewRef.current, isWide ? 300 : 96);
    if (smallPrevRef.current)  paint(smallPrevRef.current,  isWide ? 140 : 40);
  }, [img, paint, isWide]);

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (!img) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = { pointerId: e.pointerId, startX: e.clientX, startY: e.clientY, origin: offset };
  }
  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const d = dragRef.current;
    if (!d || !img || d.pointerId !== e.pointerId) return;
    setOffset(clampOffset(img, zoom, FRAME_W, FRAME_H, {
      x: d.origin.x + (e.clientX - d.startX),
      y: d.origin.y + (e.clientY - d.startY),
    }));
  }
  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    if (dragRef.current?.pointerId === e.pointerId) dragRef.current = null;
  }

  function handleReset() {
    if (!img) return;
    setZoom(1);
    setOffset(centerOffset(img, 1, FRAME_W, FRAME_H));
  }

  async function handleConfirm() {
    if (!img || !file) return;
    setBusy(true);
    setError(null);
    try {
      const canvas = document.createElement("canvas");
      paint(canvas, spec.outputWidth);

      const maxBytes = spec.maxSizeMB * 1024 * 1024;
      // PNG sources keep transparency; anything else exports as JPEG.
      let blob = file.type === "image/png"
        ? await canvasToBlob(canvas, "image/png")
        : await canvasToBlob(canvas, "image/jpeg", 0.92);

      // A detailed PNG crop can still exceed the context limit. Flatten onto
      // white and step the JPEG quality down until it fits.
      if (blob && blob.size > maxBytes) {
        const flat = document.createElement("canvas");
        flat.width = canvas.width;
        flat.height = canvas.height;
        const fctx = flat.getContext("2d");
        if (fctx) {
          fctx.fillStyle = "#ffffff";
          fctx.fillRect(0, 0, flat.width, flat.height);
          fctx.drawImage(canvas, 0, 0);
          for (const q of [0.9, 0.8, 0.7, 0.6, 0.5]) {
            const attempt = await canvasToBlob(flat, "image/jpeg", q);
            if (!attempt) break;
            blob = attempt;
            if (attempt.size <= maxBytes) break;
          }
        }
      }

      if (!blob) {
        setError("The cropped image could not be prepared. Please try again.");
        return;
      }
      if (blob.size > maxBytes) {
        setError(`The cropped image is still ${formatMB(blob.size)} MB. Try a smaller source image.`);
        return;
      }

      const ext = blob.type === "image/png" ? "png" : "jpg";
      await onConfirm(new File([blob], renameFile(file.name, ext), { type: blob.type }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the cropped photo.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  const s  = img ? coverScale(img, FRAME_W, FRAME_H) * zoom : 1;
  const dw = img ? img.naturalWidth * s : 0;
  const dh = img ? img.naturalHeight * s : 0;
  const radius = spec.shape === "circle" ? "50%" : 10;

  return (
    <Modal
      open={open}
      onClose={busy ? () => {} : onCancel}
      title={title ?? "Adjust photo"}
      size={isWide ? "lg" : "md"}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          <Move size={13}/>
          Drag to reposition, then zoom until the {spec.shape === "wide" ? "banner" : "face"} fills the frame.
        </p>

        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          {/* Crop stage */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
              onWheel={e => { if (img) applyZoom(zoom - Math.sign(e.deltaY) * 0.15); }}
              style={{
                position: "relative", width: FRAME_W, height: FRAME_H,
                borderRadius: 10, overflow: "hidden", touchAction: "none",
                background: "var(--surface-sunken)",
                cursor: img ? "grab" : "default", userSelect: "none",
              }}
            >
              {img ? (
                <img
                  src={img.src}
                  alt=""
                  draggable={false}
                  style={{
                    position: "absolute", left: offset.x, top: offset.y,
                    width: dw, height: dh, maxWidth: "none", pointerEvents: "none",
                  }}
                />
              ) : (
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Loader size={22} style={{ animation: "spin 0.9s linear infinite", color: "var(--accent)" }}/>
                </div>
              )}
              {/* Dims everything outside the crop shape; clipped to the frame. */}
              <div style={{
                position: "absolute", inset: 0, pointerEvents: "none",
                borderRadius: radius,
                boxShadow: "0 0 0 9999px rgba(0,0,0,0.5), inset 0 0 0 2px rgba(255,255,255,0.9)",
              }}/>
            </div>

            {/* Zoom controls */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <button
                type="button" aria-label="Zoom out" disabled={!img || zoom <= 1}
                onClick={() => applyZoom(zoom - 0.25)}
                style={zoomBtnStyle(!img || zoom <= 1)}
              ><ZoomOut size={14}/></button>
              <input
                type="range" min={1} max={MAX_ZOOM} step={0.01} value={zoom}
                aria-label="Zoom" disabled={!img}
                onChange={e => applyZoom(Number(e.target.value))}
                style={{ flex: 1, accentColor: "var(--brand)" }}
              />
              <button
                type="button" aria-label="Zoom in" disabled={!img || zoom >= MAX_ZOOM}
                onClick={() => applyZoom(zoom + 0.25)}
                style={zoomBtnStyle(!img || zoom >= MAX_ZOOM)}
              ><ZoomIn size={14}/></button>
              <button
                type="button" aria-label="Reset crop" disabled={!img}
                onClick={handleReset}
                style={zoomBtnStyle(!img)}
              ><RotateCcw size={14}/></button>
            </div>
          </div>

          {/* Instant preview */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: 0 }}>
              Preview
            </p>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 12 }}>
              <canvas
                ref={bigPreviewRef}
                style={{
                  width: isWide ? 300 : 96, height: isWide ? 100 : 96,
                  borderRadius: spec.shape === "circle" ? "50%" : 8,
                  border: "1px solid var(--border)", background: "var(--surface-sunken)",
                  display: "block",
                }}
              />
              <canvas
                ref={smallPrevRef}
                style={{
                  width: isWide ? 140 : 40, height: isWide ? 47 : 40,
                  borderRadius: spec.shape === "circle" ? "50%" : 6,
                  border: "1px solid var(--border)", background: "var(--surface-sunken)",
                  display: "block",
                }}
              />
            </div>
            <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0, maxWidth: 220, lineHeight: 1.5 }}>
              Saved at {spec.outputWidth}x{Math.round(spec.outputWidth / spec.aspect)}px.
              JPG, PNG or WebP up to {spec.maxSizeMB} MB.
            </p>
          </div>
        </div>

        {error && (
          <div role="alert" style={{
            padding: "9px 12px", borderRadius: 8, fontSize: 12.5,
            background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)",
          }}>{error}</div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <Btn variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Btn>
          <Btn variant="primary" onClick={handleConfirm} loading={busy} disabled={!img}>Save photo</Btn>
        </div>
      </div>
    </Modal>
  );
}

function zoomBtnStyle(disabled: boolean): React.CSSProperties {
  return {
    display: "flex", alignItems: "center", justifyContent: "center",
    width: 30, height: 30, borderRadius: 8, flexShrink: 0,
    border: "1px solid var(--border)", background: "var(--surface)",
    color: disabled ? "var(--text-tertiary)" : "var(--text-secondary)",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1,
  };
}
