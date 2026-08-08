import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { CustomerAlias, RelayContactButton } from "../../../design-system/components/data-display/Privacy";
import { CustomerContactDTO } from "../../../services/jobDetail/types";

/** Backend reasons a call cannot be placed, in wording a technician can act on.
 * Kept as a closed map so an unrecognised code falls back to a neutral message
 * rather than showing a raw error constant to a field user. */
const CANNOT_CALL_COPY: Record<string, string> = {
  MASKED_CALLING_NOT_CONFIGURED: "Calling is unavailable right now.",
  MASKED_CALLING_JOB_NOT_CALLABLE: "This job is closed, so calls are turned off.",
  MASKED_CALLING_NO_CUSTOMER_NUMBER: "No contact number on file for this customer.",
  MASKED_CALLING_NO_STAFF_NUMBER: "Add your phone number in Profile to place calls.",
};

export interface CustomerContactCardProps {
  customer: CustomerContactDTO;
  onCallRelay: () => void;
  onMessageRelay: () => void;
  /** Live capability from the masked-calling backend. When omitted, the card
   * falls back to the job-detail DTO's own flags, so existing callers that
   * have not adopted the hook keep working unchanged. */
  callAvailable?: boolean;
  cannotCallReason?: string | null;
  calling?: boolean;
  /** True once a bridged call has genuinely CONNECTED for this job. */
  connectedBefore?: boolean;
  callError?: string | null;
}

/**
 * Never renders a raw phone or email. Calls are bridged by the platform, so
 * neither the technician nor the customer sees the other's number -- and there
 * is no number in the payload to render even by mistake.
 *
 * Availability is the BACKEND's decision (`can_call`), never inferred here from
 * job status: when it says no, the reason is shown instead of a dead button or
 * an invented fallback contact route.
 */
export function CustomerContactCard({
  customer, onCallRelay, onMessageRelay,
  callAvailable, cannotCallReason, calling, connectedBefore, callError,
}: CustomerContactCardProps) {
  const { theme } = useTheme();
  const canCall = callAvailable ?? customer.call_relay_available;
  const reasonCode = cannotCallReason ?? customer.call_relay_reason;
  const reasonText = reasonCode
    ? (CANNOT_CALL_COPY[reasonCode] ?? "Calling is unavailable right now.")
    : null;

  return (
    <Card>
      <CustomerAlias alias={customer.customer_alias} showAvatar />

      <AppText variant="caption" color="secondary" style={{ marginTop: theme.spacing.xs }}>
        Calls go through the platform — your number and the customer&apos;s stay private.
      </AppText>

      <View style={{ flexDirection: "row", gap: theme.spacing.lg, marginTop: theme.spacing.sm }}>
        <RelayContactButton
          label={calling ? "Connecting…" : connectedBefore ? "Call again" : "Call customer"}
          onPress={onCallRelay}
          disabled={!canCall || !!calling}
        />
        <RelayContactButton
          label="Message"
          onPress={onMessageRelay}
          disabled={!customer.message_relay_available}
        />
      </View>

      {!canCall && reasonText ? (
        <AppText variant="caption" color="secondary" style={{ marginTop: theme.spacing.xs }}>
          {reasonText}
        </AppText>
      ) : null}

      {callError ? (
        <AppText variant="caption" color="danger" style={{ marginTop: theme.spacing.xs }}>
          {callError}
        </AppText>
      ) : null}
    </Card>
  );
}
