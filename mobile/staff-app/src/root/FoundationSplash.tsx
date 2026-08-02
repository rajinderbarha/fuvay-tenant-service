import React from "react";
import { View, Text, Pressable } from "react-native";
import { useTheme } from "../design-system/themes";

/**
 * Temporary foundation-proof view -- NOT a feature screen. Confirms tokens/
 * theme/System-Light-Dark switching render correctly before Phase D
 * (component library) and Phase E (navigation/auth shell) are built.
 * Replace with RootNavigator once the application shell phase lands.
 */
export function FoundationSplash() {
  const { theme, preference, setPreference, mode } = useTheme();
  const { colors, spacing, typography, radius } = theme;

  return (
    <View style={{ flex: 1, backgroundColor: colors.backgroundPrimary, padding: spacing.lg, justifyContent: "center" }}>
      <Text style={[typography.headingLarge, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
        ServiceOS Technician
      </Text>
      <Text style={[typography.body, { color: colors.textSecondary, marginBottom: spacing.xl }]}>
        Design foundation preview -- {mode} mode active.
      </Text>

      <View style={{ flexDirection: "row", gap: spacing.sm }}>
        {(["system", "light", "dark"] as const).map(p => (
          <Pressable
            key={p}
            onPress={() => setPreference(p)}
            style={{
              paddingVertical: spacing.sm,
              paddingHorizontal: spacing.base,
              borderRadius: radius.radiusMedium,
              backgroundColor: preference === p ? colors.brandPrimary : colors.surfaceInteractive,
              borderWidth: 1,
              borderColor: preference === p ? colors.brandPrimary : colors.borderDefault,
            }}
          >
            <Text style={[typography.button, { color: preference === p ? colors.brandOnPrimary : colors.textPrimary }]}>
              {p[0].toUpperCase() + p.slice(1)}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={{ marginTop: spacing.xxl, padding: spacing.base, borderRadius: radius.radiusLarge, backgroundColor: colors.surfaceDefault, borderWidth: 1, borderColor: colors.borderSubtle }}>
        <Text style={[typography.label, { color: colors.textTertiary, marginBottom: spacing.xs }]}>STATUS TOKEN PREVIEW</Text>
        {(["statusSuccess", "statusWarning", "statusDanger", "statusInfo"] as const).map(key => (
          <Text key={key} style={[typography.bodySmall, { color: colors[key], marginBottom: spacing.xxs }]}>
            {key}
          </Text>
        ))}
      </View>
    </View>
  );
}
