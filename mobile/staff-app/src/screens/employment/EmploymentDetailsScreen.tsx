import React, { useState } from "react";
import { View, Image, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { KeyValueList, SectionHeader, ListRow } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState, EmptyState } from "../../design-system/components/feedback/States";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { AssignmentChip, SkillChip } from "./components/AssignmentChip";
import { PermissionsSummarySheet } from "./components/PermissionsSummarySheet";
import { RequestCorrectionSheet } from "./components/RequestCorrectionSheet";
import { useEmploymentDetails } from "./useEmploymentDetails";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { CorrectionFieldKey } from "../../services/employment/types";

type Props = NativeStackScreenProps<ProfileStackParamList, "EmploymentDetails">;

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—";

/**
 * Employment Details (Phase S). Read-only projection over the canonical
 * ProviderTeamMember + real capability-resolution SQL. Incorrect data is
 * handled through the structured Request Correction workflow, never direct
 * editing of tenant-controlled fields (spec sections 1, 5).
 */
export function EmploymentDetailsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const [permissionsOpen, setPermissionsOpen] = useState(false);
  const [correctionOpen, setCorrectionOpen] = useState(false);

  const { data, isLoading, isError, error, refetch, submitCorrection, submitting, submitError } = useEmploymentDetails();

  if (isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Employment details" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="100%" height={100} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.base }} />
          <Skeleton width="100%" height={220} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Employment details" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load employment details" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  const employment = data.employment;
  const statusKnown = data.status_known;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Employment details" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}>
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached employment details." /></View> : null}

        <Section>
          <Card style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.base }}>
            <View style={{ width: 48, height: 48, borderRadius: 10, overflow: "hidden", backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center" }}>
              {data.business.logo_url ? (
                <Image source={{ uri: data.business.logo_url }} style={{ width: 48, height: 48 }} />
              ) : (
                <Icon name="business-outline" size="standard" color={theme.colors.brandPrimary} decorative />
              )}
            </View>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                <AppText variant="title" style={{ flex: 1 }}>{data.business.name ?? "—"}</AppText>
                {employment && statusKnown ? (
                  <View style={{
                    paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill,
                    backgroundColor: employment.status === "active" ? theme.colors.statusSuccessSurface : theme.colors.statusNeutralSurface,
                  }}>
                    <AppText variant="labelStrong" color={employment.status === "active" ? "success" : "tertiary"}>
                      {employment.status === "active" ? "Active" : "Inactive"}
                    </AppText>
                  </View>
                ) : null}
              </View>
              {data.business.vertical_label ? <AppText color="secondary">{data.business.vertical_label}</AppText> : null}
              {employment?.joined_at ? <AppText variant="caption" color="tertiary">Member since {formatDate(employment.joined_at)}</AppText> : null}
            </View>
          </Card>
        </Section>

        {!employment ? (
          <EmptyState icon="briefcase-outline" title="No employment record" message="We couldn't find an employment record for your account with this business." />
        ) : !statusKnown ? (
          <InlineAlert tone="neutral" title="Employment status unavailable" message="We couldn't determine your current employment status. Please contact your business or support." />
        ) : (
          <>
            <Section>
              <SectionHeader title="Employment" />
              <Card>
                <KeyValueList items={[
                  { label: "Staff ID", value: employment.staff_reference },
                  { label: "Staff type", value: employment.staff_type ?? "—" },
                  { label: "Designation", value: employment.designation ?? "—" },
                  { label: "Reports to", value: employment.reports_to ? `${employment.reports_to.display_name ?? ""}${employment.reports_to.designation ? ` · ${employment.reports_to.designation}` : ""}` : "—" },
                  { label: "Joined", value: formatDate(employment.joined_at) },
                ]} />
                <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>Managed by your business -- read-only</AppText>
              </Card>
            </Section>

            {employment.status === "active" ? (
              <>
                <Section>
                  <SectionHeader title="Assigned work" />
                  <Card>
                    <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.xs }}>Service groups</AppText>
                    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs, marginBottom: theme.spacing.base }}>
                      {data.assignments.service_groups.length === 0
                        ? <AppText variant="bodySmall" color="tertiary">None assigned yet</AppText>
                        : data.assignments.service_groups.map(g => <AssignmentChip key={g.id} label={g.name} />)}
                    </View>
                    <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.xs }}>Job types</AppText>
                    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs, marginBottom: theme.spacing.base }}>
                      {data.assignments.job_types.length === 0
                        ? <AppText variant="bodySmall" color="tertiary">None assigned yet</AppText>
                        : data.assignments.job_types.map(j => <AssignmentChip key={j.id} label={j.name} />)}
                    </View>
                    <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.xs }}>Verified skills</AppText>
                    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs }}>
                      {data.assignments.verified_skills.length === 0
                        ? <AppText variant="bodySmall" color="tertiary">None recorded yet</AppText>
                        : data.assignments.verified_skills.map(s => <SkillChip key={s.id} label={s.name} verified={s.verification_status === "verified"} />)}
                    </View>
                  </Card>
                </Section>

                <Section>
                  <SectionHeader title="Work scope" />
                  <Card padding="base">
                    <View style={{ paddingVertical: theme.spacing.sm }}>
                      <AppText variant="body">Service area</AppText>
                      <AppText variant="bodySmall" color="tertiary">{data.scope?.service_area_summary ?? "Not configured"}</AppText>
                      <AppText variant="caption" color="tertiary">Managed by your business</AppText>
                    </View>
                    <ListRow
                      title="Working schedule"
                      subtitle={data.scope?.working_schedule_summary ?? "Not configured"}
                      onPress={() => navigation.navigate("AvailabilityPreferences")}
                    />
                    <ListRow
                      title="Permissions"
                      subtitle={`Technician access · ${data.scope?.effective_capability_count ?? 0} capabilities enabled`}
                      onPress={() => setPermissionsOpen(true)}
                    />
                  </Card>
                </Section>
              </>
            ) : (
              <InlineAlert tone="neutral" title="Employment inactive" message="Assigned work and permissions are hidden while your employment is inactive." />
            )}

            <Section>
              <InlineAlert tone="neutral" message={`Employment details are managed by ${data.business.name ?? "your business"}.`} />
              <View style={{ height: theme.spacing.base }} />
              {data.allowed_actions.request_correction ? (
                <SecondaryButton label="Request correction" onPress={() => setCorrectionOpen(true)} fullWidth />
              ) : null}
            </Section>
          </>
        )}
      </ScrollView>

      <PermissionsSummarySheet visible={permissionsOpen} onClose={() => setPermissionsOpen(false)} permissions={data.permissions} />
      <RequestCorrectionSheet
        visible={correctionOpen}
        onClose={() => setCorrectionOpen(false)}
        submitting={submitting}
        error={submitError?.safeMessage ?? null}
        currentValues={{
          designation: employment?.designation ?? null,
          reports_to: employment?.reports_to ? `${employment.reports_to.display_name ?? ""} · ${employment.reports_to.designation ?? ""}` : null,
          joined_at: employment?.joined_at ? formatDate(employment.joined_at) : null,
          service_area: data.scope?.service_area_summary ?? null,
        }}
        onSubmit={(fieldKey: CorrectionFieldKey, requestedValue, reason) => submitCorrection(fieldKey, requestedValue, reason)}
      />
    </SafeAreaScreen>
  );
}
