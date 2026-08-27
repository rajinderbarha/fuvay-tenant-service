import React from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";

/**
 * Terms / Privacy links on the auth screens.
 *
 * These used to open `EXPO_PUBLIC_TERMS_URL` / `EXPO_PUBLIC_PRIVACY_URL` in
 * the system browser. Neither variable was ever configured, and the component
 * failed safe by doing nothing — so on every build shipped so far, tapping
 * either link was a no-op above a sentence promising the reader they had
 * agreed to something they could not read.
 *
 * Both now open the in-app LegalDocumentScreen, which reads the published
 * text from /v1/public/legal. That endpoint takes no session, which is what
 * makes it usable from here: nobody on this screen is signed in yet.
 */

const TERMS_DOC_TYPE = "terms_of_service";
const PRIVACY_DOC_TYPE = "privacy_policy";

export function LegalLinksFooter({ inverse = false }: { inverse?: boolean }) {
  const { theme } = useTheme();
  const navigation = useNavigation<{
    navigate: (screen: string, params: { docType: string; title: string }) => void;
  }>();

  function open(docType: string, title: string) {
    navigation.navigate("LegalDocument", { docType, title });
  }

  const linkStyle = inverse
    ? { color: theme.colors.brandOnPrimary, textDecorationLine: "underline" as const }
    : undefined;
  const plainStyle = inverse ? { color: theme.colors.brandOnPrimary } : undefined;

  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "center" }}>
      <AppText variant="caption" color={inverse ? undefined : "tertiary"} align="center" style={plainStyle}>
        By continuing, you agree to our{" "}
      </AppText>
      <AppText
        variant="caption"
        color={inverse ? undefined : "link"}
        style={linkStyle}
        accessibilityRole="link"
        accessibilityLabel="Open Terms of Service"
        onPress={() => open(TERMS_DOC_TYPE, "Terms of Service")}
      >
        Terms
      </AppText>
      <AppText variant="caption" color={inverse ? undefined : "tertiary"} style={plainStyle}> and </AppText>
      <AppText
        variant="caption"
        color={inverse ? undefined : "link"}
        style={linkStyle}
        accessibilityRole="link"
        accessibilityLabel="Open Privacy Policy"
        onPress={() => open(PRIVACY_DOC_TYPE, "Privacy Policy")}
      >
        Privacy Policy
      </AppText>
      <AppText variant="caption" color={inverse ? undefined : "tertiary"} style={plainStyle}>.</AppText>
    </View>
  );
}
