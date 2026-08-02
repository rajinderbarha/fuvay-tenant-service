import React, { useEffect } from "react";
import { Modal, View, Pressable, BackHandler } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../../themes";
import { zIndex } from "../../tokens/zIndex";

export interface BottomSheetProps {
  visible: boolean;
  onClose: () => void;
  children: React.ReactNode;
  /** Prevent dismissal while a submit/upload is in flight. */
  dismissible?: boolean;
}

/**
 * BottomSheet foundation -- safe-area aware, backdrop dismissible (unless
 * `dismissible=false`), Android hardware back-button closes it. Built on
 * RN's built-in Modal rather than adding a new gesture library, per
 * "prove the current system cannot support the requirement" (it can).
 */
export function BottomSheet({ visible, onClose, children, dismissible = true }: BottomSheetProps) {
  const { theme } = useTheme();

  useEffect(() => {
    if (!visible) return;
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (dismissible) onClose();
      return true;
    });
    return () => sub.remove();
  }, [visible, dismissible, onClose]);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={() => dismissible && onClose()}>
      <Pressable
        style={{ flex: 1, backgroundColor: theme.colors.backgroundOverlay, justifyContent: "flex-end", zIndex: zIndex.bottomSheet }}
        onPress={() => dismissible && onClose()}
        accessibilityLabel="Close"
      >
        <Pressable onPress={e => e.stopPropagation()}>
          <SafeAreaView edges={["bottom"]} style={{ backgroundColor: theme.colors.surfaceRaised, borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card }}>
            <View style={{ alignItems: "center", paddingTop: theme.spacing.sm }}>
              <View style={{ width: 36, height: 4, borderRadius: 2, backgroundColor: theme.colors.borderStrong }} />
            </View>
            <View style={{ padding: theme.spacing.base }}>{children}</View>
          </SafeAreaView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
