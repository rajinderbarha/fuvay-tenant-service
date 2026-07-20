import React, { useEffect } from "react";
import { Modal, View, BackHandler } from "react-native";
import { AppText } from "../primitives/AppText";
import { AppButton } from "../primitives/AppButton";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface ConfirmationModalProps {
  visible: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Shared confirmation / destructive-confirmation modal. Business features
 * pass their own copy; the interaction behavior (Android back button, safe
 * area, scrim) is standardized here.
 */
export function ConfirmationModal({
  visible,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive,
  onConfirm,
  onCancel,
}: ConfirmationModalProps) {
  const { theme } = useAppTheme();

  useEffect(() => {
    if (!visible) return;
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      onCancel();
      return true;
    });
    return () => sub.remove();
  }, [visible, onCancel]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel} accessibilityViewIsModal>
      <View style={{ flex: 1, backgroundColor: theme.colors.scrim, alignItems: "center", justifyContent: "center", padding: theme.spacing[7] }}>
        <View
          accessible
          accessibilityRole="alert"
          style={{
            width: "100%",
            maxWidth: 360,
            backgroundColor: theme.colors.backgroundElevated,
            borderRadius: theme.radii.lg,
            padding: theme.spacing[7],
            gap: theme.spacing[5],
            ...theme.shadows.lg,
          }}
        >
          <AppText variant="headingSmall">{title}</AppText>
          {description ? (
            <AppText variant="bodyMedium" color="textSecondary">
              {description}
            </AppText>
          ) : null}
          <View style={{ flexDirection: "row", justifyContent: "flex-end", gap: theme.spacing[3] }}>
            <AppButton label={cancelLabel} onPress={onCancel} variant="text" size="medium" />
            <AppButton label={confirmLabel} onPress={onConfirm} variant={destructive ? "destructive" : "primary"} size="medium" />
          </View>
        </View>
      </View>
    </Modal>
  );
}
