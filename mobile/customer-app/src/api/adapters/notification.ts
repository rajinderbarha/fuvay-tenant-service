import { NotificationDto } from "../contracts/notifications";
import { CustomerNotification, CustomerNotificationReadStatus } from "../../domain/notification";
import { asNotificationId } from "../../domain/ids";
import { parseServerTimestamp } from "../../domain/dates";
import { resolveSafeNotificationDestination } from "../../domain/notificationDestination";

const KNOWN_READ_STATUSES: CustomerNotificationReadStatus[] = ["unread", "read", "archived"];

export function adaptNotification(dto: NotificationDto): CustomerNotification {
  return {
    id: asNotificationId(dto.id),
    type: dto.notification_type,
    title: dto.title,
    body: dto.body,
    createdAt: parseServerTimestamp(dto.created_at, "notification.created_at"),
    readAt: dto.read_at ? parseServerTimestamp(dto.read_at, "notification.read_at") : null,
    // An unrecognized read_status is treated as unread -- the safer default
    // for something the customer hasn't confirmed seeing.
    readStatus: KNOWN_READ_STATUSES.includes(dto.read_status as CustomerNotificationReadStatus)
      ? (dto.read_status as CustomerNotificationReadStatus) : "unread",
    destination: resolveSafeNotificationDestination(dto.source_record_type, dto.source_record_id),
  };
}
