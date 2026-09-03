import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { Money } from "../data-display/Money";
import { PrimaryButton } from "../actions/Buttons";

export type DirectPaymentState = "not_reported" | "provider_reported" | "customer_confirmation_pending" | "confirmed" | "disputed";

const STATE_LABEL: Record<DirectPaymentState, string> = {
  not_reported: "Not reported",
  provider_reported: "Provider reported",
  customer_confirmation_pending: "Customer confirmation pending",
  confirmed: "Confirmed",
  disputed: "Disputed",
};

export interface DirectPaymentConfirmationCardProps {
  amount: number;
  state: DirectPaymentState;
  onReportPayment?: () => void;
  loading?: boolean;
}

/**
 * Uses the correct Fuvay language: the customer pays the PROVIDER
 * directly; Fuvay only records confirmation. Never says "Fuvay
 * payout", "platform settlement sent" or "funds transferred" -- and a
 * technician can only REPORT what was collected, never mark the
 * customer's own confirmation on their behalf.
 */
export function DirectPaymentConfirmationCard({ amount, state, onReportPayment, loading }: DirectPaymentConfirmationCardProps) {
  const { theme } = useTheme();
  const tone = state === "confirmed" ? "success" : state === "disputed" ? "danger" : "secondary";

  return (
    <Card>
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: theme.spacing.xs }}>
        <AppText variant="bodyStrong">Direct payment</AppText>
        <AppText variant="bodySmall" color={tone}>{STATE_LABEL[state]}</AppText>
      </View>
      <Money amount={amount} size="large" />
      <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs, fontStyle: "italic" }}>
        Customer pays the provider directly. Fuvay records confirmation only.
      </AppText>
      {state === "not_reported" && onReportPayment ? (
        <View style={{ marginTop: theme.spacing.sm }}>
          <PrimaryButton label="Report payment collected" onPress={onReportPayment} loading={loading} fullWidth />
        </View>
      ) : null}
    </Card>
  );
}
