import React from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "VoluntaryDataExport">;

/**
 * Voluntary Data Export (Phase X spec section 14). Explicitly labeled
 * "Voluntary ServiceOS data export" -- never framed as a statutory
 * portability right (spec section 8), since the backend-approved policy
 * doesn't make that claim. Submission only creates the request; the
 * backend runs discovery, approval and export generation asynchronously
 * (never generated on-device, spec section 14).
 */
export function VoluntaryDataExportScreen({ navigation }: Props) {
  const { theme } = useTheme();
  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Download my data" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card>
            <AppText variant="bodyStrong">Voluntary ServiceOS data export</AppText>
            <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
              Request a downloadable copy of supported ServiceOS account information. Your request will be reviewed, and once approved, an export is generated and made available through a short-lived, authorized download link.
            </AppText>
          </Card>
        </Section>
        <PrimaryButton
          label="Request export"
          onPress={() => navigation.navigate("PrivacyRequestForm", { requestType: "staff_data_export" })}
          fullWidth
        />
      </ScrollView>
    </SafeAreaScreen>
  );
}
