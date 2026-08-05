import React, { useState } from "react";
import { View, Alert } from "react-native";
import Constants from "expo-constants";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { AppText } from "../../components/AppText";
import { Icon } from "../../components/Icon";
import { ProfileHeader } from "../../components/profile/ProfileHeader";
import { CustomerIdentityCard } from "../../components/profile/CustomerIdentityCard";
import { ProfileSection } from "../../components/profile/ProfileSection";
import { ProfileRow } from "../../components/profile/ProfileRow";
import { AppearanceSelector } from "../../components/profile/AppearanceSelector";
import { LegalLinks } from "../../components/profile/LegalLinks";
import { SignOutCard } from "../../components/profile/SignOutCard";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useCustomerAddressesQuery } from "../../api/customerAddresses/useCustomerAddressesQuery";
import { formatSavedAddress } from "../../domain/formatAddress";
import { logout } from "../../api/session/sessionManager";
import { isOffline } from "../../api/networkState";

/**
 * Canonical root Profile tab. Every row is either a real capability
 * (confirmed route) or absent entirely -- no disabled placeholders (spec
 * section 14).
 */
export function ProfileScreen() {
  const { theme, preference, setPreference, mode } = useTheme();
  const navigation = useNavigation();
  const query = useCustomerProfileQuery();
  const { data: addresses } = useCustomerAddressesQuery();
  const [signingOut, setSigningOut] = useState(false);

  function cycleTheme() {
    const order: Array<typeof preference> = ["system", "light", "dark"];
    const next = order[(order.indexOf(preference) + 1) % order.length];
    setPreference(next);
  }

  function handleSignOut() {
    Alert.alert(
      "Sign out of Fuvay?",
      "You can sign in again anytime.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Sign out",
          style: "destructive",
          onPress: async () => {
            if (signingOut) return;
            setSigningOut(true);
            try {
              await logout();
              // RootNavigator's session-state watcher resets navigation to
              // the unauthenticated stack once state becomes
              // "unauthenticated" -- no manual reset needed here, and no
              // path back into authenticated screens exists once that
              // stack is mounted (spec section 12).
            } finally {
              setSigningOut(false);
            }
          },
        },
      ],
    );
  }

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your profile" />
      </AppScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your profile" actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  const profile = query.data;
  if (!profile) return null;

  const defaultAddress = addresses?.find(a => a.isDefault) ?? null;
  const appVersion = Constants.expoConfig?.version ?? "—";

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      {isOffline() ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.base }}>
        <ProfileHeader onToggleTheme={cycleTheme} themeIcon={mode === "dark" ? "moon-outline" : "sunny-outline"} />

        <CustomerIdentityCard
          profile={profile}
          onEditProfile={profile.capabilities.canEditProfile ? () => (navigation as { navigate: (n: string) => void }).navigate("EditProfile") : undefined}
        />

        <ProfileSection title="Account">
          <ProfileRow
            icon="person-outline"
            label="Personal details"
            subtitle="Name, mobile and email"
            onPress={() => (navigation as { navigate: (n: string) => void }).navigate("EditProfile")}
          />
          <ProfileRow
            icon="home-outline"
            label="Saved addresses"
            subtitle={defaultAddress ? `${defaultAddress.label ?? "Default"} · ${formatSavedAddress(defaultAddress)}` : "No saved addresses yet"}
            onPress={() => (navigation as { navigate: (n: string) => void }).navigate("SavedAddresses")}
          />
          {profile.capabilities.canChangePassword || profile.capabilities.canManageSessions ? (
            <ProfileRow
              icon="shield-checkmark-outline"
              label="Security"
              subtitle="Password and signed-in sessions"
              onPress={() => (navigation as { navigate: (n: string) => void }).navigate("Security")}
              bordered={false}
            />
          ) : null}
        </ProfileSection>

        <ProfileSection title="Preferences">
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.base, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
              <Icon name="sunny-outline" size="standard" color={theme.colors.textSecondary} decorative />
              <AppText variant="body">Appearance</AppText>
            </View>
            <AppearanceSelector selected={preference} onSelect={setPreference} />
          </View>
          <ProfileRow
            icon="chatbubble-ellipses-outline"
            label="Fuvay Assistant language"
            subtitle="Choose during each conversation · App interface remains in English"
            bordered={false}
          />
        </ProfileSection>

        <ProfileSection title="Privacy & legal">
          <ProfileRow
            icon="lock-closed-outline"
            label="Privacy & data"
            subtitle="Manage your information and privacy requests"
            onPress={() => (navigation as { navigate: (n: string) => void }).navigate("PrivacyData")}
            bordered={false}
          />
          <LegalLinks privacyPolicyUrl={null} termsOfServiceUrl={null} appVersion={appVersion} />
        </ProfileSection>

        <SignOutCard onSignOut={handleSignOut} signingOut={signingOut} />

        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, justifyContent: "center", paddingBottom: theme.spacing.base }}>
          <Icon name="shield-checkmark" size="compact" color={theme.colors.statusSuccess} decorative />
          <AppText variant="caption" color="tertiary">Your account information is protected</AppText>
        </View>
      </View>
    </AppScreen>
  );
}
