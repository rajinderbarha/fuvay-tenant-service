"use client";
/**
 * DESIGN PHASE UX-03 — shared operational-workspace pattern: a
 * multi-column live-ops layout (queue / detail / side context). Backs the
 * Assignment/Dispatch workspace and can back future operational surfaces.
 * Does NOT claim AI-based matching — only surfaces availability, workload,
 * skills, and conflicts as data, matching what the repo actually implements.
 */
import React from "react";
import { PageHeader, Card } from "@serviceos/design-system";

export function OperationalWorkspace({
  title,
  description,
  queue,
  detail,
  sideContext,
}: {
  title: string;
  description?: string;
  queue: React.ReactNode;
  detail: React.ReactNode;
  sideContext?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <PageHeader title={title} description={description} />
      <div style={{ display: "grid", gridTemplateColumns: sideContext ? "18rem 1fr 18rem" : "18rem 1fr", gap: "1rem" }}>
        <Card title="Queue" padding="sm">{queue}</Card>
        <Card title="Detail">{detail}</Card>
        {sideContext && <Card title="Context" padding="sm">{sideContext}</Card>}
      </div>
    </div>
  );
}
