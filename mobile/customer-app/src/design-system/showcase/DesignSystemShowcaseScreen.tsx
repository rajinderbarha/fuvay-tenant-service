import React, { useState } from "react";
import { View } from "react-native";
import { ScreenContainer } from "../../components/layout/ScreenContainer";
import { Section } from "../../components/layout/Section";
import { Stack } from "../../components/layout/Stack";
import { Inline } from "../../components/layout/Inline";
import { AppText } from "../../components/primitives/AppText";
import { AppButton } from "../../components/primitives/AppButton";
import { AppIconButton } from "../../components/primitives/AppIconButton";
import { AppCard } from "../../components/primitives/AppCard";
import { AppBadge } from "../../components/primitives/AppBadge";
import { AppAvatar } from "../../components/primitives/AppAvatar";
import { AppDivider } from "../../components/primitives/AppDivider";
import { AppTextField } from "../../components/forms/AppTextField";
import { AppTextArea } from "../../components/forms/AppTextArea";
import { AppCheckbox } from "../../components/forms/AppCheckbox";
import { AppRadio } from "../../components/forms/AppRadio";
import { AppSwitch } from "../../components/forms/AppSwitch";
import { LoadingIndicator } from "../../components/feedback/LoadingIndicator";
import { Skeleton } from "../../components/feedback/Skeleton";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { ConfirmationModal } from "../../components/feedback/ConfirmationModal";
import { BottomSheet } from "../../components/feedback/BottomSheet";
import { toastService } from "../../components/feedback/toast-service";
import { useAppTheme } from "../themes/use-app-theme";
import { typography, type TypographyVariant } from "../tokens/typography";
import type { ThemePreference } from "../themes/theme-types";

const TYPOGRAPHY_VARIANTS = Object.keys(typography) as TypographyVariant[];

/**
 * Development-only screen. Never register this in a production navigator
 * without the __DEV__ guard applied at the call site (see AppNavigator.tsx).
 * Not a product screen — demonstrates tokens/components only.
 */
