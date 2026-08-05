"use client";
// COMPLAINT-CONSOLIDATION: Home Services Complaint 360 -- the same
// ComplaintInspector used by the central queue's persistent preview,
// rendered full-page. Vertical hardcoded to "home-services" (never a
// client-supplied param), consistent with the rest of Home Services.
import React from "react";
import { useParams, useRouter } from "next/navigation";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { ComplaintInspector } from "../../../../../components/directory/VerticalComplaintWorkspace";

export default function HomeServicesComplaint360Page() {
  const params = useParams();
  const router = useRouter();
  const complaintId = String(params.complaint_id);

  return (
    <AdminLayout>
      <div style={{ padding: "0 4px", maxWidth: 900 }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>
          Operations / Home Services / Complaints / {complaintId.slice(0, 8)}
        </p>
        <button onClick={() => router.push("/admin/home-services/complaints")}
          style={{ fontSize: 12, color: "var(--text-tertiary)", background: "none", border: "none", cursor: "pointer", padding: 0, marginBottom: 12 }}>
          ← Back to Complaints
        </button>
        <ComplaintInspector vertical="home-services" complaintId={complaintId} fullPage/>
      </div>
    </AdminLayout>
  );
}
