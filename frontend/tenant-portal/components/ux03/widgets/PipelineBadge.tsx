"use client";
/**
 * DESIGN PHASE UX-03 — visually distinguishes the two separate pipelines:
 * Booking -> field_ops.Job  vs  ServiceBooking -> ServiceJob.
 * Every booking/job row and detail page must show this badge so pipeline
 * identity is never silently merged in the UI.
 */
import React from "react";
import type { PipelineKind } from "../../../lib/ux03/types";

const CONFIG: Record<PipelineKind, { label: string; sub: string; color: string }> = {
  booking_field_ops: { label: "Booking", sub: "field_ops.Job", color: "var(--info-text)" },
  service_booking_service_job: { label: "Service Job", sub: "ServiceJob", color: "var(--brand)" },
};

export function PipelineBadge({ pipeline, canonicalId }: { pipeline: PipelineKind; canonicalId: string }) {
  const c = CONFIG[pipeline];
  return (
    <span style={{ display: "inline-flex", flexDirection: "column", lineHeight: 1.2 }}>
      <span style={{ fontWeight: 600, fontSize: "0.75rem", color: c.color }}>{c.label}</span>
      <span style={{ fontSize: "0.625rem", color: "var(--text-secondary)" }} title="Canonical backend identity for this row — never merge across pipelines">
        {c.sub} · {canonicalId}
      </span>
    </span>
  );
}
