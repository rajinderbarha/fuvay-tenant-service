import { ServerTimestamp } from "./dates";

/** Every value confirmed real in `app/engines/compliance/customer_router.py`
 * (`CUSTOMER_ALLOWED_REQUEST_TYPES`) -- never a client-invented type. */
export type PrivacyRequestType =
  | "right_to_erasure" | "data_export" | "consent_withdrawal"
  | "consent_update" | "data_correction" | "processing_objection" | "grievance";

export interface PrivacyRequestExport {
  exportId: string;
  status: string;
  expiresAt: ServerTimestamp | null;
  isExpired: boolean;
}

export interface PrivacyRequestAuditEvent {
  action: string;
  createdAt: ServerTimestamp;
}

export interface PrivacyRequest {
  id: string;
  requestNumber: string;
  requestType: PrivacyRequestType;
  status: string;
  statusLabel: string;
  slaStatus: string | null;
  slaLabel: string | null;
  verificationStatus: string | null;
  submittedAt: ServerTimestamp | null;
  dueAt: ServerTimestamp | null;
  completedAt: ServerTimestamp | null;
  reason: string | null;
  rejectionReason: string | null;
  createdAt: ServerTimestamp;
  updatedAt: ServerTimestamp | null;
  export?: PrivacyRequestExport;
  /** Only populated when this object came from the single-request detail
   * fetch -- list rows never carry it (spec section 6). */
  auditTrail?: PrivacyRequestAuditEvent[];
}

/** Only the withdrawable set the backend actually enforces
 * (`WITHDRAWABLE_CONSENT_TYPES`) -- required legal acknowledgements are
 * never rendered with a toggle (spec section 13). */
export type ConsentType =
  | "marketing" | "location_access" | "notification"
  | "profiling" | "ai_assistant_processing" | "media_processing"
  | (string & {});

export interface ConsentRecord {
  id: string;
  consentType: ConsentType;
  action: "granted" | "withdrawn";
  policyVersion: string;
  grantedAt: ServerTimestamp | null;
  withdrawnAt: ServerTimestamp | null;
  expiresAt: ServerTimestamp | null;
}

const WITHDRAWABLE_CONSENT_TYPES = new Set<ConsentType>([
  "marketing", "location_access", "notification",
  "profiling", "ai_assistant_processing", "media_processing",
]);

export function isConsentWithdrawable(type: ConsentType): boolean {
  return WITHDRAWABLE_CONSENT_TYPES.has(type);
}

/** Every capability gated by a confirmed real route in
 * `app/engines/compliance/customer_router.py` (audited this phase).
 * `canDownloadExport` is real (the customer-scoped download endpoint
 * exists, ownership-checked, rate-limited) but its underlying
 * `download_url` is a backend limitation, not a frontend one -- disclosed
 * in the final report, not hidden here, since the endpoint itself is
 * genuine and customer-callable. */
export interface PrivacyCapabilities {
  canRequestExport: boolean;
  canRequestErasure: boolean;
  canRequestCorrection: boolean;
  canManageConsent: boolean;
  canViewRequestHistory: boolean;
  canCancelRequest: boolean;
  canDownloadExport: boolean;
}
