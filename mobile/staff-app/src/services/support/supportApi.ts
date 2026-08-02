import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { HelpWorkspaceDTO, ArticleDetailDTO, TicketDetailDTO } from "./types";

const BASE = "/v1/tenant/support";

/** Help & Support (Phase Y). Reuses the EXISTING canonical Tenant Help &
 * Support engine end-to-end (confirmed by audit: `get_current_user` already
 * grants the "technician" role real ticket/knowledge/status access) --
 * zero new backend routes, only real content seeded into the existing
 * knowledge-article model. */
export function getWorkspace(signal?: AbortSignal): Promise<ApiResult<HelpWorkspaceDTO>> {
  return authenticatedRequest<HelpWorkspaceDTO>(`${BASE}/workspace`, { method: "GET", signal });
}

export function getServiceStatus(signal?: AbortSignal): Promise<ApiResult<HelpWorkspaceDTO["service_status"]>> {
  return authenticatedRequest(`${BASE}/service-status`, { method: "GET", signal });
}

/** The backend derives `role` from the authenticated caller server-side
 * (`user.role`, app/engines/support/tenant_router.py:437) -- there is no
 * client-supplied audience parameter to fake here, and no separate
 * article-detail-by-slug endpoint. The list endpoint already returns full
 * article bodies (`with_body=True` server-side), so the Article screen
 * finds its article within this same result set. */
export function searchArticles(params: { search?: string; area?: string }, signal?: AbortSignal): Promise<ApiResult<{ articles: ArticleDetailDTO[]; categories: HelpWorkspaceDTO["quick_help"]; featured: ArticleDetailDTO[] }>> {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.area) query.set("area", params.area);
  return authenticatedRequest(`${BASE}/knowledge?${query.toString()}`, { method: "GET", signal });
}

export function submitArticleFeedback(articleId: string, isHelpful: boolean): Promise<ApiResult<{ recorded: boolean }>> {
  return authenticatedRequest(`${BASE}/knowledge/${articleId}/feedback`, { method: "POST", body: { is_helpful: isHelpful } });
}

export interface CreateRequestInput {
  category: string; subject: string; description: string; impact: string;
  subcategory?: string; affected_feature?: string; attachment_media_ids?: string[];
}

export function createSupportRequest(input: CreateRequestInput): Promise<ApiResult<TicketDetailDTO>> {
  return authenticatedRequest<TicketDetailDTO>(`${BASE}/requests`, { method: "POST", body: input });
}

export function listRequests(signal?: AbortSignal): Promise<ApiResult<{ requests: HelpWorkspaceDTO["requests"]; total: number }>> {
  return authenticatedRequest(`${BASE}/requests`, { method: "GET", signal });
}

export function getRequestDetail(ticketId: string, signal?: AbortSignal): Promise<ApiResult<TicketDetailDTO>> {
  return authenticatedRequest<TicketDetailDTO>(`${BASE}/requests/${ticketId}`, { method: "GET", signal });
}

export function replyToRequest(ticketId: string, body: string): Promise<ApiResult<{ id: string }>> {
  return authenticatedRequest(`${BASE}/requests/${ticketId}/messages`, { method: "POST", body: { body } });
}

export function reopenRequest(ticketId: string, reason: string): Promise<ApiResult<TicketDetailDTO>> {
  return authenticatedRequest<TicketDetailDTO>(`${BASE}/requests/${ticketId}/reopen`, { method: "POST", body: { reason } });
}

export function confirmResolution(ticketId: string): Promise<ApiResult<TicketDetailDTO>> {
  return authenticatedRequest<TicketDetailDTO>(`${BASE}/requests/${ticketId}/confirm-resolution`, { method: "POST" });
}
