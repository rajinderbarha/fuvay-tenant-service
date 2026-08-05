import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { PrivacyRequest } from "../../domain/privacyData";
import { ServerTimestamp } from "../../domain/dates";

const REQUEST_TYPE_LABEL: Record<string, string> = {
  right_to_erasure: "Account deletion",
  data_export: "Data export",
  consent_withdrawal: "Consent withdrawal",
  consent_update: "Consent update",
  data_correction: "Data correction",
  processing_objection: "Processing objection",
  grievance: "Grievance",
};

const STATUS_TONE: Record<string, "success" | "warning" | "danger" | "info" | "neutral"> = {
  Submitted: "info",
  "Identity Verification Required": "warning",
  "Under Review": "info",
  Approved: "success",
  "Partially Approved": "success",
  Rejected: "danger",
  Processing: "info",
  Completed: "success",
  "Needs Attention": "danger",
  Cancelled: "neutral",
  Delayed: "warning",
};

export interface PrivacyRequestCardProps {
  request: PrivacyRequest;
  onPress?: () => void;
  onCancel?: () => void;
  onDownload?: () => void;
}

/** `statusLabel` always comes from the backend's own safe mapping -- an
 * unrecognized value here means the backend added a new status this app
 * doesn't know about yet, so it falls back to a neutral tone rather than
 * guessing (spec section 10). */
export function PrivacyRequestCard({ request, onPress, onCancel, onDownload }: PrivacyRequestCardProps) {
  const { theme } = useTheme();
  const tone = STATUS_TONE[request.statusLabel] ?? "neutral";
  const typeLabel = REQUEST_TYPE_LABEL[request.requestType] ?? "Privacy request";
  const submitted = request.submittedAt
    ? new Date(request.submittedAt as ServerTimestamp).toLocaleDateString()
    : new Date(request.createdAt as ServerTimestamp).toLocaleDateString();

  const canCancel = !!onCancel && (request.status === "submitted" || request.status === "identity_verification_pending");
  const canDownload = !!onDownload && !!request.export && !request.export.isExpired && request.export.status === "ready";

  const content = (
    <AppCard style={{ gap: theme.spacing.xs }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <AppText variant="bodyStrong">{typeLabel}</AppText>
        <AppBadge label={request.statusLabel || "Request status unavailable"} tone={tone} />
      </View>
      <AppText variant="bodySmall" color="secondary">Submitted {submitted}</AppText>
      {request.rejectionReason ? (
        <AppText variant="bodySmall" color="secondary">{request.rejectionReason}</AppText>
      ) : null}
      {canCancel || canDownload ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle, paddingTop: theme.spacing.sm }}>
          {canDownload ? (
            <AppText variant="labelStrong" color="link" onPress={onDownload} accessibilityRole="button" accessibilityLabel={`Download export for ${typeLabel}`}>
              Download export
            </AppText>
          ) : null}
          {canCancel ? (
            <AppText variant="labelStrong" color="danger" onPress={onCancel} accessibilityRole="button" accessibilityLabel={`Withdraw ${typeLabel} request`}>
              Withdraw request
            </AppText>
          ) : null}
        </View>
      ) : null}
    </AppCard>
  );

  if (!onPress) {
    return (
      <View accessible accessibilityLabel={`${typeLabel}, ${request.statusLabel || "Request status unavailable"}, submitted ${submitted}`}>
        {content}
      </View>
    );
  }

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${typeLabel}, ${request.statusLabel || "Request status unavailable"}, submitted ${submitted}. View details.`}
    >
      {content}
    </Pressable>
  );
}
