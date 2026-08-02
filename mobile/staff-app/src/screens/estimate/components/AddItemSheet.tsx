import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { BottomSheet } from "../../../design-system/components/overlays/BottomSheet";
import { AppText } from "../../../design-system/components/typography/AppText";
import { TextField } from "../../../design-system/components/forms/TextField";
import { SegmentedControl } from "../../../design-system/components/forms/SegmentedControl";
import { PrimaryButton } from "../../../design-system/components/actions/Buttons";
import { QuoteItemType, QuoteLineItemDTO } from "../../../services/estimate/types";

export interface AddItemSheetProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (item: { item_type: QuoteItemType; item_name: string; quantity: number; unit_price: number }) => void;
  initial?: QuoteLineItemDTO | null;
  submitting: boolean;
}

const CATEGORY_OPTIONS: { value: QuoteItemType; label: string }[] = [
  { value: "labour", label: "Labour" },
  { value: "part", label: "Part" },
  { value: "material", label: "Material" },
  { value: "other", label: "Other" },
];

/** Client-side hints only -- the backend independently rejects negative
 * quantity/price and recomputes the line total regardless (spec section 6). */
export function AddItemSheet({ visible, onClose, onSubmit, initial, submitting }: AddItemSheetProps) {
  const { theme } = useTheme();
  const [itemType, setItemType] = useState<QuoteItemType>(initial?.item_type ?? "labour");
  const [name, setName] = useState(initial?.item_name ?? "");
  const [quantity, setQuantity] = useState(initial?.quantity ?? "1");
  const [unitPrice, setUnitPrice] = useState(initial?.unit_price ?? "");

  useEffect(() => {
    if (visible) {
      setItemType(initial?.item_type ?? "labour");
      setName(initial?.item_name ?? "");
      setQuantity(initial?.quantity ?? "1");
      setUnitPrice(initial?.unit_price ?? "");
    }
  }, [visible, initial]);

  const qtyNum = Number(quantity);
  const priceNum = Number(unitPrice);
  const valid = name.trim().length > 0 && qtyNum > 0 && priceNum >= 0;

  return (
    <BottomSheet visible={visible} onClose={onClose} dismissible={!submitting}>
      <AppText variant="title" style={{ marginBottom: theme.spacing.base }}>{initial ? "Edit item" : "Add item"}</AppText>
      <SegmentedControl options={CATEGORY_OPTIONS} value={itemType} onChange={setItemType} disabled={!!initial} />
      <View style={{ height: theme.spacing.base }} />
      <TextField label="Description" value={name} onChangeText={setName} placeholder="e.g. Gas refill & leak repair" />
      <View style={{ height: theme.spacing.sm }} />
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <View style={{ flex: 1 }}>
          <TextField label="Quantity" value={quantity} onChangeText={setQuantity} keyboardType="numeric" />
        </View>
        <View style={{ flex: 1 }}>
          <TextField label="Unit rate (₹)" value={unitPrice} onChangeText={setUnitPrice} keyboardType="numeric" />
        </View>
      </View>
      <View style={{ height: theme.spacing.lg }} />
      <PrimaryButton
        label={initial ? "Save changes" : "Add item"}
        onPress={() => onSubmit({ item_type: itemType, item_name: name.trim(), quantity: qtyNum, unit_price: priceNum })}
        disabled={!valid}
        loading={submitting}
        fullWidth
      />
    </BottomSheet>
  );
}
