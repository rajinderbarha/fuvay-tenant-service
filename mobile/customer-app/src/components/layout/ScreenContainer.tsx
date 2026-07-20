import React from "react";
import { View, ScrollView, KeyboardAvoidingView, Platform, RefreshControl, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface ScreenContainerProps {
  children: React.ReactNode;
  scrollable?: boolean;
  background?: "primary" | "secondary";
  maxContentWidth?: boolean;
  onRefresh?: () => void;
  refreshing?: boolean;
  style?: ViewStyle;
}

/**
 * The standard screen wrapper: safe areas, optional scrolling, keyboard
 * avoidance, and a centered max-width for tablets. Screens should not
 * re-implement this by hand.
 */
export function ScreenContainer({
  children,
  scrollable = true,
  background = "primary",
  maxContentWidth = true,
  onRefresh,
  refreshing = false,
  style,
}: ScreenContainerProps) {
  const { theme } = useAppTheme();
  const backgroundColor = background === "primary" ? theme.colors.backgroundPrimary : theme.colors.backgroundSecondary;

  const content = (
    <View
      style={[
        { flex: 1, width: "100%", paddingHorizontal: theme.sizes.screenHorizontalPadding as number },
        maxContentWidth ? { maxWidth: theme.sizes.maxContentWidth as number, alignSelf: "center" } : null,
        style,
      ]}
    >
      {children}
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor }} edges={["top", "bottom", "left", "right"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {scrollable ? (
          <ScrollView
            contentContainerStyle={{ flexGrow: 1 }}
            keyboardShouldPersistTaps="handled"
            refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.iconPrimary} /> : undefined}
          >
            {content}
          </ScrollView>
        ) : (
          content
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
