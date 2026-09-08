"use client";
import Link from "next/link";

/** These are navigation links, never an automatic upload or resubmission. */
export function CorrectionActions({ status }: { status: string }) {
  if (status !== "changes_requested") return null;
  return <section aria-label="Application corrections" style={{ margin: "16px 0", padding: 16, border: "1px solid var(--warning-border)", borderRadius: 12, background: "var(--warning-bg)" }}>
    <p style={{ margin: "0 0 10px", fontSize: 13, color: "var(--text-primary)" }}>
      Your setup is open for corrections. Upload requested evidence in Documents (use the GST registration certificate slot for GST), then review and resubmit your application. Uploading alone does not resubmit it.
    </p>
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 13, fontWeight: 600 }}>
      <Link href="/tenant/home-services/setup/documents">Upload or replace documents</Link>
      <Link href="/tenant/home-services/setup/overview">Edit setup</Link>
      <Link href="/tenant/home-services/setup/review">Review &amp; resubmit</Link>
    </div>
  </section>;
}
