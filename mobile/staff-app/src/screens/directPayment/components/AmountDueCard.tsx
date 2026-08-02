import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Money } from "../../../design-system/components/data-display/Money";
import { Icon } from "../../../design-system/components/Icon";
import { ExpectedAmountDTO } from "../../../services/directPayment/types";

/** Every figure here is backend-calculated and read-only -- the technician
 * cannot edit the authoritative amount (spec section 6). */
export function AmountDueCard({ amount }: { amount: ExpectedAmountDTO }) {
  const { theme } = useTheme();
  const total = amount.expected_amount !== null ? Number(amount.expected_amount) : null;
  return (
    <Card>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
        <AppText variant="bodyStrong">Amount due to provider</AppText>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          <Icon name="lock-closed" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary">Backend calculated</AppText>
        </View>
      </View>
      {total !== null ? (
        <Money amount={total} size="large" style={{ marginTop: theme.spacing.xs }} />
      ) : (
        <AppText variant="bodySmall" color="warning" style={{ marginTop: theme.spacing.xs }}>Amount not yet resolvable.</AppText>
      )}
      {amount.approved_estimate ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: theme.spacing.sm }}>
          <AppText variant="bodySmall" color="secondary">Approved estimate v{amount.approved_estimate.version_number}</AppText>
          <Money amount={Number(amount.approved_estimate.total_amount)} size="medium" />
        </View>
      ) : null}
      {Number(amount.visit_fee_adjustment) !== 0 ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: theme.spacing.xxs }}>
          <AppText variant="bodySmall" color="secondary">Visit fee adjusted</AppText>
          <AppText variant="bodySmall" color="secondary">Included</AppText>
        </View>
      ) : null}
    </Card>
  );
}
