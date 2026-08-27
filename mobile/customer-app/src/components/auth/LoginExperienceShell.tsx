import React from "react";
import { Image, View, useWindowDimensions } from "react-native";
import Svg, { Line, Path, Rect } from "react-native-svg";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../AppScreen";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { LegalLinksFooter } from "./LegalLinksFooter";
import { LoginMethod, LoginMethodSegmentedControl } from "./LoginMethodSegmentedControl";

interface LoginExperienceShellProps {
  method: LoginMethod;
  onMethodChange: (method: LoginMethod) => void;
  securityMessage: string;
  onSignup: () => void;
  children: React.ReactNode;
}

function CityLineArt() {
  const { theme } = useTheme();
  return (
    <Svg width="100%" height="190" viewBox="0 0 430 190" fill="none" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Path d="M0 188H430M12 188V109H72V188M28 109V86L43 66L59 86V109M85 188V73H145V188M99 73V52H132V73M158 188V97H222V188M176 97V79H204V97M237 188V66H303V188M252 66V45H288V66M318 188V111H418V188M343 111V84H391V111" stroke={theme.colors.borderSubtle} strokeWidth="2" />
      {[30, 50, 102, 125, 178, 202, 259, 282, 343, 370, 397].map((x, index) => (
        <Rect key={x} x={x} y={index % 2 ? 128 : 119} width="9" height="12" rx="2" stroke={theme.colors.borderSubtle} />
      ))}
      <Line x1="0" y1="164" x2="430" y2="164" stroke={theme.colors.borderSubtle} />
    </Svg>
  );
}

/** Shared visual shell for both sign-in methods. Authentication state and
 * network calls remain in their route screens; this component owns only the
 * branded, responsive presentation. */
export function LoginExperienceShell({ method, onMethodChange, securityMessage, onSignup, children }: LoginExperienceShellProps) {
  const { theme } = useTheme();
  const { width } = useWindowDimensions();
  const dark = theme.mode === "dark";
  const contentWidth = Math.min(560, Math.max(280, width - theme.spacing.xl * 2));
  const logoWidth = Math.min(330, contentWidth - theme.spacing.xl);
  const logoSource = dark
    ? require("../../../assets/fuvay-logo-native.png")
    : require("../../../assets/fuvay-logo.png");

  return (
    <AppScreen scroll contentContainerStyle={{ padding: 0 }}>
      <View style={{ flex: 1, minHeight: 760, backgroundColor: theme.colors.backgroundPrimary, overflow: "hidden" }}>
        <View pointerEvents="none" style={{ position: "absolute", left: -46, top: 142, width: 112, height: 190, borderRadius: 56, backgroundColor: theme.colors.brandPrimaryMuted, opacity: dark ? 0.28 : 0.72 }} />
        <View pointerEvents="none" style={{ position: "absolute", right: -54, top: 48, width: 116, height: 202, borderRadius: 58, backgroundColor: theme.colors.brandPrimaryMuted, opacity: dark ? 0.28 : 0.72 }} />
        <View pointerEvents="none" style={{ position: "absolute", left: 30, top: 86, width: 54, flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {Array.from({ length: 12 }, (_, index) => <View key={index} style={{ width: 3, height: 3, borderRadius: 2, backgroundColor: theme.colors.brandPrimary, opacity: 0.32 }} />)}
        </View>

        <View style={{ width: contentWidth, alignSelf: "center", paddingTop: theme.spacing.huge, paddingHorizontal: theme.spacing.sm }}>
          <View style={{ alignItems: "center" }}>
            <Image source={logoSource} resizeMode="contain" style={{ width: logoWidth, height: Math.round(logoWidth / 3.25) }} accessibilityRole="image" accessibilityLabel="Fuvay, Far Away in Fare Way" accessibilityIgnoresInvertColors />
            <View style={{ width: Math.min(230, contentWidth * 0.58), height: 2, marginTop: theme.spacing.md, backgroundColor: theme.colors.brandPrimary, borderRadius: 1, opacity: 0.9 }} />
          </View>

          <View style={{ marginTop: theme.spacing.xxl, alignItems: "center" }}>
            <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "center" }}>
              <AppText variant="headingLarge" accessibilityRole="header">Welcome </AppText>
              <AppText variant="headingLarge" style={{ color: theme.colors.brandPrimaryStrong }}>Fuvay!</AppText>
            </View>
            <AppText variant="body" color="secondary" align="center" style={{ marginTop: theme.spacing.xs }}>
              Sign in to continue to your account
            </AppText>
          </View>

          <View style={{ marginTop: theme.spacing.xl }}>
            <LoginMethodSegmentedControl value={method} onChange={onMethodChange} />
          </View>

          {children}

          <View style={{ marginTop: theme.spacing.xl, minHeight: 82, borderRadius: theme.radius.radiusLarge, borderWidth: 1, borderColor: theme.colors.borderSubtle, backgroundColor: theme.colors.surfaceInteractive, paddingHorizontal: theme.spacing.lg, paddingVertical: theme.spacing.base, flexDirection: "row", alignItems: "center", gap: theme.spacing.md }}>
            <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
            <AppText variant="bodySmall" style={{ flex: 1 }}>{securityMessage}</AppText>
          </View>
        </View>

        <View pointerEvents="none" style={{ height: 150, marginTop: theme.spacing.sm, opacity: dark ? 0.26 : 0.52 }}>
          <CityLineArt />
        </View>

        <View style={{ position: "relative", minHeight: 240, marginTop: -34, paddingTop: 68, paddingHorizontal: theme.spacing.xl, paddingBottom: theme.spacing.xl, backgroundColor: theme.colors.brandPrimary, overflow: "hidden" }}>
          <View pointerEvents="none" style={{ position: "absolute", top: -92, left: -width * 0.25, width: width * 1.5, height: 124, borderRadius: width, backgroundColor: theme.colors.backgroundPrimary }} />
          <View style={{ width: contentWidth, maxWidth: "100%", alignSelf: "center", alignItems: "center" }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
              <Icon name="person-add-outline" size="standard" color={theme.colors.brandOnPrimary} decorative />
              <AppText variant="bodyStrong" style={{ color: theme.colors.brandOnPrimary }}>New to Fuvay? Create an account</AppText>
            </View>
            <View style={{ width: "100%", marginTop: theme.spacing.base }}>
              <View style={{ minHeight: 50, borderRadius: theme.radius.radiusMedium, backgroundColor: theme.colors.brandOnPrimary, alignItems: "center", justifyContent: "center" }}>
                <AppText variant="button" accessibilityRole="button" accessibilityLabel="Sign Up" onPress={onSignup} style={{ width: "100%", paddingVertical: theme.spacing.base, color: theme.colors.brandPrimaryPressed, textAlign: "center" }}>
                  Sign Up  →
                </AppText>
              </View>
            </View>
            <View style={{ marginTop: theme.spacing.lg }}>
              <LegalLinksFooter inverse />
            </View>
          </View>
        </View>
      </View>
    </AppScreen>
  );
}
