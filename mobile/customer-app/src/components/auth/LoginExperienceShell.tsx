import React, { useMemo } from "react";
import { View, useWindowDimensions } from "react-native";

import { useTheme } from "../../design-system/theme";
import { buildFuvayTheme } from "../../design-system/tokens/fuvay";
import { AppScreen } from "../AppScreen";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon, IconProps } from "../Icon";
import { FuvayAmbientCanvas, FuvayEyebrow, FuvayPanel } from "../fuvay";
import { LegalLinksFooter } from "./LegalLinksFooter";
import { LoginMethod, LoginMethodSegmentedControl } from "./LoginMethodSegmentedControl";
import { customerExperienceCopy } from "../../content/customerExperience";

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
  const copy = customerExperienceCopy.login;
  const compact =
    width <= theme.layout.authCompactWidthBreakpoint ||
    height <= theme.layout.authCompactHeightBreakpoint;

  /** The two universal points from the canvas; the caller's own message
   *  leads, so the list stays method-accurate. */
  const points: { label: string; icon: IconProps["name"]; color: string }[] = [
    { label: method === "otp" ? copy.reassurance.fastCode : securityMessage, icon: "time-outline", color: fuvay.accents.a2 },
    { label: copy.reassurance.privateNumber, icon: "shield-checkmark-outline", color: fuvay.accents.a3 },
    { label: copy.reassurance.flexibleBooking, icon: "calendar-outline", color: fuvay.accents.a1 },
  ];

  return (
    <AppScreen scroll contentContainerStyle={{ padding: 0, flexGrow: 1 }}>
      <FuvayAmbientCanvas>

        {/* ── Header ─────────────────────────────────────────────────── */}
        <View style={{ paddingHorizontal: 26, paddingTop: compact ? 40 : 52, paddingBottom: 30, gap: 20 }}>
          <FuvayEyebrow color={fuvay.accents.a2}>{copy.eyebrow}</FuvayEyebrow>
          <View style={{ gap: 10 }}>
            <AppText variant="displayLarge" accessibilityRole="header">
              {copy.title}
            </AppText>
            <AppText variant="body" color="secondary" style={{ maxWidth: 270 }}>
              {method === "otp" ? copy.otpDescription : copy.passwordDescription}
            </AppText>
          </View>
        </View>

        {/* ── Panel ──────────────────────────────────────────────────── */}
        <FuvayPanel
          style={{
            flex: 1,
            marginHorizontal: theme.metrics.screen.authHorizontalInset,
            paddingHorizontal: theme.metrics.panel.horizontalPadding,
            paddingTop: theme.metrics.panel.verticalPadding,
            paddingBottom: theme.spacing.xl,
            borderTopLeftRadius: 28,
            borderTopRightRadius: 28,
            borderBottomLeftRadius: theme.radius.radiusShell,
            borderBottomRightRadius: theme.radius.radiusShell,
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
                {copy.newCustomer}
              </AppText>
              <AppButton label={copy.createAccount} tone="secondary" size="compact" onPress={onSignup} />
            </View>
            <LegalLinksFooter />
          </View>
        </FuvayPanel>
      </FuvayAmbientCanvas>
    </AppScreen>
  );
}
