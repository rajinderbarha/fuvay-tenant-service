import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

export interface AssurancePoint {
  key: string;
  label: string;
  /** The substantiation. Every one of these must describe something the
   * platform genuinely does -- see ASSURANCE_POINTS below. */
  detail: string;
  icon: IconProps["name"];
}

export interface AssuranceSectionProps {
  title?: string | null;
  points?: readonly AssurancePoint[];
}

/**
 * What the customer is actually promised, as one quiet card at the foot of Home.
 *
 * Replaces three big bordered tiles that each held a 44px icon and two words.
 * They took a third of the screen to say "Verified Expert" and, because the
 * claims had nothing under them, read as decoration rather than assurance --
 * which is the opposite of what a trust section is for.
 *
 * The new shape does two things differently. It is ONE surface with three rows
 * rather than three competing cards, so it reads as a short list rather than a
 * grid of empty boxes. And every claim now carries the sentence that makes it
 * checkable: a customer who reads "you approve the cost before any work starts"
 * can verify that on the next screen, whereas "Transparent Pricing" alone is a
 * slogan.
 *
 * Deliberately last on the screen and deliberately low-contrast: reassurance is
 * what someone reads while deciding, not what they came for.
 */
export const ASSURANCE_POINTS: readonly AssurancePoint[] = [
  {
    key: "verified",
    label: "Checked providers",
    // True: tenants carry a verification_status, and the customer-facing
    // "Verified Business" badge is only awarded once it is approved.
    detail: "Business details are verified before a provider can take work.",
    icon: "shield-checkmark-outline",
  },
  {
    key: "pricing",
    label: "You approve the cost",
    // True: the review screen shows the visit fee and states that it is
    // credited against the work if the customer continues; parts and estimates
    // both need explicit customer approval.
    detail: "Visit fee shown up front and credited against the work. Parts need your yes.",
    icon: "receipt-outline",
  },
  {
    key: "privacy",
    label: "Your number stays private",
    // True: masked calling bridges through the platform, and the provider is
    // never shown the customer's real number.
    detail: "Calls go through Fuvay, so neither side sees the other's number.",
    icon: "call-outline",
  },
];

export function AssuranceSection({ title, points = ASSURANCE_POINTS }: AssuranceSectionProps) {
  const { theme } = useTheme();

  return (
    <View>
      <AppText variant="headingSmall" style={{ marginBottom: theme.spacing.sm }}>
        {title || "What you're promised"}
      </AppText>
      <View
        style={{
          borderRadius: theme.radiusUsage.card,
          backgroundColor: theme.colors.surfaceDefault,
          borderWidth: 1, borderColor: theme.colors.borderSubtle,
          overflow: "hidden",
        }}
      >
        {points.map((point, index) => (
          <View
            key={point.key}
            style={{
              flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm,
              paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
              // Hairlines between rows, not borders around each: one surface,
              // three items.
              borderTopWidth: index === 0 ? 0 : 1,
              borderTopColor: theme.colors.borderSubtle,
            }}
          >
            <View
              style={{
                width: 32, height: 32, borderRadius: theme.radiusUsage.input,
                alignItems: "center", justifyContent: "center", flexShrink: 0,
                backgroundColor: theme.colors.surfaceInteractive,
              }}
            >
              <Icon name={point.icon} size="compact" color={theme.colors.brandPrimaryStrong} decorative />
            </View>
            <View style={{ flex: 1, minWidth: 0, gap: 1 }}>
              <AppText variant="bodyStrong">{point.label}</AppText>
              <AppText variant="caption" color="secondary">{point.detail}</AppText>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}
