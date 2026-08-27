// ═══════════════════════════════════════════════════════════════════════════
// Legal Documents — admin authoring client (/v1/admin/legal/*)
//
// Matches app/engines/legal_documents/admin_router.py. Before this console
// the Terms of Service and Privacy Notice were hardcoded JSX in the tenant
// portal, so changing a clause meant a frontend deploy and nothing recorded
// which wording a person had actually accepted.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

export type LegalStatus = "draft" | "published" | "archived";

export interface LegalDocVersion {
  id: string;
  doc_type: string;
  doc_type_label: string;
  audience: string;
  locale: string;
  version: string;
  title: string;
  summary: string | null;
  /** Absent in list responses — bodies run to thousands of words. */
  body?: string;
  body_format: string;
  status: LegalStatus;
  effective_at: string | null;
  published_at: string | null;
  archived_at: string | null;
  requires_reacceptance: boolean;
  change_note: string | null;
  created_by: string | null;
  published_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LegalMeta {
  doc_types: { value: string; label: string }[];
  audiences: string[];
  statuses: string[];
  default_locale: string;
  body_format: string;
  signup_consent_doc_types: string[];
}

export interface LegalDraftInput {
  doc_type: string;
  version: string;
  title: string;
  body: string;
  summary?: string | null;
  audience?: string;
  locale?: string;
  requires_reacceptance?: boolean;
  change_note?: string | null;
}

export const legalAdminApi = {
  meta: () => apiFetch<LegalMeta>("/v1/admin/legal/meta"),

  listVersions: (params: {
    doc_type?: string;
    status?: string;
    audience?: string;
    limit?: number;
    offset?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiFetch<{
      versions: LegalDocVersion[]; total: number; limit: number; offset: number;
    }>(`/v1/admin/legal/versions${suffix}`);
  },

  getVersion: (id: string) =>
    apiFetch<LegalDocVersion>(`/v1/admin/legal/versions/${id}`),

  createDraft: (body: LegalDraftInput) =>
    apiFetch<LegalDocVersion>("/v1/admin/legal/versions", {
      method: "POST", body: JSON.stringify(body),
    }),

  updateDraft: (id: string, patch: Partial<LegalDraftInput>) =>
    apiFetch<LegalDocVersion>(`/v1/admin/legal/versions/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),

  /** Omit `effective_at` to take effect immediately; a future timestamp
   *  schedules the change and leaves the incumbent version live until then. */
  publish: (id: string, effective_at?: string | null) =>
    apiFetch<LegalDocVersion>(`/v1/admin/legal/versions/${id}/publish`, {
      method: "POST", body: JSON.stringify({ effective_at: effective_at ?? null }),
    }),

  archive: (id: string) =>
    apiFetch<LegalDocVersion>(`/v1/admin/legal/versions/${id}/archive`, {
      method: "POST",
    }),

  deleteDraft: (id: string) =>
    apiFetch<{ deleted: boolean; id: string }>(`/v1/admin/legal/versions/${id}`, {
      method: "DELETE",
    }),
};
