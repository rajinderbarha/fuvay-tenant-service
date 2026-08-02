import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { IconButton } from "../../../design-system/components/actions/IconButton";

/** Shared back-header for every Profile sub-screen -- mirrors the pattern
 * already established in ManageAvailabilityScreen.tsx (Phase P). */
export function ScreenHeader({ title, onBack }: { title: string; onBack: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
      <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={onBack} />
      <AppText variant="bodyStrong" style={{ flex: 1, textAlign: "center" }}>{title}</AppText>
      <View style={{ width: 44 }} />
    </View>
  );
}
