// ═══════════════════════════════════════════════════════════════════════════
// Tenant AI Assistant — admin configuration client (/v1/admin/assistant/*)
//
// Matches app/engines/tenant_assistant/admin_router.py. Everything the
// assistant does for tenants is controlled through these endpoints.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

export interface AssistantConfig {
  id: string;
  scope: string;
  is_enabled: boolean;

  display_name: string;
  tagline: string | null;
  avatar_emoji: string;
  greeting: string | null;
  input_placeholder: string;
  disabled_message: string | null;

  llm_enabled: boolean;
  model: string;
  temperature: number;
  max_tokens: number;
  max_tool_iterations: number;
  system_prompt: string;

  retrieval_top_k: number;
  retrieval_min_score: number;
  require_citation: boolean;
  allowed_product_areas: string[] | null;
  allowed_tools: string[];

  out_of_scope_message: string;
  no_answer_message: string;

  show_categories: boolean;
  show_most_asked: boolean;
  show_live_state: boolean;
  show_recent_requests: boolean;
  show_page_context: boolean;
  show_announcements: boolean;
  max_options_total: number;
  max_options_per_group: number;

  escalation_enabled: boolean;
  auto_escalate_after_unresolved: number;
  escalation_category: string;
  escalation_impact: string;
  escalation_include_transcript: boolean;
  email_on_escalation: boolean;

  rate_limit_per_hour: number;
  session_idle_minutes: number;
  allowed_roles: string[] | null;
  updated_at: string | null;
}

export interface AssistantOptionRow {
  id: string;
  group_key: string;
  label: string;
  description: string | null;
  icon: string | null;
  action_type: "article" | "topic" | "tool" | "prompt" | "link" | "ticket";
  action_target: string | null;
  role_keys: string[] | null;
  page_prefixes: string[] | null;
  display_order: number;
  is_enabled: boolean;
  is_featured: boolean;
  click_count: number;
}

export interface AssistantCapabilities {
  tools: { name: string; description: string }[];
  action_types: string[];
  portal_routes: { key: string; route: string; label: string }[];
  groups: { key: string; label: string }[];
  knowledge_areas: { product_area: string; article_count: number }[];
}

export interface AssistantAnalytics {
  window_days: number;
  total_answers: number;
  by_resolution: Record<string, number>;
  answer_rate: number | null;
  escalations: number;
  content_gaps: { question: string; times: number }[];
  top_options: { label: string; group: string; clicks: number }[];
}

export const assistantAdminApi = {
  getConfig: () => apiFetch<AssistantConfig>("/v1/admin/assistant/config"),

  updateConfig: (patch: Partial<AssistantConfig>) =>
    apiFetch<AssistantConfig>("/v1/admin/assistant/config", {
      method: "PUT", body: JSON.stringify(patch),
    }),

  capabilities: () => apiFetch<AssistantCapabilities>("/v1/admin/assistant/capabilities"),

  listOptions: () =>
    apiFetch<{ options: AssistantOptionRow[]; count: number }>("/v1/admin/assistant/options"),

  createOption: (body: Partial<AssistantOptionRow>) =>
    apiFetch<AssistantOptionRow>("/v1/admin/assistant/options", {
      method: "POST", body: JSON.stringify(body),
    }),

  updateOption: (id: string, patch: Partial<AssistantOptionRow>) =>
    apiFetch<AssistantOptionRow>(`/v1/admin/assistant/options/${id}`, {
      method: "PUT", body: JSON.stringify(patch),
    }),

  deleteOption: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/assistant/options/${id}`, { method: "DELETE" }),

  analytics: (days = 30) =>
    apiFetch<AssistantAnalytics>(`/v1/admin/assistant/analytics?days=${days}`),

  preview: (question: string, tenantId: string) =>
    apiFetch<{ answer: string; resolution: string; citations: { title: string }[] }>(
      "/v1/admin/assistant/preview", {
        method: "POST", body: JSON.stringify({ question, tenant_id: tenantId }),
      }),
};
