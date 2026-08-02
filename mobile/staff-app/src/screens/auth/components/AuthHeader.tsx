import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";

/**
 * Branded auth-flow header (Phase G). Screen-local rather than a
 * design-system primitive -- this exact wordmark+theme-toggle chrome is
 * specific to the authentication flow's visual identity; job-execution and
 * tab screens use the generic MobileHeader (design-system/components/navigation)
 * instead, so this deliberately isn't added there.
 */
export function AuthHeader() {
  const { theme, mode, setPreference } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: theme.spacing.lg }}>
      <View>
        <View style={{ flexDirection: "row", alignItems: "baseline" }}>
          <AppText variant="headingLarge" style={{ color: theme.colors.textPrimary }}>Service</AppText>
          <AppText variant="headingLarge" style={{ color: theme.colors.brandPrimary }}>OS</AppText>
        </View>
        <AppText variant="label" color="tertiary">Technician App</AppText>
      </View>
      <Pressable
        onPress={() => setPreference(mode === "dark" ? "light" : "dark")}
        accessibilityRole="button"
        accessibilityLabel={mode === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        hitSlop={8}
        style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}
      >
        <Icon name={mode === "dark" ? "moon-outline" : "sunny-outline"} size="standard" color={theme.colors.textSecondary} decorative />
      </Pressable>
    </View>
  );
}
