import { SupportRequestDto, SupportRequestMessageDto } from "../contracts/supportRequests";
import { SupportRequest, SupportRequestMessage, SupportRequestRecordType } from "../../domain/supportRequests";
import { parseServerTimestamp } from "../../domain/dates";

function ts(value: string | null) {
  return value ? parseServerTimestamp(value, "timestamp") : null;
}

export function adaptSupportRequest(dto: SupportRequestDto): SupportRequest {
  return {
    id: dto.id,
    complaintNumber: dto.complaint_number,
    recordType: dto.record_type as SupportRequestRecordType,
    recordId: dto.record_id,
    bookingId: dto.booking_id,
    complaintType: dto.complaint_type,
    status: dto.status,
    title: dto.title,
    description: dto.description,
    requestedResolution: dto.requested_resolution,
    customerVisibleSummary: dto.customer_visible_summary,
    createdAt: ts(dto.created_at),
    updatedAt: ts(dto.updated_at),
    resolvedAt: ts(dto.resolved_at),
    closedAt: ts(dto.closed_at),
  };
}

export function adaptSupportRequestMessage(dto: SupportRequestMessageDto): SupportRequestMessage {
  return {
    id: dto.id,
    senderType: dto.sender_type,
    messageText: dto.message_text,
    createdAt: parseServerTimestamp(dto.created_at, "message.created_at"),
  };
}
