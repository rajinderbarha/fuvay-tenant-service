"use client";
import React from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, EmptyState } from "../../../components/shared/ui";
import { History } from "lucide-react";

export default function StaffActivityPage() {
  return (
    <StaffLayout activeNav="activity">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Activity</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Your own account activity log.
        </p>
      </div>
      <Card padding={0}>
        <EmptyState
          icon={<History/>}
          title="Self-service activity history is not yet available in this app."
          description="No dedicated staff-scoped audit/activity endpoint exists yet — only platform-admin-level audit search endpoints exist today. Contact your tenant admin if you need your activity history."
        />
      </Card>
    </StaffLayout>
  );
}
