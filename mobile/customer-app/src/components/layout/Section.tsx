import React from "react";
import { View } from "react-native";
import { AppText } from "../primitives/AppText";
import { Stack } from "./Stack";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface SectionProps {
  title?: string;
  children: React.ReactNode;
}

/** Groups related content with a consistent heading + spacing rhythm. */
export function Section({ title, children }: SectionProps) {
  const { theme } = useAppTheme();
  return (
    <View style={{ marginBottom: theme.spacing[8] }}>
      {title ? (
        <AppText variant="titleSmall" color="textSecondary" style={{ marginBottom: theme.spacing[4], textTransform: "uppercase" }}>
          {title}
        </AppText>
      ) : null}
      <Stack gap={4}>{children}</Stack>
    </View>
  );
}
