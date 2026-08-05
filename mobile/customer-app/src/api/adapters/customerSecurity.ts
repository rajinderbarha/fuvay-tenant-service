import { SessionDto, LoginActivityEventDto } from "../contracts/customerSecurity";
import { CustomerSession, LoginActivityEvent } from "../../domain/customerSecurity";
import { parseServerTimestamp } from "../../domain/dates";

export function adaptCustomerSession(dto: SessionDto): CustomerSession {
  return {
    sessionId: dto.session_id,
    deviceName: dto.device_name ?? null,
    channel: dto.channel,
    isCurrent: dto.is_current,
    isTrusted: dto.is_trusted,
    lastActiveAt: dto.last_active_at ? parseServerTimestamp(dto.last_active_at, "last_active_at") : null,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
  };
}

export function adaptLoginActivityEvent(dto: LoginActivityEventDto): LoginActivityEvent {
  return {
    eventId: dto.event_id,
    label: dto.label,
    outcome: dto.outcome,
    channel: dto.channel,
    deviceName: dto.device_name,
    isCurrentDevice: dto.is_current_device,
    occurredAt: parseServerTimestamp(dto.occurred_at, "occurred_at"),
  };
}
