import React from "react";
import { ScrollView, ScrollViewProps } from "react-native";
import { SafeAreaView, Edge } from "react-native-safe-area-context";
import { useTheme } from "../../themes";

export interface ScrollScreenProps extends ScrollViewProps {
  edges?: readonly Edge[];
}

/** Safe-area-aware scrollable screen with sensible defaults (no bounce
 * flash of empty color, horizontal screen padding via contentContainerStyle
 * left to the caller so this stays a foundation primitive, not a layout
 * decision-maker). */
export function ScrollScreen({ style, contentContainerStyle, children, edges = ["top", "bottom", "left", "right"], ...rest }: ScrollScreenProps) {
  const { theme } = useTheme();
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
      <ScrollView
        style={[{ flex: 1 }, style]}
        contentContainerStyle={contentContainerStyle}
        keyboardShouldPersistTaps="handled"
        {...rest}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
