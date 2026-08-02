import React from "react";
import { Modal, View, Pressable } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { PrimaryButton, SecondaryButton, DestructiveButton } from "../actions/Buttons";
import { zIndex } from "../../tokens/zIndex";

export interface ConfirmationDialogProps {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Confirmation dialog for destructive/high-risk actions. `loading` blocks
 * a second tap on the confirm button while the async action is in flight. */
export function ConfirmationDialog({ visible, title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", destructive, loading, onConfirm, onCancel }: ConfirmationDialogProps) {
  const { theme } = useTheme();
  const ConfirmButton = destructive ? DestructiveButton : PrimaryButton;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <View style={{ flex: 1, backgroundColor: theme.colors.backgroundOverlay, alignItems: "center", justifyContent: "center", padding: theme.spacing.xl, zIndex: zIndex.modal }}>
        <Pressable style={{ position: "absolute", inset: 0 }} onPress={loading ? undefined : onCancel} />
        <View style={{ width: "100%", maxWidth: 360, backgroundColor: theme.colors.surfaceRaised, borderRadius: theme.radiusUsage.card, padding: theme.spacing.lg, ...theme.shadow.lg }}>
          <AppText variant="headingSmall" style={{ marginBottom: theme.spacing.xs }}>{title}</AppText>
          <AppText variant="bodySmall" color="secondary" style={{ marginBottom: theme.spacing.lg }}>{message}</AppText>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            <View style={{ flex: 1 }}><SecondaryButton label={cancelLabel} onPress={onCancel} disabled={loading} fullWidth /></View>
            <View style={{ flex: 1 }}><ConfirmButton label={confirmLabel} onPress={onConfirm} loading={loading} fullWidth /></View>
          </View>
        </View>
      </View>
    </Modal>
  );
}
