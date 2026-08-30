import React, { useMemo } from "react";
import { View, useWindowDimensions } from "react-native";

import { useTheme } from "../../design-system/theme";
import { buildFuvayTheme } from "../../design-system/tokens/fuvay";
import { AppScreen } from "../AppScreen";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";
import { LegalLinksFooter } from "./LegalLinksFooter";
import { LoginMethod, LoginMethodSegmentedControl } from "./LoginMethodSegmentedControl";

interface LoginExperienceShellProps {
  method: LoginMethod;
  onMethodChange: (method: LoginMethod) => void;
  securityMessage: string;
  onSignup: () => void;
  children: React.ReactNode;
}

/**
 * Shared visual shell for both sign-in methods — Fuvay v2.
 *
 * The v2 canvas replaces the previous centred-logo + city-line-art +
 * brand-footer composition with a two-part layout: a dark header carrying an
 * eyebrow and a large headline, and a rounded panel that holds the whole
 * form. The panel is the visual anchor, so it takes the remaining height
 * rather than being a card floating in the middle.
 *
 * Authentication state and network calls remain in the route screens; this
 * component owns only presentation, and its props are unchanged so both
 * LoginMethodScreen and PasswordLoginScreen keep working untouched.
 *
 * `securityMessage` is rendered as the FIRST of the three reassurance points
 * rather than a separate callout: the callers pass a method-specific message
 * (OTP vs password), and dropping it in favour of the canvas's fixed copy
 * would lose that distinction.
 */
export function LoginExperienceShell({
  method,
  onMethodChange,
  securityMessage,
  onSignup,
  children,
}: LoginExperienceShellProps) {
  const { theme, mode } = useTheme();
  const fuvay = useMemo(() => buildFuvayTheme(mode === "dark"), [mode]);
  const { width, height } = useWindowDimensions();
  const compact =
    width <= theme.layout.authCompactWidthBreakpoint ||
    height <= theme.layout.authCompactHeightBreakpoint;

  /** The two universal points from the canvas; the caller's own message
   *  leads, so the list stays method-accurate. */
  const points: { label: string; icon: IconProps["name"]; color: string }[] = [
    { label: securityMessage, icon: "shield-checkmark-outline", color: fuvay.accents.a3 },
    { label: "Your number is never shared with pros", icon: "eye-off-outline", color: fuvay.accents.a2 },
    { label: "Track and reschedule any booking", icon: "calendar-outline", color: fuvay.accents.a1 },
  ];

  return (
    <AppScreen scroll contentContainerStyle={{ padding: 0, flexGrow: 1 }}>
      <View style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary, overflow: "hidden" }}>
        {/* Ambient glow, top-right, matching the canvas. */}
        <View
          pointerEvents="none"
          style={{
            position: "absolute",
            right: -120,
            top: -140,
            width: 300,
            height: 300,
            borderRadius: 150,
            backgroundColor: fuvay.surfaces.glowTint,
          }}
        />

        {/* ── Header ─────────────────────────────────────────────────── */}
        <View style={{ paddingHorizontal: 26, paddingTop: compact ? 32 : 52, paddingBottom: 30, gap: 20 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <View style={{ width: 26, height: 1, backgroundColor: fuvay.accents.a2 }} />
            <AppText variant="metaLabelWide" style={{ color: fuvay.accents.a2 }}>
              SIGN IN
            </AppText>
          </View>
          <View style={{ gap: 10 }}>
            <AppText variant="displayLarge" accessibilityRole="header">
              Your home,{"\n"}one number away.
            </AppText>
            <AppText variant="body" color="secondary" style={{ maxWidth: 270 }}>
              Enter your mobile number and we&apos;ll send a one-time code — no password to
              remember.
            </AppText>
          </View>
        </View>

        {/* ── Panel ──────────────────────────────────────────────────── */}
        <View
          style={{
            flex: 1,
            marginHorizontal: 14,
            paddingHorizontal: 20,
            paddingTop: 22,
            paddingBottom: 24,
            borderTopLeftRadius: 28,
            borderTopRightRadius: 28,
            borderBottomLeftRadius: theme.radius.radiusShell,
            borderBottomRightRadius: theme.radius.radiusShell,
            backgroundColor: theme.colors.surfaceDefault,
            borderWidth: 1,
            borderColor: theme.colors.borderSubtle,
            ...theme.shadow.md,
          }}
        >
          <LoginMethodSegmentedControl value={method} onChange={onMethodChange} />

          {children}

          <View style={{ marginTop: 20, gap: 12 }}>
            {points.map((pt) => (
              <View key={pt.label} style={{ flexDirection: "row", alignItems: "center", gap: 11 }}>
                <Icon name={pt.icon} size="compact" color={pt.color} decorative />
                <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>
                  {pt.label}
                </AppText>
              </View>
            ))}
          </View>

          <View style={{ marginTop: "auto", paddingTop: 22, gap: 14 }}>
            <View style={{ height: 1, backgroundColor: theme.colors.divider }} />
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <AppText variant="bodySmall" color="secondary">
                New to Fuvay?
              </AppText>
              <AppText
                variant="button"
                accessibilityRole="button"
                accessibilityLabel="Create account"
                onPress={onSignup}
                style={{
                  minHeight: theme.touchTargets.minimum,
                  paddingHorizontal: 20,
                  paddingVertical: 13,
                  borderRadius: theme.radiusUsage.button,
                  borderWidth: 1.5,
                  borderColor: fuvay.accents.a2,
                  color: fuvay.accents.a2,
                  textAlign: "center",
                }}
              >
                Create account
              </AppText>
            </View>
            <LegalLinksFooter />
          </View>
        </View>
      </View>
    </AppScreen>
  );
}
