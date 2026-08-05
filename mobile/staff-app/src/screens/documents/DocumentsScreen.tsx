import React, { useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { DocumentsReadinessCard } from "./components/DocumentsReadinessCard";
import { DocumentFilterPills } from "./components/DocumentFilterPills";
import { DocumentRow } from "./components/DocumentRow";
import { useDocuments } from "./useDocuments";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { DocumentFilter, DocumentRequirementDTO } from "../../services/documents/types";

type Props = NativeStackScreenProps<ProfileStackParamList, "Documents">;

function matchesFilter(req: DocumentRequirementDTO, filter: DocumentFilter): boolean {
  if (filter === "all") return true;
  if (filter === "verified") return req.review_status === "verified";
  if (filter === "pending") return req.review_status === "pending_review";
  if (filter === "action_needed") {
    return req.review_status === "missing" || req.review_status === "rejected" || req.review_status === "changes_requested" || req.display_condition === "expired";
  }
  return true;
}

/**
 * Documents & Certifications (Phase T). Verification is completed by the
 * tenant, never by the technician -- this screen has no approve/reject
 * action anywhere (spec section 10: "Technician app must not contain these
 * review actions").
 */
export function DocumentsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const [filter, setFilter] = useState<DocumentFilter>("all");

  const { data, isLoading, isError, error, isRefetching, refetch } = useDocuments();

  if (isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Documents & certifications" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="100%" height={140} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.base }} />
          <Skeleton width="100%" height={300} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Documents & certifications" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load documents" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  const actionNeeded = data.requirements.filter(r => matchesFilter(r, "action_needed"));
  const requiredDocs = data.requirements.filter(r => r.required);
  const optionalDocs = data.requirements.filter(r => !r.required);
  const visibleActionNeeded = filter === "all" || filter === "action_needed" ? actionNeeded : [];
  const visibleRequired = requiredDocs.filter(r => matchesFilter(r, filter));
  const visibleOptional = optionalDocs.filter(r => matchesFilter(r, filter));

  const openDetail = (requirement: DocumentRequirementDTO) => {
    if (requirement.review_status === "missing") {
      navigation.navigate("DocumentUpload", { docCode: requirement.code });
    } else {
      navigation.navigate("DocumentDetail", { docCode: requirement.code });
    }
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Documents & certifications" onBack={() => navigation.goBack()} />
      <ScrollView
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached documents. Upload and replace are disabled until you're back online." /></View> : null}

        <Section>
          <DocumentsReadinessCard readiness={data.readiness} onUpload={() => navigation.navigate("DocumentUpload", { docCode: undefined })} />
        </Section>

        <Section>
          <DocumentFilterPills readiness={data.readiness} totalCount={data.requirements.length} value={filter} onChange={setFilter} />
        </Section>

        {visibleActionNeeded.length > 0 && filter !== "verified" && filter !== "pending" ? (
          <Section>
            <SectionHeader title="Action needed" />
            <Card padding="base" style={{ borderWidth: 1, borderColor: theme.colors.statusWarning }}>
              {visibleActionNeeded.map(r => <DocumentRow key={r.requirement_id} requirement={r} onPress={() => openDetail(r)} />)}
            </Card>
          </Section>
        ) : null}

        <Section>
          <SectionHeader title="Required documents" />
          <Card padding="base">
            {visibleRequired.length === 0
              ? <AppText variant="bodySmall" color="tertiary">No documents match this filter.</AppText>
              : visibleRequired.map(r => <DocumentRow key={r.requirement_id} requirement={r} onPress={() => openDetail(r)} />)}
          </Card>
        </Section>

        {visibleOptional.length > 0 ? (
          <Section>
            <SectionHeader title="Optional documents" />
            <Card padding="base">
              {visibleOptional.map(r => <DocumentRow key={r.requirement_id} requirement={r} onPress={() => openDetail(r)} />)}
            </Card>
          </Section>
        ) : null}

        <Section>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, padding: theme.spacing.base, backgroundColor: theme.colors.surfaceInteractive, borderRadius: theme.radiusUsage.card }}>
            <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
            <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>Files are encrypted and visible only to authorized reviewers.</AppText>
          </View>
          <AppText variant="caption" color="tertiary" style={{ textAlign: "center", marginTop: theme.spacing.sm }}>Verification is completed by your business.</AppText>
        </Section>
      </ScrollView>
    </SafeAreaScreen>
  );
}