export function DesignSystemShowcaseScreen() {
  const { theme, preference, setPreference } = useAppTheme();
  const [checked, setChecked] = useState(false);
  const [radioValue, setRadioValue] = useState("a");
  const [switchOn, setSwitchOn] = useState(true);
  const [text, setText] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [showSheet, setShowSheet] = useState(false);

  const colorGroups: [string, string[]][] = [
    ["Backgrounds", ["backgroundPrimary", "backgroundSecondary", "backgroundTertiary", "backgroundElevated"]],
    ["Surfaces", ["surfacePrimary", "surfaceSecondary", "surfaceSelected", "surfacePressed"]],
    ["Text", ["textPrimary", "textSecondary", "textTertiary", "textLink"]],
    ["Status", ["statusSuccessBackground", "statusWarningBackground", "statusDangerBackground", "statusInfoBackground"]],
  ];

  return (
    <ScreenContainer>
      <Stack gap={7}>
        <View>
          <AppText variant="displayMedium">Design System Showcase</AppText>
          <AppText variant="bodyMedium" color="textSecondary">
            Internal, development-only. Not a product screen.
          </AppText>
        </View>

        <Section title="Theme">
          <Inline gap={3} wrap>
            {(["light", "dark", "system"] as ThemePreference[]).map((mode) => (
              <AppButton key={mode} label={mode} variant={preference === mode ? "primary" : "secondary"} size="small" onPress={() => setPreference(mode)} />
            ))}
          </Inline>
        </Section>

        <Section title="Typography">
          <Stack gap={2}>
            {TYPOGRAPHY_VARIANTS.map((variant) => (
              <AppText key={variant} variant={variant}>
                {variant} — The quick brown fox
              </AppText>
            ))}
          </Stack>
        </Section>

        <Section title="Colors">
          <Stack gap={5}>
            {colorGroups.map(([label, keys]) => (
              <View key={label}>
                <AppText variant="titleSmall" color="textSecondary" style={{ marginBottom: theme.spacing[2] }}>
                  {label}
                </AppText>
                <Inline gap={3} wrap>
                  {keys.map((key) => (
                    <View key={key} style={{ alignItems: "center", gap: 4 }}>
                      <View
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: theme.radii.md,
                          backgroundColor: (theme.colors as unknown as Record<string, string>)[key],
                          borderWidth: 1,
                          borderColor: theme.colors.borderSubtle,
                        }}
                      />
                      <AppText variant="caption" color="textTertiary">
                        {key}
                      </AppText>
                    </View>
                  ))}
                </Inline>
              </View>
            ))}
          </Stack>
        </Section>

        <Section title="Buttons">
          <Stack gap={3}>
            <Inline gap={3} wrap>
              <AppButton label="Primary" onPress={() => {}} variant="primary" />
              <AppButton label="Secondary" onPress={() => {}} variant="secondary" />
              <AppButton label="Tertiary" onPress={() => {}} variant="tertiary" />
              <AppButton label="Destructive" onPress={() => {}} variant="destructive" />
              <AppButton label="Text" onPress={() => {}} variant="text" />
            </Inline>
            <Inline gap={3} wrap>
              <AppButton label="Loading" onPress={() => {}} loading />
              <AppButton label="Disabled" onPress={() => {}} disabled />
              <AppIconButton icon="star" accessibilityLabel="Favorite" onPress={() => {}} />
            </Inline>
          </Stack>
        </Section>

        <Section title="Cards, badges, avatars">
          <Stack gap={4}>
            <AppCard variant="elevated">
              <AppText variant="titleMedium">Elevated card</AppText>
            </AppCard>
            <AppCard variant="outlined">
              <AppText variant="titleMedium">Outlined card</AppText>
            </AppCard>
            <Inline gap={3} wrap>
              <AppBadge label="Neutral" tone="neutral" />
              <AppBadge label="Success" tone="success" />
              <AppBadge label="Warning" tone="warning" />
              <AppBadge label="Danger" tone="danger" />
              <AppBadge label="Info" tone="info" />
            </Inline>
            <Inline gap={3}>
              <AppAvatar accessibilityLabel="User avatar" initials="JD" />
              <AppAvatar accessibilityLabel="User avatar loading" loading />
              <AppAvatar accessibilityLabel="User avatar fallback" />
            </Inline>
          </Stack>
        </Section>

        <AppDivider />

        <Section title="Forms">
          <Stack gap={5}>
            <AppTextField label="Full name" value={text} onChangeText={setText} placeholder="Jane Doe" required />
            <AppTextField label="With error" value="" onChangeText={() => {}} errorText="This field is required" required />
            <AppTextArea label="Notes" value="" onChangeText={() => {}} placeholder="Add a note" />
            <AppCheckbox checked={checked} onChange={setChecked} label="I agree to the terms" />
            <Stack gap={2}>
              <AppRadio selected={radioValue === "a"} onSelect={() => setRadioValue("a")} label="Option A" groupLabel="example group" />
              <AppRadio selected={radioValue === "b"} onSelect={() => setRadioValue("b")} label="Option B" groupLabel="example group" />
            </Stack>
            <AppSwitch value={switchOn} onValueChange={setSwitchOn} label="Enable notifications" />
          </Stack>
        </Section>

        <AppDivider />

        <Section title="Feedback">
          <Stack gap={5}>
            <LoadingIndicator variant="inline" />
            <Stack gap={2}>
              <Skeleton height={16} width="80%" />
              <Skeleton height={16} width="60%" />
            </Stack>
            <EmptyState title="No results" description="Try a different search." icon="search" primaryAction={{ label: "Reset", onPress: () => {} }} />
            <ErrorState title="Couldn't load this" description="Something went wrong on our end." errorReferenceId="err_demo_123" onRetry={() => {}} />
            <Inline gap={3} wrap>
              <AppButton label="Show toast" onPress={() => toastService.success("Saved successfully")} variant="secondary" size="small" />
              <AppButton label="Show modal" onPress={() => setShowModal(true)} variant="secondary" size="small" />
              <AppButton label="Show sheet" onPress={() => setShowSheet(true)} variant="secondary" size="small" />
            </Inline>
          </Stack>
        </Section>
      </Stack>

      <ConfirmationModal
        visible={showModal}
        title="Confirm action"
        description="This is a shared confirmation modal."
        onConfirm={() => setShowModal(false)}
        onCancel={() => setShowModal(false)}
      />
      <BottomSheet visible={showSheet} onClose={() => setShowSheet(false)} accessibilityLabel="Example bottom sheet">
        <AppText variant="titleLarge">Bottom sheet</AppText>
        <AppText variant="bodyMedium" color="textSecondary">
          This is the shared bottom-sheet wrapper.
        </AppText>
      </BottomSheet>
    </ScreenContainer>
  );
}
