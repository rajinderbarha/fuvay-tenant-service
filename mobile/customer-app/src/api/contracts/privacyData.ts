/**
 * `GET/POST /v1/me/compliance/requests`, `GET .../requests/{id}`,
 * `POST .../requests/{id}/cancel`, `GET .../consents`,
 * `POST .../consents/{type}/withdraw`, `GET .../exports/{id}/download` --
 * all confirmed real in `app/engines/compliance/customer_router.py`.
 */
import { z } from "zod";

export const privacyRequestExportDtoSchema = z.object({
  export_id: z.string(),
  status: z.string(),
  expires_at: z.string().nullable(),
  is_expired: z.boolean(),
});

export const privacyRequestAuditEventDtoSchema = z.object({
  action: z.string(),
  created_at: z.string(),
});

export const privacyRequestDtoSchema = z.object({
  id: z.string(),
  request_number: z.string(),
  request_type: z.string(),
  status: z.string(),
  status_label: z.string(),
  sla_status: z.string().nullable(),
  sla_label: z.string().nullable(),
  verification_status: z.string().nullable().optional(),
  submitted_at: z.string().nullable(),
  due_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  reason: z.string().nullable(),
  rejection_reason: z.string().nullable(),
  request_source: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
  export: privacyRequestExportDtoSchema.optional(),
  /** Only present on the single-request detail response
   * (`GET /v1/me/compliance/requests/{id}`) -- already filtered
   * server-side to customer-visible actions only (see
   * `customer_router.get_my_request`'s `customer_visible_actions` set). */
  audit_trail: z.array(privacyRequestAuditEventDtoSchema).optional(),
}).passthrough();
export type PrivacyRequestDto = z.infer<typeof privacyRequestDtoSchema>;

export const privacyRequestListResponseSchema = z.object({
  requests: z.array(privacyRequestDtoSchema),
  meta: z.object({ total: z.number(), page: z.number(), limit: z.number(), total_pages: z.number() }),
});

export const createPrivacyRequestBodySchema = z.object({
  request_type: z.string(),
  reason: z.string().optional(),
  confirm_understanding: z.literal(true),
  /** Real backend contract (Data Export Request phase) -- reusing the same
   * key across a retry of the same deliberate submission attempt makes the
   * server return the original request instead of creating a duplicate. */
  idempotency_key: z.string().optional(),
  /** Account Deletion Final Confirmation phase: `right_to_erasure` requires
   * current-password confirmation, verified server-side in the same call
   * that creates the request (`customer_router.create_my_request`) --
   * never sent for any other request_type. Never logged, never persisted
   * client-side beyond the in-flight request body. */
  password: z.string().optional(),
});
export type CreatePrivacyRequestBody = z.infer<typeof createPrivacyRequestBodySchema>;

export const createPrivacyRequestResponseSchema = z.object({
  request_id: z.string(),
  request_number: z.string(),
  request_type: z.string(),
  status: z.string(),
  status_label: z.string(),
  sla_status: z.string().nullable(),
  submitted_at: z.string().nullable(),
  due_at: z.string().nullable(),
  message: z.string(),
});

export const consentRecordDtoSchema = z.object({
  id: z.string(),
  consent_type: z.string(),
  action: z.enum(["granted", "withdrawn"]),
  policy_version: z.string(),
  granted_at: z.string().nullable(),
  withdrawn_at: z.string().nullable(),
  expires_at: z.string().nullable(),
});
export type ConsentRecordDto = z.infer<typeof consentRecordDtoSchema>;

export const consentListResponseSchema = z.object({
  items: z.array(consentRecordDtoSchema),
  meta: z.object({ total: z.number(), page: z.number(), limit: z.number(), total_pages: z.number() }),
});

export const exportDownloadResponseSchema = z.object({
  download_url: z.string().nullable(),
  export_id: z.string(),
  status: z.string(),
  downloaded_at: z.string().nullable(),
});
