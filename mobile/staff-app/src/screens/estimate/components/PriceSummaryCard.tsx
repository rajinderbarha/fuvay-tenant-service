import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Money } from "../../../design-system/components/data-display/Money";
import { CalculationDTO } from "../../../services/estimate/types";

function Row({ label, amount, strong }: { label: string; amount: number; strong?: boolean }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xxs }}>
      <AppText variant={strong ? "bodyStrong" : "bodySmall"} color={strong ? "primary" : "secondary"}>{label}</AppText>
      <Money amount={amount} size={strong ? "medium" : "medium"} />
    </View>
  );
}

/** Every figure here is the backend-computed calculation (Decimal-safe,
 * spec section 5) -- this component never sums line items itself. */
export function PriceSummaryCard({ calculation }: { calculation: CalculationDTO }) {
  const { theme } = useTheme();
  const hasVisitFee = Number(calculation.visit_fee_adjustment) !== 0;
  const hasTax = Number(calculation.tax_total) !== 0;
  return (
    <Card>
      <Row label="Labour" amount={Number(calculation.labour_total)} />
      <Row label="Parts / materials" amount={Number(calculation.parts_total)} />
      {hasVisitFee ? <Row label="Visit fee adjustment" amount={Number(calculation.visit_fee_adjustment)} /> : null}
      {hasTax ? <Row label="Tax" amount={Number(calculation.tax_total)} /> : null}
      <View style={{ height: 1, backgroundColor: theme.colors.borderSubtle, marginVertical: theme.spacing.sm }} />
      <Row label="Estimated total" amount={Number(calculation.grand_total)} strong />
    </Card>
  );
}
