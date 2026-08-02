import React from "react";
import { ViewProps, View } from "react-native";
import { SafeAreaView, Edge } from "react-native-safe-area-context";
import { useTheme } from "../../themes";

export interface SafeAreaScreenProps extends ViewProps {
  edges?: readonly Edge[];
}

/** Safe-area-aware full-flex screen. Use for the top-level content of a
 * stack/tab screen (bottom nav already reserves its own inset, so screens
 * nested inside a bottom-tab navigator typically want edges=["top","left","right"]). */
export function SafeAreaScreen({ style, children, edges = ["top", "bottom", "left", "right"], ...rest }: SafeAreaScreenProps) {
  const { theme } = useTheme();
  return (
    <SafeAreaView edges={edges} style={[{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }, style]} {...rest}>
      <View style={{ flex: 1 }}>{children}</View>
    </SafeAreaView>
  );
}
