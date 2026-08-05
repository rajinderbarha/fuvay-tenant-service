import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

interface Step {
  key: string;
  title: string;
  body: string;
  icon: IconProps["name"];
}

/**
 * Static explanatory copy, not backend data.
 *
 * Every step describes something this product ACTUALLY does, which is the
 * whole point of the section -- the two things that most differentiate this
 * booking flow are that a real capacity-checked slot is shown BEFORE the
 * customer commits, and that a provider is assigned immediately rather than
 * the customer waiting on a callback. Both are stated plainly here because
 * a first-time customer has no way to know that from the booking screen.
 *
 * Deliberately does not promise anything the platform cannot honour: it
 * says the visit fee is adjusted if the service goes ahead (which the
 * booking review already discloses), and makes no claim about arrival
 * times beyond the slot the customer is actually shown.
 */
const STEPS: Step[] = [
  {
    key: "describe",
    title: "Tell us what's wrong",
    body: "Answer a few quick questions, or just describe the problem in your own words. Add a photo if it helps.",
    icon: "chatbubble-ellipses-outline",
  },
  {
    key: "price",
    title: "See the price and the time slot",
    body: "You get a clear price and the actual slot your provider has room for — before you confirm anything.",
    icon: "pricetag-outline",
  },
  {
    key: "assign",
    title: "A verified provider is assigned",
    body: "No waiting for a callback. Your request goes straight to a provider who covers your area.",
    icon: "shield-checkmark-outline",
  },
  {
    key: "done",
    title: "Job done, then you pay",
    body: "Track progress, pay after the work is finished, and rate your experience. The visit fee is adjusted if the service goes ahead.",
    icon: "checkmark-done-outline",
  },
];

/** Explains the booking flow to a first-time customer. */
export function HowItWorksSection() {
  const { theme } = useTheme();

  return (
    <View accessibilityRole="summary" accessibilityLabel="How booking works">
      <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>
        How it works
      </AppText>

      <View
        style={{
          borderRadius: theme.radiusUsage.card,
          backgroundColor: theme.colors.surfaceDefault,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          paddingVertical: theme.spacing.xs,
        }}
      >
        {STEPS.map((step, index) => (
          <View
            key={step.key}
            style={{
              flexDirection: "row",
              gap: theme.spacing.sm,
              paddingHorizontal: theme.spacing.base,
              paddingVertical: theme.spacing.sm,
              borderTopWidth: index === 0 ? 0 : 1,
              borderTopColor: theme.colors.borderSubtle,
            }}
          >
            <View
              style={{
                width: 34, height: 34, borderRadius: 17,
                alignItems: "center", justifyContent: "center", flexShrink: 0,
                backgroundColor: theme.colors.brandPrimaryMuted,
              }}
            >
              <Icon name={step.icon} size="compact" color={theme.colors.brandPrimaryStrong} decorative />
            </View>

            <View style={{ flex: 1, minWidth: 0 }}>
              <AppText variant="labelStrong">
                {`${index + 1}. ${step.title}`}
              </AppText>
              <AppText
                variant="bodySmall"
                color="secondary"
                style={{ marginTop: theme.spacing.xxs }}
              >
                {step.body}
              </AppText>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}
