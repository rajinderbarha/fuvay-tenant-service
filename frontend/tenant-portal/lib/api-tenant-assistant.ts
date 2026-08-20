// ═══════════════════════════════════════════════════════════════════════════
// Fuvay AI — tenant assistant client (/v1/tenant/assistant/*)
//
// Every path matches a real route in app/engines/tenant_assistant/tenant_router.py.
// The assistant is admin-configured, so this client makes no assumptions about
// what the panel contains: it renders whatever groups/options come back.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

export type AssistantAction =
  | "article" | "topic" | "tool" | "prompt" | "link" | "ticket";

export interface AssistantOption {
  id: string;
  group_key: string;
  label: string;
  description: string | null;
  icon: string | null;
  action_type: AssistantAction;
  action_target: string | null;
  is_featured: boolean;
}

export interface AssistantGroup {
  key: string;
  label: string;
  options: AssistantOption[];
}

export interface AssistantIdentity {
  display_name: string;
  tagline: string | null;
  avatar_emoji: string;
  greeting: string | null;
  input_placeholder: string;
  can_escalate: boolean;
  free_text_enabled: boolean;
}

export interface AssistantPanel {
  enabled: boolean;
  message?: string;
  assistant?: AssistantIdentity;
  groups?: AssistantGroup[];
  featured?: AssistantOption[];
  most_asked?: { slug: string; title: string; product_area: string }[];
  live_state?: { looks_ready: boolean; blockers: string[]; account_status: string | null };
  open_requests?: {
    ticket_number: string; subject: string; status: string;
    priority: string; raised_on: string | null; unread_replies: number;
  }[];
  announcements?: { title: string; summary: string | null; published_on: string | null }[];
  page_context?: { key: string; route: string; label: string } | null;
}

export interface AssistantCitation {
  article_id: string; slug: string; title: string;
  product_area: string; score: number;
}

export interface AssistantAnswer {
  kind: "answer" | "data" | "article_list" | "link" | "escalate";
  session_id?: string;
  message_id?: string;
  answer?: string;
  resolution?: "answered" | "partial" | "no_answer" | "out_of_scope"
             | "escalated" | "rate_limited";
  citations?: AssistantCitation[];
  can_escalate?: boolean;
  should_escalate?: boolean;
  // kind === "data"
  tool?: string;
  data?: string;
  // kind === "article_list"
  product_area?: string;
  articles?: { slug: string; title: string; summary: string | null }[];
  // kind === "link"
  route?: string;
  label?: string;
  // kind === "escalate"
  prefill?: { subject?: string };
}

export interface AssistantEscalation {
  ticket_id: string;
  ticket_number: string;
  status: string;
  priority: string;
  deep_link: string;
}

export const assistantApi = {
  panel: (path?: string) =>
    apiFetch<AssistantPanel>(
      `/v1/tenant/assistant/panel${path ? `?path=${encodeURIComponent(path)}` : ""}`),

  ask: (question: string, path?: string) =>
    apiFetch<AssistantAnswer>("/v1/tenant/assistant/ask", {
      method: "POST", body: JSON.stringify({ question, path }),
    }),

  runOption: (optionId: string, path?: string) =>
    apiFetch<AssistantAnswer>(`/v1/tenant/assistant/options/${optionId}/run`, {
      method: "POST", body: JSON.stringify({ path }),
    }),

  article: (slug: string) =>
    apiFetch<{ slug: string; title: string; summary: string | null;
               body: string | null; product_area: string }>(
      `/v1/tenant/assistant/articles/${encodeURIComponent(slug)}`),

  history: () =>
    apiFetch<{ session: unknown; messages: unknown[] }>("/v1/tenant/assistant/history"),

  escalate: (body: {
    session_id?: string | null; subject: string; description: string;
    category?: string; impact?: string;
  }) =>
    apiFetch<AssistantEscalation>("/v1/tenant/assistant/escalate", {
      method: "POST", body: JSON.stringify(body),
    }),

  feedback: (messageId: string, isHelpful: boolean, note?: string) =>
    apiFetch<{ recorded: boolean }>(
      `/v1/tenant/assistant/messages/${messageId}/feedback`, {
        method: "POST", body: JSON.stringify({ is_helpful: isHelpful, note }),
      }),
};
