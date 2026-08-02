import React, { useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { BottomSheet } from "../../../design-system/components/overlays/BottomSheet";
import { AppText } from "../../../design-system/components/typography/AppText";
import { TextField } from "../../../design-system/components/forms/TextField";
import { TextArea } from "../../../design-system/components/forms/TextArea";
import { PrimaryButton } from "../../../design-system/components/actions/Buttons";

export interface RequestPartSheetProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (body: { part_name: string; quantity: number; estimated_cost: number; reason: string }) => void;
  submitting: boolean;
}

/** The technician never approves their own request -- tenant/business
 * decisioning happens entirely outside this app (spec sections 10, 25). */
export function RequestPartSheet({ visible, onClose, onSubmit, submitting }: RequestPartSheetProps) {
  const { theme } = useTheme();
  const [partName, setPartName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [cost, setCost] = useState("");
  const [reason, setReason] = useState("");

  const valid = partName.trim().length > 0 && Number(quantity) > 0 && Number(cost) >= 0 && reason.trim().length > 0;

  return (
    <BottomSheet visible={visible} onClose={onClose} dismissible={!submitting}>
      <AppText variant="title" style={{ marginBottom: theme.spacing.base }}>Request part</AppText>
      <TextField label="Part / material" value={partName} onChangeText={setPartName} placeholder="e.g. Copper pipe" />
      <View style={{ height: theme.spacing.sm }} />
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <View style={{ flex: 1 }}><TextField label="Quantity" value={quantity} onChangeText={setQuantity} keyboardType="numeric" /></View>
        <View style={{ flex: 1 }}><TextField label="Estimated cost (₹)" value={cost} onChangeText={setCost} keyboardType="numeric" /></View>
      </View>
      <View style={{ height: theme.spacing.sm }} />
      <TextArea label="Reason" value={reason} onChangeText={setReason} placeholder="Why is this part needed?" minLines={3} />
      <View style={{ height: theme.spacing.lg }} />
      <PrimaryButton
        label="Send request"
        onPress={() => onSubmit({ part_name: partName.trim(), quantity: Number(quantity), estimated_cost: Number(cost), reason: reason.trim() })}
        disabled={!valid}
        loading={submitting}
        fullWidth
      />
    </BottomSheet>
  );
}
