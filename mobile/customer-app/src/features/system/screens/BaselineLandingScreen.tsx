import React from "react";
import { useNavigation } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppCard } from "../../../components/primitives/AppCard";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useStartup } from "../../../app/startup/use-startup";
import { useConnectivity } from "../../../hooks/useConnectivity";
import { appConfig } from "../../../config/app-config";
import { environment } from "../../../config/environment";
import { useAuthSession } from "../../auth/hooks/use-auth-session";
import { useLogout } from "../../auth/hooks/use-logout";

/**
 * Temporary, non-business screen proving startup + navigation succeeded.
 * This is NOT the customer Home screen — later sprints replace this route's
 * destination once real discovery/home content exists.
 */
export function BaselineLandingScreen() {
  const { mode } = useAppTheme();
  const { i18n } = useTranslation();
  const { snapshot } = useStartup();
  const { status: connectivity } = useConnectivity();
  const { status: authStatus, session } = useAuthSession();
  const { logout, loading: loggingOut } = useLogout();
  const navigation = useNavigation<any>();

  return (
    <ScreenContainer>
      <Stack gap={6}>
        <AppText variant="displayMedium">{appConfig.appName}</AppText>
        <AppText variant="bodyMedium" color="textSecondary">
          Startup and navigation succeeded. This is a temporary system baseline screen — not the customer Home screen.
        </AppText>

        <AppCard variant="outlined">
          <Stack gap={2}>
            <AppText variant="labelMedium" color="textSecondary">
              Theme: {mode}
            </AppText>
            <AppText variant="labelMedium" color="textSecondary">
              Locale: {i18n.language}
            </AppText>
            <AppText variant="labelMedium" color="textSecondary">
              Connectivity: {connectivity}
            </AppText>
            {__DEV__ ? (
              <>
                <AppText variant="labelMedium" color="textSecondary">
                  Environment: {environment.name}
                </AppText>
                <AppText variant="labelMedium" color="textSecondary">
                  Config version: {snapshot.resolvedConfig?.config.configVersion ?? "n/a"}
                </AppText>
                <AppText variant="labelMedium" color="textSecondary">
                  Config source: {snapshot.resolvedConfig?.source ?? "n/a"}
                </AppText>
              </>
            ) : null}
          </Stack>
        </AppCard>

        <AppCard variant="outlined">
          {authStatus === "authenticated" && session ? (
            <Stack gap={3}>
              <AppText variant="titleMedium">Signed in as {session.fullName}</AppText>
              <AppButton label="View profile" onPress={() => navigation.navigate("Profile")} variant="secondary" size="medium" />
              <AppButton label="Sign out" onPress={logout} variant="text" size="medium" loading={loggingOut} />
            </Stack>
          ) : (
            <Stack gap={3}>
              <AppText variant="titleMedium">You're browsing as a guest</AppText>
              <AppButton label="Sign in" onPress={() => navigation.navigate("Authentication")} variant="primary" size="medium" />
            </Stack>
          )}
        </AppCard>

        {__DEV__ ? (
          <Stack gap={3}>
            <AppButton label="🧪 Design System Showcase (dev)" variant="secondary" size="medium" onPress={() => navigation.navigate("DesignSystemShowcase")} />
            <AppButton label="🔧 Startup Inspector (dev)" variant="secondary" size="medium" onPress={() => navigation.navigate("StartupInspector")} />
          </Stack>
        ) : null}
      </Stack>
    </ScreenContainer>
  );
}
