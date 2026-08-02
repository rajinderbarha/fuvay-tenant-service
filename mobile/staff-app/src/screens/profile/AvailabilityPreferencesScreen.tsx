import React from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { ScreenHeader } from "./components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "AvailabilityPreferences">;

/**
 * Availability Preferences (Phase R spec section 10). Deliberately a thin
 * link into the real Phase P schedule system -- no second availability
 * system. Cross-tab navigation mirrors the two-level getParent() pattern
 * already used from ScheduleScreen to reach JobExecutionStack.
 */
export function AvailabilityPreferencesScreen({ navigation }: Props) {
  const { theme } = useTheme();

  const openSchedule = () => {
    // Hands off to the real Schedule tab rather than reaching into its
    // nested stack -- the root navigator's typed params don't support a
    // cross-tab deep link into "ManageAvailability" directly.
    navigation.getParent()?.getParent()?.navigate("AppTabs");
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Availability preferences" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card>
            <AppText variant="bodyStrong">Working hours & time off</AppText>
            <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
              Your recurring working hours, live availability, blocked time and time-off requests all live in the Schedule tab -- open Schedule, then "Manage availability".
            </AppText>
          </Card>
        </Section>
        <PrimaryButton label="Go to Schedule" onPress={openSchedule} fullWidth />
      </ScrollView>
    </SafeAreaScreen>
  );
}
