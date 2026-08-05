import { PrivacyRequestDto, ConsentRecordDto } from "../contracts/privacyData";
import { PrivacyRequest, PrivacyRequestType, ConsentRecord } from "../../domain/privacyData";
import { parseServerTimestamp } from "../../domain/dates";

function ts(value: string | null) {
  return value ? parseServerTimestamp(value, "timestamp") : null;
}

export function adaptPrivacyRequest(dto: PrivacyRequestDto): PrivacyRequest {
  return {
    id: dto.id,
    requestNumber: dto.request_number,
    requestType: dto.request_type as PrivacyRequestType,
    status: dto.status,
    statusLabel: dto.status_label,
    slaStatus: dto.sla_status,
    slaLabel: dto.sla_label,
    verificationStatus: dto.verification_status ?? null,
    submittedAt: ts(dto.submitted_at),
    dueAt: ts(dto.due_at),
    completedAt: ts(dto.completed_at),
    reason: dto.reason,
    rejectionReason: dto.rejection_reason,
    createdAt: parseServerTimestamp(dto.created_at, "created_at"),
    updatedAt: ts(dto.updated_at),
    export: dto.export ? {
      exportId: dto.export.export_id,
      status: dto.export.status,
      expiresAt: ts(dto.export.expires_at),
      isExpired: dto.export.is_expired,
    } : undefined,
    auditTrail: dto.audit_trail?.map(e => ({
      action: e.action,
      createdAt: parseServerTimestamp(e.created_at, "audit_trail.created_at"),
    })),
  };
}

export function adaptConsentRecord(dto: ConsentRecordDto): ConsentRecord {
  return {
    id: dto.id,
    consentType: dto.consent_type,
    action: dto.action,
    policyVersion: dto.policy_version,
    grantedAt: ts(dto.granted_at),
    withdrawnAt: ts(dto.withdrawn_at),
    expiresAt: ts(dto.expires_at),
  };
}
