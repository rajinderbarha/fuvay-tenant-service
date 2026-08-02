import React from "react";
import { Modal, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { IconButton } from "../actions/IconButton";

export interface FullScreenModalProps {
  visible: boolean;
  title?: string;
  onClose: () => void;
  children: React.ReactNode;
}

/** Shell for a full-screen modal flow (e.g. a multi-step form). Feature
 * screens render their own content inside; this only provides the
 * chrome (header + close) and safe-area handling. */
export function FullScreenModal({ visible, title, onClose, children }: FullScreenModalProps) {
  const { theme } = useTheme();
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose} presentationStyle="pageSheet">
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: theme.spacing.base, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
          {title ? <AppText variant="title">{title}</AppText> : <View />}
          <IconButton icon="close" accessibilityLabel="Close" onPress={onClose} />
        </View>
        <View style={{ flex: 1 }}>{children}</View>
      </SafeAreaView>
    </Modal>
  );
}
