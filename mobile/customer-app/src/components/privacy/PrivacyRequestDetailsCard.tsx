import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon, IconProps } from "../Icon";
import { PrivacyRequest } from "../../domain/privacyData";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";

function formatDateTime(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function Row({ icon, label, value }: { icon: IconProps["name"]; label: string; value: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <Icon name={icon} size="compact" color={theme.colors.textSecondary} decorative />
      <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>{label}</AppText>
      <AppText variant="bodySmall">{value}</AppText>
    </View>
  );
}

/** Only real, customer-safe fields (spec section 7) -- no database ID,
 * storage key, admin assignee, internal comment, risk score or policy
 * code is ever rendered here. */
export function PrivacyRequestDetailsCard({ request, typeLabel }: { request: PrivacyRequest; typeLabel: string }) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      <Row icon="document-text-outline" label="Request type" value={typeLabel} />
      {request.requestNumber ? (
        <Row icon="pricetag-outline" label="Reference" value={request.requestNumber} />
      ) : null}
      {request.submittedAt ? (
        <Row icon="calendar-outline" label="Submitted" value={formatDateTime(request.submittedAt)} />
      ) : null}
      {request.updatedAt ? (
        <Row icon="refresh-outline" label="Last updated" value={formatDateTime(request.updatedAt)} />
      ) : null}
    </AppCard>
  );
}
