import React, { useEffect } from "react";
import { Modal, View, BackHandler, TouchableWithoutFeedback } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface BottomSheetProps {
  visible: boolean;
  onClose: () => void;
  children: React.ReactNode;
  accessibilityLabel: string;
}

/**
 * Application-level bottom-sheet wrapper. No third-party sheet library is
 * added in this sprint (none was present and none is required yet) — this
 * is a Modal-based implementation with the standard interaction contract
 * (scrim tap to dismiss, Android back button, safe-area handling).
 */
export function BottomSheet({ visible, onClose, children, accessibilityLabel }: BottomSheetProps) {
  const { theme } = useAppTheme();

  useEffect(() => {
    if (!visible) return;
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      onClose();
      return true;
    });
    return () => sub.remove();
  }, [visible, onClose]);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose} accessibilityViewIsModal>
      <TouchableWithoutFeedback onPress={onClose} accessibilityLabel="Close">
        <View style={{ flex: 1, backgroundColor: theme.colors.scrim, justifyContent: "flex-end" }}>
          <TouchableWithoutFeedback>
            <SafeAreaView
              edges={["bottom"]}
              accessibilityRole="none"
              accessibilityLabel={accessibilityLabel}
              style={{
                backgroundColor: theme.colors.backgroundElevated,
                borderTopLeftRadius: theme.radii.xl,
                borderTopRightRadius: theme.radii.xl,
                padding: theme.spacing[7],
                ...theme.shadows.lg,
              }}
            >
              {children}
            </SafeAreaView>
          </TouchableWithoutFeedback>
        </View>
      </TouchableWithoutFeedback>
    </Modal>
  );
}
