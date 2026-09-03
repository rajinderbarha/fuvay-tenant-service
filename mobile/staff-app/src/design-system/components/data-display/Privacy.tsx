import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Avatar } from "./Avatar";

export interface CustomerAliasProps {
  /** Already-safe alias/reference resolved by the backend (e.g. "Customer
   * HS-4F21"). This component NEVER accepts a raw phone/email/name prop --
   * that would defeat the entire point of it existing. */
  alias: string | null | undefined;
  showAvatar?: boolean;
}

/**
 * Renders a customer's safe alias. Never fetches customer profile details,
 * never accepts raw contact fields. Falls back to a generic "Customer"
 * label if no alias is available yet (e.g. still loading) rather than
 * showing nothing or a raw ID.
 */
export function CustomerAlias({ alias, showAvatar = false }: CustomerAliasProps) {
  const safeAlias = alias && alias.trim().length > 0 ? alias : "Customer";
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      {showAvatar ? <Avatar name={safeAlias} size={28} /> : null}
      <AppText variant="body" accessibilityLabel={`Customer: ${safeAlias}`}>{safeAlias}</AppText>
    </View>
  );
}

export interface MaskedIdentifierProps {
  /** An ALREADY-masked value from the backend (e.g. "+91 98••••••10").
   * This component renders it as-is -- it does not invent its own masking
   * policy or attempt to mask a raw value passed in by mistake. */
  maskedValue: string;
  label?: string;
}

export function MaskedIdentifier({ maskedValue, label }: MaskedIdentifierProps) {
  const { theme } = useTheme();
  return (
    <View>
      {label ? <AppText variant="caption" color="tertiary">{label}</AppText> : null}
      <AppText variant="bodySmall" style={{ fontVariant: ["tabular-nums"] }} color="secondary">{maskedValue}</AppText>
    </View>
  );
}

/** PrivacyNotice -- standard disclosure line used across job-scoped
 * customer-data surfaces. */
export function PrivacyNotice({ text }: { text?: string }) {
  const { theme } = useTheme();
  return (
    <AppText variant="caption" color="tertiary" style={{ fontStyle: "italic" }}>
      {text ?? "Customer contact is protected by Fuvay and available only during authorized job activity."}
    </AppText>
  );
}

/** JobScopedLocation -- shows only a generalized locality unless/until the
 * feature layer explicitly reveals the exact address through an authorized
 * action (Phase F: address-reveal service). */
export function JobScopedLocation({ localityLabel }: { localityLabel: string }) {
  return <AppText variant="bodySmall" color="secondary">{localityLabel}</AppText>;
}

/** SensitiveValue -- generic wrapper for a value that must never be logged
 * or included in telemetry; purely a visual/accessibility marker for now
 * (screenshot protection is a Phase F platform-service concern). */
export function SensitiveValue({ children }: { children: React.ReactNode }) {
  return <View accessibilityLabel="Sensitive information">{children}</View>;
}

/** RelayContactButton -- feature layer supplies the real relay action;
 * this is presentation only and never exposes a raw phone/email. */
export function RelayContactButton({ label = "Contact through Fuvay", onPress, disabled }: { label?: string; onPress: () => void; disabled?: boolean }) {
  const { theme } = useTheme();
  return (
    <AppText
      variant="bodyStrong"
      color={disabled ? "disabled" : "link"}
      onPress={disabled ? undefined : onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
    >
      {label}
    </AppText>
  );
}
