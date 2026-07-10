"use client";
import React from "react";
import { type MediaAsset } from "../../lib/api";
import { MediaPreview } from "./MediaPreview";

type MediaGalleryProps = {
  assets: MediaAsset[];
  onDeleted?: (id: string) => void;
  canDelete?: boolean;
  columns?: number;
  emptyMessage?: string;
};

export function MediaGallery({
  assets,
  onDeleted,
  canDelete = false,
  columns = 3,
  emptyMessage = "No files uploaded yet.",
}: MediaGalleryProps) {
  if (assets.length === 0) {
    return (
      <div style={{
        textAlign: "center", padding: "24px 0",
        color: "var(--text-tertiary)", fontSize: 13,
      }}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gap: 12,
    }}>
      {assets.map(asset => (
        <MediaPreview
          key={asset.id}
          asset={asset}
          onDeleted={onDeleted}
          canDelete={canDelete}
        />
      ))}
    </div>
  );
}
