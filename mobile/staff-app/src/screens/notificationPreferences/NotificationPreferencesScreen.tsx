import React, { useState } from "react";
import { View, ScrollView, Linking } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, ListRow } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { Switch } from "../../design-system/components/forms/Switch";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { QuietHoursSheet } from "./components/QuietHoursSheet";
import { useNotificationPreferences } from "./useNotificationPreferences";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { PreferenceEventDTO } from "../../services/notifications/preferencesTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "NotificationPreferences">;

const GROUP_LABEL: Record<string, string> = { jobs: "Work updates", schedule: "Work updates", account: "Account" };

function groupEvents(events: PreferenceEventDTO[]): { title: string; items: PreferenceEventDTO[] }[] {
  const order = ["Work updates", "Account"];
  const buckets = new Map<string, PreferenceEventDTO[]>();
  for (const e of events) {
    const title = GROUP_LABEL[e.event_group] ?? "Account";
    if (!buckets.has(title)) buckets.set(title, []);
    buckets.get(title)!.push(e);
  }
  return order.filter(title => buckets.has(title)).map(title => ({ title, items: buckets.get(title)! }));
}

/**
 * Notification Preferences (Phase U). Personal delivery preferences only --
 * never a template/recipient/provider-credential editor. Every toggle here
 * is backed by a real, already-registered event key with a confirmed
 * technician-facing producer (spec section 1: "Only show preferences
 * supported end to end").
 */
export function NotificationPreferencesScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const [quietHoursOpen, setQuietHoursOpen] = useState(false);

  const { data, isLoading, isError, error, refetch, saveStatus, saveError, versionConflict, toggleEvent, saveQuietHours } = useNotificationPreferences();

  if (isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Notification preferences" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={400} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Notification preferences" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load preferences" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  const groups = groupEvents(data.events);

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Notification preferences" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}>
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached preferences. Changes require a connection." /></View> : null}
        {versionConflict ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="warning" title="Notification policy changed" message="Your preferences were refreshed to the latest version." /></View> : null}

        <Section>
          <Card style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            <Icon name="notifications-outline" size="standard" color={theme.colors.brandPrimary} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">Stay updated</AppText>
              <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
                Choose how you receive non-critical work updates. Required safety and account alerts always stay on.
              </AppText>
            </View>
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Delivery" />
          <Card padding="base">
            <View style={{ paddingVertical: theme.spacing.sm }}>
              <AppText variant="body">Push notifications</AppText>
              <AppText variant="caption" color="tertiary">Receive alerts on this device</AppText>
              <View style={{ marginTop: theme.spacing.xs }}>
                <Switch label="" value={data.delivery.push.enabled} onChange={() => {}} disabled accessibilityLabel="Push notifications, managed automatically" />
              </View>
              <AppText variant="caption" color="tertiary">
                {data.delivery.push.enabled ? "This device is registered for push." : "Push isn't registered on this device yet -- open the app and allow notifications when prompted."}
              </AppText>
            </View>
            <ListRow title="In-app notifications" subtitle="Always available in Notifications" trailing={<LockedPill />} />
            <View style={{ paddingVertical: theme.spacing.sm, opacity: 0.5 }}>
              <AppText variant="body">Email summaries</AppText>
              <AppText variant="caption" color="tertiary">Not available yet</AppText>
            </View>
          </Card>
        </Section>

        {groups.map(g => (
          <Section key={g.title}>
            <SectionHeader title={g.title} />
            <Card padding="base">
              {g.items.map(item => (
                <View key={item.code} style={{ paddingVertical: theme.spacing.sm }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                    <View style={{ flex: 1 }}>
                      <AppText variant="body">{item.label}</AppText>
                      <AppText variant="caption" color="tertiary">{item.description}</AppText>
                    </View>
                    {item.mandatory ? (
                      <LockedPill />
                    ) : (
                      <Switch
                        label=""
                        value={item.push_enabled}
                        onChange={(v) => toggleEvent(item.code, v)}
                        disabled={offline}
                        accessibilityLabel={`${item.label}, ${item.push_enabled ? "on" : "off"}`}
                      />
                    )}
                  </View>
                </View>
              ))}
            </Card>
          </Section>
        ))}

        <Section>
          <SectionHeader title="Quiet hours" />
          <Card padding="base">
            <ListRow
              title="Quiet hours"
              subtitle={data.quiet_hours.enabled && data.quiet_hours.start_local_time ? `${data.quiet_hours.start_local_time} – ${data.quiet_hours.end_local_time}` : "Off"}
              onPress={() => setQuietHoursOpen(true)}
              trailing={<Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />}
            />
          </Card>
          <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.sm }}>
            Critical job and security alerts can bypass quiet hours.
          </AppText>
        </Section>

        <Section>
          {saveStatus === "saving" ? (
            <AppText variant="caption" color="tertiary">Saving…</AppText>
          ) : saveStatus === "saved" ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
              <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
              <AppText variant="caption" color="success">Preferences saved automatically</AppText>
            </View>
          ) : saveStatus === "error" ? (
            <AppText variant="caption" color="danger">Couldn't save: {saveError?.safeMessage ?? "Please try again."}</AppText>
          ) : null}
        </Section>
      </ScrollView>

      <QuietHoursSheet
        visible={quietHoursOpen}
        onClose={() => setQuietHoursOpen(false)}
        quietHours={data.quiet_hours}
        saving={saveStatus === "saving"}
        onSave={(enabled, start, end) => { saveQuietHours(enabled, start, end); setQuietHoursOpen(false); }}
      />
    </SafeAreaScreen>
  );
}

function LockedPill() {
  const { theme } = useTheme();
  return (
    <View accessibilityLabel="Required, cannot be turned off" style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
      <Icon name="lock-closed" size="compact" color={theme.colors.statusSuccess} decorative />
      <AppText variant="labelStrong" color="success">Required</AppText>
    </View>
  );
}
