import React, { useState } from "react";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { Section } from "../../../components/layout/Section";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { useStartup } from "../../../app/startup/use-startup";
import { buildStartupDiagnostics } from "../../../app/startup/startup-diagnostics";
import { refreshRemoteConfig, clearConfigCache } from "../../../remote-config";
import { setStartupDevOverride, resetStartupDevOverrides } from "../../../app/startup/startup-dev-overrides";
import { toastService } from "../../../components/feedback/toast-service";

/**
 * Development-only. Never mounted in production — see RootNavigator.tsx,
 * which registers this route only inside a `__DEV__` guard.
 */
export function StartupInspectorScreen() {
  const { snapshot, retry } = useStartup();
  const [busy, setBusy] = useState(false);
  const diagnostics = buildStartupDiagnostics(snapshot);

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScreenContainer>
      <Stack gap={7}>
        <AppText variant="displayMedium">Startup Inspector</AppText>

        <Section title="Snapshot">
          <AppText variant="bodySmall" color="textSecondary">
            {JSON.stringify(diagnostics, null, 2)}
          </AppText>
        </Section>

        <Section title="Phase history">
          <Stack gap={2}>
            {diagnostics.phaseDurationsMs.map((entry) => (
              <AppText key={entry.phase} variant="bodySmall" color="textSecondary">
                {entry.phase}: {entry.durationMs ?? "…"}ms {entry.result ? `(${entry.result})` : ""}
              </AppText>
            ))}
          </Stack>
        </Section>

        <Section title="Actions">
          <Stack gap={3}>
            <AppButton
              label="Refresh config"
              onPress={() =>
                withBusy(() =>
                  refreshRemoteConfig({ force: true }).then(() => {
                    toastService.success("Config refreshed");
                  })
                )
              }
              variant="secondary"
              size="medium"
              loading={busy}
            />
            <AppButton
              label="Clear config cache"
              onPress={() =>
                withBusy(() =>
                  clearConfigCache().then(() => {
                    toastService.info("Cache cleared");
                  })
                )
              }
              variant="secondary"
              size="medium"
            />
            <AppButton label="Retry startup" onPress={retry} variant="secondary" size="medium" />
          </Stack>
        </Section>

        <Section title="Simulations (dev-only)">
          <Stack gap={3}>
            <AppButton
              label="Simulate offline config failure"
              onPress={() => {
                setStartupDevOverride("forceOffline", true);
                retry();
              }}
              variant="text"
              size="small"
            />
            <AppButton
              label="Simulate mandatory update"
              onPress={() => {
                setStartupDevOverride("forceMandatoryUpdate", true);
                retry();
              }}
              variant="text"
              size="small"
            />
            <AppButton
              label="Simulate maintenance"
              onPress={() => {
                setStartupDevOverride("forceMaintenance", true);
                retry();
              }}
              variant="text"
              size="small"
            />
            <AppButton
              label="Simulate invalid deep link"
              onPress={() => {
                setStartupDevOverride("forceInvalidDeepLink", true);
                retry();
              }}
              variant="text"
              size="small"
            />
            <AppButton
              label="Reset simulations"
              onPress={() => {
                resetStartupDevOverrides();
                retry();
              }}
              variant="destructive"
              size="small"
            />
          </Stack>
        </Section>
      </Stack>
    </ScreenContainer>
  );
}
