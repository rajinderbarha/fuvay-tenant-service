import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { PrivacyRequest, PrivacyRequestAuditEvent } from "../../domain/privacyData";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";

/** Only the customer-visible action names the backend actually emits
 * (`customer_router.get_my_request`'s `customer_visible_actions` allowlist)
 * -- an unrecognized action falls back to a generic label rather than
 * showing a raw internal action string. */
const EVENT_LABEL: Record<string, string> = {
  "request.created": "Request submitted",
  "request.identity_verified": "Identity verified",
  "request.approved": "Request approved",
  "request.partially_approved": "Request partially approved",
  "request.rejected": "Request rejected",
  "request.processed": "Request processed",
  "request.completed": "Request completed",
  "sla.at_risk": "Review due soon",
  "sla.breached": "Review delayed",
  "sla.on_track": "Review on track",
  "compliance.customer_request_viewed": "Viewed",
};

function formatDateTime(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function TimelineRow({ event, isLast }: { event: PrivacyRequestAuditEvent; isLast: boolean }) {
  const { theme } = useTheme();
  const label = EVENT_LABEL[event.action] ?? "Status updated";
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
      <View style={{ alignItems: "center" }}>
        <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        {!isLast ? <View style={{ width: 1, flex: 1, backgroundColor: theme.colors.borderSubtle, marginTop: theme.spacing.xxs }} /> : null}
      </View>
      <View style={{ flex: 1, paddingBottom: isLast ? 0 : theme.spacing.sm }}>
        <AppText variant="bodyStrong">{label}</AppText>
        <AppText variant="caption" color="secondary">{formatDateTime(event.createdAt)}</AppText>
      </View>
    </View>
  );
}

/** Real customer-visible history when the backend provides one
 * (`audit_trail` on the detail response); otherwise a single current-status
 * row plus submitted/updated timestamps only -- no manufactured earlier or
 * future stages, no dates assigned to conceptual future steps (spec
 * section 6). */
export function PrivacyRequestProgress({ request }: { request: PrivacyRequest }) {
  const { theme } = useTheme();
  const events = request.auditTrail ?? [];

  if (events.length > 0) {
    return (
      <AppCard style={{ gap: 0 }}>
        {events.map((event, i) => (
          <TimelineRow key={`${event.action}-${event.createdAt}-${i}`} event={event} isLast={i === events.length - 1} />
        ))}
      </AppCard>
    );
  }

  return (
    <AppCard style={{ gap: theme.spacing.xs }}>
      <AppText variant="bodyStrong">{request.statusLabel || "Status unavailable"}</AppText>
      {request.submittedAt ? (
        <AppText variant="bodySmall" color="secondary">Submitted {formatDateTime(request.submittedAt)}</AppText>
      ) : null}
      {request.updatedAt ? (
        <AppText variant="bodySmall" color="secondary">Last updated {formatDateTime(request.updatedAt)}</AppText>
      ) : null}
    </AppCard>
  );
}
