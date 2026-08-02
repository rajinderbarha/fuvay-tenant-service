import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { Money } from "../data-display/Money";
import { Divider } from "../foundation/Layout";

export interface EstimateLineItem {
  label: string;
  quantity: number;
  unitAmount: number;
  totalAmount: number;
}

export type EstimateDecisionState =
  | "not_requested" | "draft" | "sent" | "approved" | "revision_requested" | "rejected" | "expired" | "cancelled" | "superseded";

const DECISION_LABEL: Record<EstimateDecisionState, string> = {
  not_requested: "Not requested", draft: "Draft", sent: "Awaiting customer decision", approved: "Approved",
  revision_requested: "Revision requested", rejected: "Rejected", expired: "Expired", cancelled: "Cancelled", superseded: "Superseded",
};

export interface EstimateSummaryProps {
  version: number;
  decisionState: EstimateDecisionState;
  lineItems: EstimateLineItem[];
  visitFeeAmount?: number;
  totalAmount: number;
  /** Totals are ALWAYS server-calculated -- this component only displays
   * the number it's given, it never sums line items itself. */
}

export function EstimateSummary({ version, decisionState, lineItems, visitFeeAmount, totalAmount }: EstimateSummaryProps) {
  const { theme } = useTheme();
  const isTerminal = decisionState === "rejected" || decisionState === "expired" || decisionState === "cancelled" || decisionState === "superseded";

  return (
    <Card>
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: theme.spacing.sm }}>
        <AppText variant="bodyStrong">Estimate v{version}</AppText>
        <AppText variant="bodySmall" color={isTerminal ? "danger" : decisionState === "approved" ? "success" : "secondary"}>
          {DECISION_LABEL[decisionState]}
        </AppText>
      </View>

      {lineItems.map((item, i) => (
        <View key={i} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 }}>
          <AppText variant="bodySmall" style={{ flex: 1 }}>{item.label} × {item.quantity}</AppText>
          <Money amount={item.totalAmount} size="medium" />
        </View>
      ))}

      {visitFeeAmount !== undefined ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 }}>
          <AppText variant="bodySmall" color="tertiary">Visit fee</AppText>
          <Money amount={visitFeeAmount} size="medium" />
        </View>
      ) : null}

      <Divider style={{ marginVertical: theme.spacing.sm }} />
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <AppText variant="bodyStrong">Total</AppText>
        <Money amount={totalAmount} size="large" />
      </View>
    </Card>
  );
}
