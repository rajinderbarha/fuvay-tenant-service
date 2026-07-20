import React from "react";
import { View } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { SpacingKey } from "../../design-system/tokens/spacing";

export function Spacer({ size = 6 }: { size?: SpacingKey }) {
  const { theme } = useAppTheme();
  return <View style={{ width: theme.spacing[size], height: theme.spacing[size] }} />;
}
