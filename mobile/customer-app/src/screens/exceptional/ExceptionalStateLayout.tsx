import React from "react";
import { View, AccessibilityInfo } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton } from "../../components";
import { Icon, IconProps } from "../../components/Icon";
import { FuvayMark } from "../../components/FuvayMark";

export interface ExceptionalActionSpec {
  label: string;
  tone?: "primary" | "secondary";
  onPress: () => void;
}

export interface ExceptionalStateLayoutProps {
  icon: IconProps["name"];
  title: string;
  message: string;
  actions?: ExceptionalActionSpec[];
  /** Dark, near-black treatment matches the approved design for
   * session/security-sensitive states (session expired, invalid access);
   * light/warm-white matches informational states (maintenance, update). */
  tone?: "dark" | "light";
}

/** Shared full-screen layout for every exceptional/global state screen
 * (spec section 13). Title is announced first for screen readers -- see
 * accessibilityLiveRegion + the initial focus order this establishes. */
export function ExceptionalStateLayout({ icon, title, message, actions = [], tone = "light" }: ExceptionalStateLayoutProps) {
  const { theme } = useTheme();
  const isDarkTreatment = tone === "dark";
  const backgroundColor = isDarkTreatment ? theme.colors.backgroundSunken : theme.colors.backgroundPrimary;

  React.useEffect(() => {
    AccessibilityInfo.announceForAccessibility(title);
  }, [title]);

  return (
    <AppScreen style={{ backgroundColor, alignItems: "center", justifyContent: "center" }}>
      <View style={{ marginBottom: theme.spacing.xxl }}>
        <FuvayMark />
      </View>
      <View
        style={{
          width: 96,
          height: 96,
          borderRadius: theme.radius.radiusFull,
          borderWidth: 2,
          borderColor: theme.colors.brandPrimary,
          alignItems: "center",
          justifyContent: "center",
          marginBottom: theme.spacing.xl,
          backgroundColor: isDarkTreatment ? theme.colors.brandPrimaryMuted : "transparent",
        }}
      >
        <Icon name={icon} size="feature" color={theme.colors.brandPrimaryStrong} decorative />
      </View>
      <AppText
        variant="headingLarge"
        align="center"
        accessibilityRole="header"
        color={isDarkTreatment ? "inverse" : "primary"}
        style={{ marginBottom: theme.spacing.sm }}
      >
        {title}
      </AppText>
      <AppText
        variant="body"
        align="center"
        color={isDarkTreatment ? "secondary" : "secondary"}
        style={{ marginBottom: theme.spacing.xxl, maxWidth: 320 }}
      >
        {message}
      </AppText>
      {actions.length > 0 ? (
        <View style={{ width: "100%", maxWidth: 360, gap: theme.spacing.sm }}>
          {actions.map(action => (
            <AppButton key={action.label} label={action.label} tone={action.tone ?? "secondary"} onPress={action.onPress} fullWidth />
          ))}
        </View>
      ) : null}
    </AppScreen>
  );
}
