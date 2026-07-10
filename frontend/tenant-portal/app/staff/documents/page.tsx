"use client";
import React from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, EmptyState } from "../../../components/shared/ui";
import { FileText } from "lucide-react";

export default function StaffDocumentsPage() {
  return (
    <StaffLayout activeNav="documents">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Documents</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Upload and track your verification documents.
        </p>
      </div>
      <Card padding={0}>
        <EmptyState
          icon={<FileText/>}
          title="Document upload is not yet available in this app."
          description="Self-service document upload and verification tracking for technicians has not been built yet. Contact your tenant admin if you need to submit documents."
        />
      </Card>
    </StaffLayout>
  );
}
