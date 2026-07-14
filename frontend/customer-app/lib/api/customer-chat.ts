/**
 * Customer Chat API module — customer ↔ provider messaging.
 *
 * MODULE-L5-14: admin, provider and tenant all had chat UIs wired to the
 * platform_notifications chat engine, but the CUSTOMER — one party to every
 * conversation — had no chat surface or client at all, though customer_chat_router
 * exposes the full thread/message API. This wires it.
 *
 * Real router: app/engines/platform_notifications/customer_router.py
 *   GET  /v1/customer/chat/threads
 *   POST /v1/customer/chat/threads              { record_type, record_id }
 *   GET  /v1/customer/chat/threads/{id}
 *   GET  /v1/customer/chat/threads/{id}/messages
 *   POST /v1/customer/chat/threads/{id}/messages { message_text }
 *   POST /v1/customer/chat/threads/{id}/read
 */
import { apiFetch } from "./client";

export interface ChatThread {
  id: string;
  thread_number: string;
  tenant_id?: string | null;
  record_type: string;
  record_id: string;
  status: string;
  last_message_at?: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  thread_id: string;
  sender_user_id?: string | null;
  sender_type: string;
  message_type: string;
  message_text?: string | null;
  media_urls?: string[] | null;
  delivery_status: string;
  created_at: string;
}

export async function listChatThreads(): Promise<ChatThread[]> {
  const d = await apiFetch<{ items: ChatThread[] }>("/v1/customer/chat/threads");
  return d.items ?? [];
}

// Opens (or reuses) the thread attached to a booking/job/complaint record.
export async function openChatThread(recordType: string, recordId: string): Promise<ChatThread> {
  return apiFetch<ChatThread>("/v1/customer/chat/threads", {
    method: "POST", body: JSON.stringify({ record_type: recordType, record_id: recordId }),
  });
}

export async function getChatThread(threadId: string): Promise<ChatThread> {
  return apiFetch<ChatThread>(`/v1/customer/chat/threads/${threadId}`);
}

export async function listChatMessages(threadId: string): Promise<ChatMessage[]> {
  const d = await apiFetch<{ items: ChatMessage[] }>(`/v1/customer/chat/threads/${threadId}/messages`);
  return d.items ?? [];
}

export async function sendChatMessage(threadId: string, text: string): Promise<ChatMessage> {
  return apiFetch<ChatMessage>(`/v1/customer/chat/threads/${threadId}/messages`, {
    method: "POST", body: JSON.stringify({ message_text: text, message_type: "text" }),
  });
}

export async function markThreadRead(threadId: string): Promise<void> {
  await apiFetch(`/v1/customer/chat/threads/${threadId}/read`, { method: "POST", body: "{}" });
}
