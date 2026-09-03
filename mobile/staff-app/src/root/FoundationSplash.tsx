import React from "react";
import { ActivityIndicator, Image, View, Text } from "react-native";
import { useTheme } from "../design-system/themes";

/** Branded cold-start screen shown while the stored session is restored. */
export function FoundationSplash() {
  const { theme } = useTheme();
  const { colors, spacing, typography } = theme;

  return (
    <View
      accessibilityLabel="Loading Fuvay Staff"
      style={{
        flex: 1,
        backgroundColor: colors.backgroundPrimary,
        padding: spacing.lg,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <Image source={require("../../assets/fuvay-logo-native.png")} resizeMode="contain"
        accessibilityLabel="Fuvay" style={{ width: 228, height: 72, marginBottom: spacing.lg }} />
      <Text style={[typography.headingLarge, { color: colors.textPrimary, marginBottom: spacing.sm, textAlign: "center" }]}>Fuvay Staff</Text>
      <Text style={[typography.body, { color: colors.textSecondary, marginBottom: spacing.xl, textAlign: "center" }]}>
        Checking your secure session…
      </Text>
      <ActivityIndicator size="large" color={colors.brandPrimary} accessibilityLabel="Loading" />
    </View>
  );
}
