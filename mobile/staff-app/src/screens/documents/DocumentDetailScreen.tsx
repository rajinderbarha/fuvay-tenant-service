import React from "react";
import { View, ScrollView, Linking } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { KeyValueList, SectionHeader, ListRow } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ENV } from "../../config/environment";
import { getAccessToken } from "../../services/auth/tokenCoordinator";
import { useDocuments } from "./useDocuments";
import { resolveDocumentStatus } from "./components/DocumentRow";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "DocumentDetail">;

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString() : "—";

/** Document Detail (Phase T spec section 9). State-specific guidance per
 * lifecycle state; "Preview" opens the access-checked /view endpoint
 * (already the real serving mechanism used for TenantDocument evidence
 * elsewhere in the codebase) -- never a public/permanent URL. */
export function DocumentDetailScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { docCode } = route.params;
  const { data, isLoading } = useDocuments();
  const requirement = data?.requirements.find(r => r.code === docCode);

  if (isLoading || !requirement) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Document" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={200} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  const visual = resolveDocumentStatus(requirement);
  const canReplace = requirement.allowed_actions.includes("replace") || requirement.review_status === "missing";

  const openPreview = () => {
    // No signed-URL endpoint is available to non-admin roles (confirmed by
    // audit) -- reuses the same access-checked /view URL convention that
    // tenant_documents_workspace_router.py already stores as file_url.
    const token = getAccessToken();
    if (!token) return;
    // Deep-linking a token into an in-app browser is out of scope here;
    // this opens the same authenticated API URL a logged-in session can reach.
    Linking.openURL(`${ENV.apiBaseUrl}/v1/media/${requirement.current_document_id}/view`).catch(() => {});
  };

  let guidance: string | null = null;
  if (requirement.review_status === "missing") guidance = "Upload this document to begin verification.";
  else if (requirement.review_status === "pending_review") guidance = "Verification is pending. You'll be notified once your business reviews it.";
  else if (requirement.review_status === "changes_requested") guidance = requirement.reviewer_note ?? "Your business asked for changes to this document.";
  else if (requirement.review_status === "rejected") guidance = requirement.reviewer_note ?? "This document was not approved.";
  else if (requirement.display_condition === "expired") guidance = "This document has expired. Replace it to stay eligible for assignment.";
  else if (requirement.display_condition === "expiring_soon") guidance = `This document expires in ${requirement.days_until_expiry} day${requirement.days_until_expiry === 1 ? "" : "s"}.`;
  else if (requirement.review_status === "verified") guidance = "This document is verified.";

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title={requirement.label} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, marginBottom: theme.spacing.sm }}>
              <AppText variant="bodyStrong" color={visual.color}>{visual.label}</AppText>
            </View>
            {guidance ? <InlineAlert tone={visual.color === "danger" ? "danger" : visual.color === "warning" ? "warning" : "neutral"} message={guidance} /> : null}
          </Card>
        </Section>

        {requirement.review_status !== "missing" ? (
          <Section>
            <SectionHeader title="Details" />
            <Card>
              <KeyValueList items={[
                { label: "Current version", value: requirement.current_version ? `v${requirement.current_version}` : "—" },
                { label: "Submitted", value: formatDate(requirement.submitted_at) },
                { label: "Verified", value: formatDate(requirement.verified_at) },
                { label: "Expiry", value: formatDate(requirement.expires_at) },
              ]} />
            </Card>
          </Section>
        ) : null}

        {requirement.review_status !== "missing" ? (
          <Section>
            <Card padding="base">
              <ListRow title="Preview document" onPress={openPreview} />
              <ListRow title="Version history" onPress={() => navigation.navigate("DocumentHistory", { docCode })} />
            </Card>
          </Section>
        ) : null}

        <Section>
          {requirement.review_status === "missing" || canReplace ? (
            <PrimaryButton
              label={requirement.review_status === "missing" ? "Upload document" : "Replace document"}
              onPress={() => navigation.navigate("DocumentUpload", { docCode })}
              fullWidth
            />
          ) : (
            <SecondaryButton label="Version history" onPress={() => navigation.navigate("DocumentHistory", { docCode })} fullWidth />
          )}
        </Section>
      </ScrollView>
    </SafeAreaScreen>
  );
}
