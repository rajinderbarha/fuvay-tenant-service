import React from "react";
import { Linking, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";

/**
 * Real configured destinations (spec section 17) -- never a hardcoded
 * temporary URL baked into the component. `EXPO_PUBLIC_TERMS_URL` /
 * `EXPO_PUBLIC_PRIVACY_URL` follow the same `EXPO_PUBLIC_*`-only-safe-to-
 * be-public convention as `EXPO_PUBLIC_API_BASE_URL` (see
 * config/environment.ts) -- add both to `.env.example` alongside it.
 * Opens in the system browser (`Linking.openURL`), never an in-app
 * webview capable of arbitrary navigation.
 */
const TERMS_URL = process.env.EXPO_PUBLIC_TERMS_URL;
const PRIVACY_URL = process.env.EXPO_PUBLIC_PRIVACY_URL;

export function LegalLinksFooter() {
  const { theme } = useTheme();

  function openIfConfigured(url: string | undefined) {
    if (!url) return; // Fails safe: no destination configured yet -- see Phase G report "backend/config gaps".
    Linking.openURL(url).catch(() => {});
  }

  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "center" }}>
      <AppText variant="caption" color="tertiary" align="center">
        By continuing, you agree to our{" "}
      </AppText>
      <AppText
        variant="caption"
        color="link"
        accessibilityRole="link"
        accessibilityLabel="Open Terms of Service"
        onPress={() => openIfConfigured(TERMS_URL)}
      >
        Terms
      </AppText>
      <AppText variant="caption" color="tertiary"> and </AppText>
      <AppText
        variant="caption"
        color="link"
        accessibilityRole="link"
        accessibilityLabel="Open Privacy Policy"
        onPress={() => openIfConfigured(PRIVACY_URL)}
      >
        Privacy Policy
      </AppText>
      <AppText variant="caption" color="tertiary">.</AppText>
    </View>
  );
}
