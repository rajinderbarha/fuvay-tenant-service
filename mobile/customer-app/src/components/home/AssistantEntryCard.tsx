import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface AssistantEntryCardProps {
  onPress: () => void;
}

/** The three things the assistant actually does, in the customer's words. Kept
 * to three: a longer list turns a prompt into a feature tour. */
const WHAT_IT_DOES = [
  { key: "describe", icon: "chatbubble-ellipses-outline" as const, label: "Describe it in your words" },
  { key: "price", icon: "pricetag-outline" as const, label: "See the price first" },
  { key: "slot", icon: "time-outline" as const, label: "Pick a real slot" },
] as const;

/**
 * The way in for someone who cannot name their problem.
 *
 * REBUILT. The old card was a cramped row of four competing elements -- an
 * avatar, three stacked lines of text at three sizes, and a pill button -- inside
 * a flat brand-tinted box. Nothing led, the "Guided by available services" line
 * was internal wording that meant nothing to a customer, and the pill looked
 * like a button while the whole card was also tappable.
 *
 * Now it leads with the question, answers it in one line, and shows the three
 * things that actually happen next. One tap target, one primary action, and no
 * claim beyond what the flow does: it never mentions the model behind it, never
 * promises diagnosis from a photo, and starts no booking here -- this is a
 * navigation affordance.
 */
export function AssistantEntryCard({ onPress }: AssistantEntryCardProps) {
  const { theme } = useTheme();

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel="Not sure what to book? Describe the problem and Fuvay Assistant takes it from there."
      style={({ pressed }) => ({
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1, borderColor: theme.colors.brandPrimaryMuted,
        overflow: "hidden",
        opacity: pressed ? 0.9 : 1,
      })}
    >
      <View style={{ padding: theme.spacing.base, gap: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <View
            style={{
              width: 36, height: 36, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.brandPrimary,
              alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Icon name="sparkles" size="standard" color={theme.colors.brandOnPrimary} decorative />
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
            <AppText variant="bodyStrong">Not sure what to book?</AppText>
            <AppText variant="bodySmall" color="secondary" numberOfLines={2}>
              Describe the problem — we'll work out the service.
            </AppText>
          </View>
          {/* Chevron, not a pill: the whole card is the target, and a button
              inside a button invites two different taps for one action. */}
          <Icon name="chevron-forward" size="standard" color={theme.colors.brandPrimary} decorative />
        </View>

        <View
          style={{
            flexDirection: "row", gap: theme.spacing.sm,
            paddingTop: theme.spacing.sm,
            borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle,
          }}
        >
          {WHAT_IT_DOES.map(item => (
            <View key={item.key} style={{ flex: 1, alignItems: "center", gap: theme.spacing.xxs }}>
              <Icon name={item.icon} size="compact" color={theme.colors.brandPrimaryStrong} decorative />
              <AppText variant="caption" color="secondary" align="center" numberOfLines={2}>
                {item.label}
              </AppText>
            </View>
          ))}
        </View>
      </View>
    </Pressable>
  );
}
