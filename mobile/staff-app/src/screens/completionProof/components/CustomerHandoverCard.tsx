import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { SecondaryButton } from "../../../design-system/components/actions/Buttons";
import { HandoverStatus } from "../../../services/completionProof/types";

const STATUS_META: Record<HandoverStatus, { label: string; description: string; icon: string }> = {
  not_requested: { label: "Not requested", description: "Send a handover request once proof is submitted.", icon: "time-outline" },
  requested: { label: "Acknowledgment pending", description: "Customer will confirm completion in the Fuvay app.", icon: "person-outline" },
  customer_unavailable: { label: "Customer unavailable", description: "Reported unavailable -- follow tenant policy for next steps.", icon: "alert-circle-outline" },
  acknowledged: { label: "Acknowledged", description: "Customer confirmed completion.", icon: "checkmark-circle" },
  concern_reported: { label: "Customer reported a concern", description: "Routed to support -- this does not affect the approved estimate.", icon: "warning-outline" },
};

/**
 * Technician can request/remind/report-unavailable only -- never tap
 * "accept" on the customer's behalf (spec section 10). Acknowledged /
 * concern_reported states are set exclusively by the (separate) customer
 * app; that surface doesn't exist yet, so those two states are display-only
 * here and never reachable from this screen (disclosed gap).
 */
export function CustomerHandoverCard({
  status, onRequest, onSendReminder, onMarkUnavailable, canRequest, canRemind, disabled,
}: {
  status: HandoverStatus; onRequest: () => void; onSendReminder: () => void; onMarkUnavailable: () => void;
  canRequest: boolean; canRemind: boolean; disabled?: boolean;
}) {
  const { theme } = useTheme();
  const meta = STATUS_META[status];
  const tone = status === "acknowledged" ? theme.colors.statusSuccess : status === "concern_reported" ? theme.colors.statusDanger : theme.colors.statusWarning;
  const surface = status === "acknowledged" ? theme.colors.statusSuccessSurface : status === "concern_reported" ? theme.colors.statusDangerSurface : theme.colors.statusWarningSurface;

  return (
    <View style={{ padding: theme.spacing.base, borderRadius: theme.radiusUsage.card, backgroundColor: surface }}>
      <AppText variant="bodyStrong" style={{ color: tone, marginBottom: theme.spacing.xs }}>Customer handover</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <Icon name={meta.icon as any} size="standard" color={tone} decorative />
        <View style={{ flex: 1 }}>
          <AppText variant="body" style={{ color: tone }}>{meta.label}</AppText>
          <AppText variant="caption" style={{ color: tone }}>{meta.description}</AppText>
        </View>
        {canRequest ? <SecondaryButton label="Request" onPress={onRequest} disabled={disabled} />
          : canRemind ? <SecondaryButton label="Send reminder" onPress={onSendReminder} disabled={disabled} /> : null}
      </View>
      {status === "requested" && !disabled ? (
        <View style={{ marginTop: theme.spacing.sm }}>
          <SecondaryButton label="Customer unavailable" onPress={onMarkUnavailable} />
        </View>
      ) : null}
    </View>
  );
}
