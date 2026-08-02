import React from "react";
import { ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "DataSummary">;

const GROUPS = [
  { title: "Identity", items: ["Profile", "Verified mobile/email", "Authentication and session records"] },
  { title: "Employment", items: ["Tenant relationship", "Role/designation", "Assigned services", "Documents and certifications"] },
  { title: "Operations", items: ["Assigned jobs", "Inspection evidence", "Estimates", "Parts and completion records"] },
  { title: "Finance", items: ["Direct-payment confirmation evidence", "Financial events linked to your actions"] },
  { title: "Support & governance", items: ["Complaints/disputes", "Notifications", "Consent history", "Security/audit activity"] },
];

/** Data Summary (Phase X spec section 7). A safe, high-level category list
 * -- deliberately not a live per-category record-count query in this pass
 * (would require aggregating across every engine listed; disclosed as a
 * scoped-down, honest version rather than fabricated counts). */
export function DataSummaryScreen({ navigation }: Props) {
  const { theme } = useTheme();
  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Data summary" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.base }}>
          A high-level view of the categories of information ServiceOS holds about you across every linked system.
        </AppText>
        {GROUPS.map(group => (
          <Section key={group.title}>
            <SectionHeader title={group.title} />
            <Card padding="base">
              {group.items.map(item => <AppText key={item} variant="bodySmall" style={{ marginBottom: 4 }}>• {item}</AppText>)}
            </Card>
          </Section>
        ))}
      </ScrollView>
    </SafeAreaScreen>
  );
}
