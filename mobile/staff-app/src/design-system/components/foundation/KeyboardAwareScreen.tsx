import React from "react";
import { KeyboardAvoidingView, Platform, ScrollView, ScrollViewProps } from "react-native";
import { SafeAreaView, Edge } from "react-native-safe-area-context";
import { useTheme } from "../../themes";

export interface KeyboardAwareScreenProps extends ScrollViewProps {
  edges?: readonly Edge[];
}

/** Scrollable screen that avoids the keyboard -- use for forms (auth,
 * inspection notes, estimate line items, etc). */
export function KeyboardAwareScreen({ style, contentContainerStyle, children, edges = ["top", "bottom", "left", "right"], ...rest }: KeyboardAwareScreenProps) {
  const { theme } = useTheme();
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
      >
        <ScrollView
          style={[{ flex: 1 }, style]}
          contentContainerStyle={contentContainerStyle}
          keyboardShouldPersistTaps="handled"
          {...rest}
        >
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
