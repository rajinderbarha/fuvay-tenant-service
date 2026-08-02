import React, { useCallback, useMemo, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Heading } from "../../design-system/components/typography/Heading";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState, EmptyState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { Icon } from "../../design-system/components/Icon";
import { WeekStrip } from "./components/WeekStrip";
import { AvailabilityCard } from "./components/AvailabilityCard";
import { ScheduleTimeline } from "./components/ScheduleTimeline";
import { useSchedule } from "./useSchedule";
import { useTechnicianHome } from "../home/useTechnicianHome";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { ScheduleStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ScheduleStackParamList, "ScheduleHome">;

const MONTH_LABEL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function toLocalIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/**
 * Schedule & Availability (Phase P). A projection of canonical assignments
 * -- never an alternative assignment source (spec section 7). Opening a
 * job navigates to the existing canonical Job Detail screen.
 */
export function ScheduleScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const rootNavigation = useNavigation<any>();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";
  const [selectedDate, setSelectedDate] = useState(new Date());

  const { data, isLoading, isError, error, isRefetching, refetch, weekDates, mutating, mutationError, removeBlockedTime } = useSchedule(selectedDate);
  const { data: homeData } = useTechnicianHome();

  const selectedIso = toLocalIso(selectedDate);
  const selectedDay = data?.days.find(d => d.date === selectedIso);

  const hasWorkByDate = useMemo(() => {
    const map: Record<string, boolean> = {};
    (data?.days ?? []).forEach(d => { map[d.date] = d.assigned_job_count > 0; });
    return map;
  }, [data]);

  const openJob = useCallback((jobId: string) => {
    rootNavigation.getParent()?.navigate("JobExecutionStack", { screen: "JobDetail", params: { jobId } });
  }, [rootNavigation]);

  const openManageAvailability = useCallback(() => navigation.navigate("ManageAvailability"), [navigation]);
  const openRequestTimeOff = useCallback(() => navigation.navigate("RequestTimeOff"), [navigation]);

  if (isLoading) {
    return (
      <SafeAreaScreen style={{ padding: theme.spacing.lg }}>
        <Skeleton width="60%" height={24} />
        <View style={{ height: theme.spacing.base }} />
        <Skeleton width="100%" height={80} radius={theme.radiusUsage.card} />
        <View style={{ height: theme.spacing.base }} />
        <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load your schedule" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen style={{ flex: 1, paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.base }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.base }}>
        <View>
          <Heading level="large">Schedule</Heading>
          <AppText color="secondary">Your work and availability</AppText>
        </View>
        <IconButton icon="calendar-outline" accessibilityLabel="Open calendar picker" onPress={() => {}} />
      </View>

      <ScrollView
        contentContainerStyle={{ paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message={data ? `Showing cached schedule from ${new Date(data.last_synced_at).toLocaleTimeString()}` : "No cached schedule available."} /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete that action" message={mutationError.safeMessage} /></View> : null}

        <Section>
          <AvailabilityCard
            state={homeData?.availability?.state ?? "available"}
            workingHoursLabel={selectedDay?.working_hours_label ?? null}
            onManage={openManageAvailability}
          />
        </Section>

        <Section>
          <AppText variant="label" color="tertiary" style={{ marginBottom: theme.spacing.xs }}>
            {MONTH_LABEL[weekDates[0].getMonth()]} {weekDates[0].getFullYear()}
          </AppText>
          <WeekStrip weekDates={weekDates} selectedDate={selectedDate} onSelect={setSelectedDate} hasWorkByDate={hasWorkByDate} />
        </Section>

        {selectedDay ? (
          <Section>
            <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              <Card style={{ flex: 1, alignItems: "center" }} padding="sm">
                <Icon name="briefcase-outline" size="compact" color={theme.colors.textTertiary} decorative />
                <AppText variant="bodyStrong">{selectedDay.assigned_job_count}</AppText>
                <AppText variant="caption" color="tertiary">jobs</AppText>
              </Card>
              <Card style={{ flex: 1, alignItems: "center" }} padding="sm">
                <Icon name="time-outline" size="compact" color={theme.colors.textTertiary} decorative />
                <AppText variant="bodyStrong">{selectedDay.open_slot_count}</AppText>
                <AppText variant="caption" color="tertiary">open slots</AppText>
              </Card>
              <Card style={{ flex: 1, alignItems: "center" }} padding="sm">
                <Icon name="person-outline" size="compact" color={theme.colors.textTertiary} decorative />
                <AppText variant="bodyStrong">{selectedDay.pending_leave_count}</AppText>
                <AppText variant="caption" color="tertiary">pending leave</AppText>
              </Card>
            </View>
          </Section>
        ) : null}

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.sm }}>
            {selectedDate.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}
          </AppText>
          {selectedDay && selectedDay.items.length > 0 ? (
            <ScheduleTimeline items={selectedDay.items} onOpenJob={openJob} onRemoveBlock={id => removeBlockedTime(id)} />
          ) : (
            <EmptyState icon="calendar-outline" title="Nothing scheduled" message="No jobs, slots or blocked time for this day." />
          )}
        </Section>
      </ScrollView>

      <View style={{ paddingBottom: theme.spacing.base }}>
        <PrimaryButton label="Request time off" onPress={openRequestTimeOff} disabled={offline} fullWidth />
      </View>
    </SafeAreaScreen>
  );
}
