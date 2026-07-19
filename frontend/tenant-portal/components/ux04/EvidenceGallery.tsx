"use client";
/**
 * DESIGN PHASE UX-04A — read-only operational media/evidence gallery.
 * NEVER renders a storage key, signed URL, bucket name, or credential —
 * only `previewToken`/`label`/`kind`/`uploadedAt`/`sizeLabel` from
 * `MediaAssetFixture` (UX-03 type, reused unchanged).
 */
import React from "react";
import type { MediaAssetFixture } from "../../lib/ux03/types";

export function EvidenceGallery({ assets }: { assets: MediaAssetFixture[] }) {
  if (assets.length === 0) {
    return <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>No media attached.</p>;
  }
  return (
    <ul style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", listStyle: "none", padding: 0 }}>
      {assets.map((a) => (
        <li
          key={a.id}
          style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            padding: "0.5rem",
            width: "9rem",
            fontSize: "0.6875rem",
          }}
        >
          <div
            aria-label={`${a.kind} preview`}
            style={{ height: "5rem", background: "var(--surface-muted, var(--border))", borderRadius: "var(--radius-sm)", marginBottom: "0.375rem" }}
          />
          <p style={{ margin: 0, fontWeight: 600 }}>{a.label}</p>
          <p style={{ margin: 0, color: "var(--text-secondary)" }}>{a.kind} · {a.sizeLabel}</p>
          <p style={{ margin: 0, color: "var(--text-secondary)" }}>{a.uploadedAt}</p>
        </li>
      ))}
    </ul>
  );
}
