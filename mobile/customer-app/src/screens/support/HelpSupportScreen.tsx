import React from "react";
import { View, Pressable } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppButton } from "../../components/AppButton";
import { Icon, IconProps } from "../../components/Icon";
import { CustomerTabsParamList } from "../../navigation/routeTypes";

type TabNav = BottomTabNavigationProp<CustomerTabsParamList>;
/** Root tab screens reach stack-only destinations the same way
 * `MyBookingsScreen` already does (no typed cross-navigator prop exists
 * for a bottom-tab screen reaching a parent-stack route in this app). */
type StackEscape = { navigate: (name: string, params?: unknown) => void };

interface HelpCategory {
  icon: IconProps["name"];
  title: string;
  subtitle: string;
  onPress: () => void;
}

/**
 * Root Help & Support tab (spec CUSTOMER-L5-20). Capability audit found
 * NO customer-facing help-center/FAQ/knowledge-search backend, so no
 * search field and no "Popular help" section are rendered here (spec
 * sections 4/10's explicit instruction to omit rather than fabricate).
 * Every visible entry resolves to a real, ownership-enforced backend
 * capability: the complaint engine (`/v1/customer/complaints`, this
 * app's real "support request" system) or an existing real screen
 * (Account Security, Privacy & Data, My Bookings).
 */
export function HelpSupportScreen() {
  const { theme } = useTheme();
  const tabNavigation = useNavigation<TabNav>();
  const stackNavigation = useNavigation() as unknown as StackEscape;

  const categories: HelpCategory[] = [
    {
      icon: "calendar-outline", title: "Bookings & service",
      subtitle: "Manage bookings and services",
      onPress: () => tabNavigation.navigate("Bookings"),
    },
    {
      icon: "person-outline", title: "Account & security",
      subtitle: "Your account and sign-in help",
      onPress: () => stackNavigation.navigate("Security"),
    },
    {
      icon: "shield-checkmark-outline", title: "Safety & trust",
      subtitle: "Report a concern about a booking",
      onPress: () => stackNavigation.navigate("BookingSupportEntry", { mode: "safety" }),
    },
    {
      icon: "lock-closed-outline", title: "Privacy & data",
      subtitle: "Your privacy and data settings",
      onPress: () => stackNavigation.navigate("PrivacyData"),
    },
  ];

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View>
          <AppText variant="headingSmall" accessibilityRole="header">Help & Support</AppText>
          <AppText variant="bodySmall" color="secondary">Find answers or get the right help</AppText>
        </View>

        <AppCard style={{ gap: theme.spacing.sm }}>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
            <Icon name="calendar-outline" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
            <View style={{ flex: 1, gap: theme.spacing.xxs }}>
              <AppText variant="bodyStrong">Need help with a booking?</AppText>
              <AppText variant="bodySmall" color="secondary">Choose a booking to get relevant support.</AppText>
            </View>
          </View>
          <AppButton
            label="Choose booking" tone="primary"
            onPress={() => stackNavigation.navigate("BookingSupportEntry", { mode: "help" })}
          />
        </AppCard>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Browse help</AppText>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
            {categories.map(cat => (
              <Pressable
                key={cat.title}
                accessibilityRole="button" accessibilityLabel={`${cat.title}: ${cat.subtitle}`}
                onPress={cat.onPress}
                style={{ flexBasis: "47%", flexGrow: 1 }}
              >
                <AppCard style={{ gap: theme.spacing.xs }}>
                  <Icon name={cat.icon} size="standard" color={theme.colors.textSecondary} decorative />
                  <AppText variant="bodyStrong">{cat.title}</AppText>
                  <AppText variant="caption" color="secondary">{cat.subtitle}</AppText>
                </AppCard>
              </Pressable>
            ))}
          </View>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Your support</AppText>
          <AppCard style={{ gap: 0 }}>
            <SupportRow
              icon="chatbox-ellipses-outline" title="My support requests"
              subtitle="View updates and request history"
              onPress={() => stackNavigation.navigate("SupportRequests")}
            />
            <SupportRow
              icon="alert-circle-outline" title="Report a safety concern"
              subtitle="Tell us about a service-related issue" isLast
              onPress={() => stackNavigation.navigate("BookingSupportEntry", { mode: "safety" })}
            />
          </AppCard>
        </View>

        <AppCard style={{ gap: theme.spacing.sm, borderColor: theme.colors.brandPrimary, borderWidth: 1 }}>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "center" }}>
            <Icon name="headset-outline" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">Still need help?</AppText>
              <AppText variant="bodySmall" color="secondary">Send a secure support request.</AppText>
            </View>
            <AppButton
              label="Create request" tone="primary" size="compact"
              onPress={() => stackNavigation.navigate("CreateSupportRequest", { source: "help_hub" })}
            />
          </View>
        </AppCard>
      </View>
    </AppScreen>
  );
}

function SupportRow({ icon, title, subtitle, onPress, isLast }: {
  icon: IconProps["name"]; title: string; subtitle: string; onPress: () => void; isLast?: boolean;
}) {
  const { theme } = useTheme();
  return (
    <Pressable
      accessibilityRole="button" accessibilityLabel={`${title}: ${subtitle}`} onPress={onPress}
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.sm,
        borderTopWidth: isLast ? 0 : 0, borderBottomWidth: isLast ? 0 : 1, borderBottomColor: theme.colors.borderSubtle,
      }}
    >
      <Icon name={icon} size="standard" color={theme.colors.textSecondary} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">{title}</AppText>
        <AppText variant="bodySmall" color="secondary">{subtitle}</AppText>
      </View>
      <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
    </Pressable>
  );
}
