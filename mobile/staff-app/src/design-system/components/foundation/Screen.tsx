import React from "react";
import { View, ViewProps } from "react-native";
import { useTheme } from "../../themes";

/** Plain full-flex screen background -- no safe-area, no scroll. Use
 * SafeAreaScreen/ScrollScreen/KeyboardAwareScreen for the common cases. */
export function Screen({ style, children, ...rest }: ViewProps) {
  const { theme } = useTheme();
  return (
    <View style={[{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }, style]} {...rest}>
      {children}
    </View>
  );
}
