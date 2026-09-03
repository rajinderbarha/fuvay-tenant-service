import React, { useState } from "react";
import { View, Linking, Platform } from "react-native";
import Constants from "expo-constants";
import { useTheme } from "../../design-system/themes";
import { EmptyState } from "../../design-system/components/feedback/States";
import { Caption } from "../../design-system/components/typography/Label";
import { AppText } from "../../design-system/components/typography/AppText";
import { Card, Inline, Section } from "../../design-system/components/foundation/Layout";
import { KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { IconProps } from "../../design-system/components/Icon";
import { PrimaryButton, SecondaryButton, TertiaryButton } from "../../design-system/components/actions/Buttons";
import { RestrictedRouteName, ReasonCode } from "../guards/types";
import { useSession } from "../session/SessionProvider";
import { checkPublicHealth } from "../../services/api/healthApi";

const CURRENT_APP_VERSION = Constants.expoConfig?.version ?? "0.0.0";
const CURRENT_BUILD = String(Constants.expoConfig?.android?.versionCode ?? Constants.expoConfig?.ios?.buildNumber ?? "1");
const ANDROID_PACKAGE = Constants.expoConfig?.android?.package;
const IOS_BUNDLE_ID = Constants.expoConfig?.ios?.bundleIdentifier;

interface StateContent {
  icon: IconProps["name"];
  title: string;
  message: string;
  showRetry: boolean;
  showSignOut: boolean;
}

const CONTENT: Record<RestrictedRouteName, StateContent> = {
  AccountPending: {
    icon: "hourglass-outline",
    title: "Account pending approval",
    message: "Your technician account is waiting on approval. You'll be notified once it's ready.",
    showRetry: true, showSignOut: true,
  },
  AccountSuspended: {
    icon: "lock-closed-outline",
    title: "Work access suspended",
    message: "Your account access has been suspended. Contact your business admin for details.",
    showRetry: true, showSignOut: true,
  },
  TenantSuspended: {
    icon: "business-outline",
    title: "Work access suspended",
    message: "Your business's Fuvay workspace is currently suspended.",
    showRetry: true, showSignOut: true,
  },
  TechnicianInactive: {
    icon: "person-remove-outline",
    title: "Work access suspended",
    message: "Your technician profile is currently inactive. Contact your business admin.",
    showRetry: true, showSignOut: true,
  },
  AccessDenied: {
    icon: "shield-outline",
    title: "Access denied",
    message: "Your account doesn't have access to the technician app.",
    showRetry: false, showSignOut: true,
  },
  AppUpdateRequired: {
    icon: "cloud-download-outline",
    title: "Update required",
    message: "Install the latest Fuvay Staff version to keep your account and job data secure.",
    showRetry: false, showSignOut: false,
  },
  ServiceUnavailable: {
    icon: "construct-outline",
    title: "We'll be back shortly",
    message: "Fuvay is temporarily unavailable. Please check again shortly.",
    showRetry: true, showSignOut: false,
  },
};

const SUSPENDED_SCREENS = new Set<RestrictedRouteName>(["AccountSuspended", "TenantSuspended", "TechnicianInactive"]);

function openStoreListing() {
  const url = Platform.OS === "android" && ANDROID_PACKAGE
    ? `https://play.google.com/store/apps/details?id=${ANDROID_PACKAGE}`
    : Platform.OS === "ios" && IOS_BUNDLE_ID
      ? `https://apps.apple.com/app/${IOS_BUNDLE_ID}`
      : null;
  if (url) Linking.openURL(url);
}

export interface RestrictedStateScreenProps {
  screen: RestrictedRouteName;
  reasonCode: ReasonCode;
}

/**
 * Shared presentation for every RestrictedStateStack screen (Phase E/G),
 * extended for the final certification pass to surface REAL data instead
 * of only generic copy: the actual current/required app version for
 * Update Required (from AccessContext.minimumSupportedAppVersion, backend-
 * authoritative, never guessed), a real public-health probe for Service
 * Unavailable (never a fabricated restoration time), and the real
 * tenant/technician status + enabled verticals for suspended states. No
 * business NAME is shown anywhere here because no endpoint provides one to
 * an already-restricted caller -- inventing one would be fabricated data,
 * which is exactly what this phase's audit was scoped to eliminate.
 */
export function RestrictedStateScreen({ screen, reasonCode }: RestrictedStateScreenProps) {
  const { theme } = useTheme();
  const { retryBootstrap, invalidateSession, accessContext } = useSession();
  const [retrying, setRetrying] = useState(false);
  const [healthMessage, setHealthMessage] = useState<string | null>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);
  const content = CONTENT[screen];

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await retryBootstrap();
    } finally {
      setRetrying(false);
    }
  };

  const handleCheckStatus = async () => {
    setCheckingHealth(true);
    try {
      const result = await checkPublicHealth();
      setHealthMessage(
        result === "online" ? "All systems operational."
        : result === "limited" ? "Fuvay is degraded but reachable."
        : "Fuvay is still unreachable.",
      );
    } finally {
      setCheckingHealth(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary, justifyContent: "center", padding: theme.spacing.lg }}>
      <EmptyState icon={content.icon} title={content.title} message={content.message} />

      {screen === "AppUpdateRequired" && accessContext.minimumSupportedAppVersion ? (
        <Section spacing="base">
          <Card>
            <Inline justify="space-between">
              <View style={{ alignItems: "center", flex: 1 }}>
                <AppText variant="caption" color="tertiary">Current</AppText>
                <AppText variant="bodyStrong">{CURRENT_APP_VERSION} ({CURRENT_BUILD})</AppText>
              </View>
              <View style={{ alignItems: "center", flex: 1 }}>
                <AppText variant="caption" color="tertiary">Required</AppText>
                <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimary }}>{accessContext.minimumSupportedAppVersion}</AppText>
              </View>
            </Inline>
          </Card>
        </Section>
      ) : null}

      {SUSPENDED_SCREENS.has(screen) ? (
        <Section spacing="base">
          <Card>
            <KeyValueList items={[
              ...(accessContext.enabledVerticals?.length ? [{ label: "Vertical", value: accessContext.enabledVerticals.join(", ") }] : []),
              { label: "Status", value: screen === "TenantSuspended" ? (accessContext.tenantStatus ?? "suspended") : (accessContext.technicianStatus ?? "suspended") },
            ]} />
          </Card>
        </Section>
      ) : null}

      {healthMessage ? (
        <Section spacing="base">
          <AppText color="secondary" align="center">{healthMessage}</AppText>
        </Section>
      ) : null}

      <View style={{ alignItems: "center", marginTop: theme.spacing.base, gap: theme.spacing.sm }}>
        {screen === "AppUpdateRequired" ? (
          <PrimaryButton label="Update app" onPress={openStoreListing} fullWidth />
        ) : null}
        {content.showRetry ? (
          <SecondaryButton
            label={screen === "ServiceUnavailable" ? "Check again" : "Retry"}
            onPress={handleRetry}
            loading={retrying}
            fullWidth={screen === "ServiceUnavailable"}
          />
        ) : null}
        {screen === "ServiceUnavailable" ? (
          <TertiaryButton label="View service status" onPress={handleCheckStatus} loading={checkingHealth} />
        ) : null}
        {content.showSignOut ? <TertiaryButton label="Sign out" onPress={() => invalidateSession()} /> : null}
      </View>

      <View style={{ alignItems: "center", marginTop: theme.spacing.sm, gap: 2 }}>
        {screen === "AppUpdateRequired" ? <Caption color="tertiary">Your saved drafts will remain on this device.</Caption> : null}
        {screen === "ServiceUnavailable" ? <Caption color="tertiary">Do not repeat job actions until connection is restored.</Caption> : null}
        {/* No real "contact manager" destination is reachable from a
         * restricted/suspended session (Phase S's employment-details
         * lookup requires an active technician session) -- plain text
         * rather than a fake button, per this phase's dead-button sweep. */}
        {SUSPENDED_SCREENS.has(screen) ? <Caption color="tertiary">Contact your manager through your usual business channel.</Caption> : null}
        <Caption color="tertiary">Reason code: {reasonCode}</Caption>
      </View>
    </View>
  );
}
