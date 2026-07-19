"use client";
import { useState } from "react";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { PartsRequestList } from "../../../../components/ux04/PartsRequestList";
import { partsRequestListFixture, partsRequestListEmptyFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04B — Parts Request list, with a state switcher
 * demonstrating multiple-row / empty / loading / error states using the
 * same real component (not 4 separate pages). */
export default function PartsRequestListPage() {
  const [state, setState] = useState<"multi" | "empty" | "loading" | "error">("multi");
  return (
    <PageShell>
      <PageHeader title="Parts Requests" description="ServiceJob-scoped only. Provider-side approve/reject only — no field_ops.Job link, no technician install authority." />
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
        {(["multi", "empty", "loading", "error"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setState(s)}
            style={{
              fontSize: "0.75rem",
              padding: "0.25rem 0.625rem",
              borderRadius: "var(--radius-sm)",
              border: `1px solid ${state === s ? "var(--brand)" : "var(--border)"}`,
              background: "none",
              color: state === s ? "var(--brand)" : "var(--text-secondary)",
            }}
          >
            {s}
          </button>
        ))}
      </div>
      <PartsRequestList
        items={state === "multi" ? partsRequestListFixture : state === "empty" ? partsRequestListEmptyFixture : []}
        loading={state === "loading"}
        error={state === "error" ? "Network error — could not reach the parts request service." : null}
      />
    </PageShell>
  );
}
