import React from "react";
import { View, ViewProps, ScrollView, ScrollViewProps, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView, Edge } from "react-native-safe-area-context";
import { useTheme } from "../design-system/theme";

interface AppScreenProps extends ViewProps {
  /** Renders content inside a ScrollView with keyboard-avoidance -- the
   * common case for form-like or long screens. Defaults to a plain flex
   * container for screens that manage their own scrolling. */
  scroll?: boolean;
  edges?: readonly Edge[];
  contentContainerStyle?: ScrollViewProps["contentContainerStyle"];
}

/** Canonical screen wrapper: theme background + safe area + optional
 * scroll/keyboard-avoidance. Every screen should render inside this rather
 * than a bare View so safe-area and background stay consistent app-wide. */
export function AppScreen({ scroll = false, edges, contentContainerStyle, style, children, ...rest }: AppScreenProps) {
  const { theme } = useTheme();
  const body = scroll ? (
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={[{ flexGrow: 1, padding: theme.layout.screenHorizontalPadding }, contentContainerStyle]}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[{ flex: 1, padding: theme.layout.screenHorizontalPadding }, style]} {...rest}>
      {children}
    </View>
  );

  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
      {scroll ? (
        // `behavior={undefined}` on Android is a no-op -- KeyboardAvoidingView
        // does nothing, so the keyboard can open directly over a focused
        // input on any scroll-mode screen using this wrapper. "height" is
        // the correct Android behavior (matches LoginScreen/ReviewScreen/
        // ChatScreen/AddressBookScreen's own KeyboardAvoidingView usage).
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : "height"}>
          {body}
        </KeyboardAvoidingView>
      ) : (
        body
      )}
    </SafeAreaView>
  );
}
