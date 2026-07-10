"use client";
import React from "react";
import { StaffLayout } from "../../../../components/layout/StaffLayout";
import { Card, EmptyState } from "../../../../components/shared/ui";
import { ShieldCheck } from "lucide-react";

export default function StaffSessionsPage() {
  return (
    <StaffLayout activeNav="sessions">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Security / Sessions</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Review and manage your active sign-in sessions.
        </p>
      </div>
      <Card padding={0}>
        <EmptyState
          icon={<ShieldCheck/>}
          title="Self-service session management is not yet available in this app."
          description="Viewing and revoking your own active sessions/devices has not been built yet. Contact your tenant admin if you need a session revoked."
        />
      </Card>
    </StaffLayout>
  );
}
