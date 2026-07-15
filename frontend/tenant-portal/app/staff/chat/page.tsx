"use client";
/**
 * MODULE-L5-19 — Staff (technician) chat thread list.
 *
 * The technician on a job needs to message the customer, and staff_chat_router
 * (/v1/staff/chat) exposes it — but staff had no chat surface at all. This lists
 * the tenant's conversations the technician can see (tenant-scoped since
 * MODULE-L5-14) and links into each.
 */
import React, { useCallback } from "react";
import { useRouter } from "next/navigation";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { staffChatApi } from "../../../lib/api";

const RECORD_LABEL: Record<string, string> = {
  service_booking: "Booking", service_job: "Job", complaint: "Complaint",
};

export default function StaffChatPage() {
  const router = useRouter();
  const threads = useApi(useCallback(() => staffChatApi.listThreads(), []));

  return (
    <StaffLayout activeNav="chat">
      <h1 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px" }}>Messages</h1>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 20px" }}>
        Conversations with customers for your team&apos;s jobs.
      </p>

      {threads.loading ? (
        <Skeleton />
      ) : (threads.data ?? []).length === 0 ? (
        <EmptyState title="No conversations" description="Customer messages will appear here." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {(threads.data ?? []).map(t => (
            <Card key={t.id} onClick={() => router.push(`/staff/chat/${t.id}`)}
              style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600 }}>
                  {RECORD_LABEL[t.record_type] ?? t.record_type} · #{t.thread_number}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
                  {t.last_message_at ? `Last message ${new Date(t.last_message_at).toLocaleString()}` : "No messages yet"}
                </div>
              </div>
              <span style={{ color: "var(--text-tertiary)" }}>›</span>
            </Card>
          ))}
        </div>
      )}
    </StaffLayout>
  );
}
