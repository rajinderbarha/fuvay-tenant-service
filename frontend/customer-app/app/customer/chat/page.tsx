"use client";
/**
 * MODULE-L5-14 — Customer chat thread list.
 *
 * The customer had no messaging surface at all, though every other role did and
 * customer_chat_router exposes the full API. This lists the customer's
 * conversations; the conversation view lives at /customer/chat/[threadId].
 */
import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import { listChatThreads, openChatThread, ChatThread } from "../../../lib/api/customer-chat";

const RECORD_LABEL: Record<string, string> = {
  service_booking: "Booking", service_job: "Service", complaint: "Complaint",
  coaching_appointment: "Appointment", real_estate_lead: "Enquiry",
};

export default function CustomerChatPage() {
  const router = useRouter();
  const params = useSearchParams();
  // Deep link from a booking: /customer/chat?record_type=service_booking&record_id=…
  const recordType = params?.get("record_type") ?? "";
  const recordId = params?.get("record_id") ?? "";

  const [threads, setThreads] = useState<ChatThread[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    listChatThreads().then(setThreads).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load]);

  // If arrived with a linked record, open (or create) that thread and jump in.
  useEffect(() => {
    if (recordType && recordId) {
      openChatThread(recordType, recordId)
        .then((t) => router.replace(`/customer/chat/${t.id}`))
        .catch(setError);
    }
  }, [recordType, recordId, router]);

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Messages</h1>
      <ErrorBanner error={error} />

      {threads === null ? (
        <div className="co-card">Loading…</div>
      ) : threads.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 24 }}>
          No conversations yet. Message your provider from a booking to start one.
        </div>
      ) : (
        threads.map((t) => (
          <button key={t.id} onClick={() => router.push(`/customer/chat/${t.id}`)}
            className="co-card" style={{ marginBottom: 10, width: "100%", textAlign: "left",
              border: "none", cursor: "pointer", display: "flex", justifyContent: "space-between",
              alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600 }}>
                {RECORD_LABEL[t.record_type] ?? t.record_type} · #{t.thread_number}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
                {t.last_message_at
                  ? `Last message ${new Date(t.last_message_at).toLocaleString()}`
                  : "No messages yet"}
              </div>
            </div>
            <span style={{ color: "var(--text-tertiary)" }}>›</span>
          </button>
        ))
      )}

      <BottomNav />
    </div>
  );
}
