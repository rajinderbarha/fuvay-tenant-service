import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Money } from "../../../design-system/components/data-display/Money";
import { IconButton } from "../../../design-system/components/actions/IconButton";
import { QuoteLineItemDTO } from "../../../services/estimate/types";

const CATEGORY_LABEL: Record<string, string> = {
  labour: "Labour", part: "Part / material", material: "Part / material",
  service: "Service", visit_charge: "Visit charge", discount: "Adjustment",
  tax: "Tax", other: "Other",
};

export interface LineItemRowProps {
  item: QuoteLineItemDTO;
  editable: boolean;
  onEdit: () => void;
  onRemove: () => void;
}

/** Line total is always the backend-computed `line_total` -- never
 * recalculated from quantity/unit_price on the client (spec section 6). */
export function LineItemRow({ item, editable, onEdit, onRemove }: LineItemRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm, gap: theme.spacing.sm, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
      <View style={{ flex: 1 }}>
        <AppText variant="body">{item.item_name}</AppText>
        <AppText variant="caption" color="tertiary">{CATEGORY_LABEL[item.item_type] ?? item.item_type}</AppText>
      </View>
      <Money amount={Number(item.line_total)} size="medium" />
      {editable ? (
        <View style={{ flexDirection: "row" }}>
          <IconButton icon="create-outline" accessibilityLabel={`Edit ${item.item_name}`} onPress={onEdit} />
          <IconButton icon="trash-outline" accessibilityLabel={`Remove ${item.item_name}`} onPress={onRemove} tone="danger" />
        </View>
      ) : null}
    </View>
  );
}
