import React, { useState, useCallback, useMemo } from "react";
import { View, FlatList, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Heading } from "../../design-system/components/typography/Heading";
import { AppText } from "../../design-system/components/typography/AppText";
import { Caption } from "../../design-system/components/typography/Label";
import { SearchField } from "../../design-system/components/forms/SearchField";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Icon } from "../../design-system/components/Icon";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState } from "../../design-system/components/feedback/States";
import { InlineAlert, OfflineBanner } from "../../design-system/components/feedback/Banner";
import { LoadingSpinner } from "../../design-system/components/feedback/Loading";
import { JobListCard } from "./components/JobListCard";
import { JobsFilterSheet, JobsFilters } from "./components/JobsFilterSheet";
import { useTechnicianJobs } from "./useTechnicianJobs";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { JobsView, JobListItemDTO } from "../../services/jobs/types";

const TABS: { key: JobsView; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "active", label: "Active" },
  { key: "upcoming", label: "Upcoming" },
  { key: "completed", label: "Completed" },
];

const EXECUTION_ROUTE_FOR_ACTION: Record<string, string> = {
  start_inspection: "Inspection",
  complete: "CompletionProof",
};

const EMPTY_MESSAGE: Record<JobsView, string> = {
  today: "No jobs scheduled today.",
  active: "No active jobs right now.",
  upcoming: "No upcoming jobs.",
  completed: "No completed jobs yet.",
  archive: "Nothing in the archive.",
};

export function JobsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<any>();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";

  const [view, setView] = useState<JobsView>("today");
  const [showArchive, setShowArchive] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState<JobsFilters>({});
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(searchInput.trim(), 400);

  const effectiveView = showArchive ? "archive" : view;
  const {
    items, countsByView, isLoading, isError, error, isRefetching, refetch,
    fetchNextPage, hasNextPage, isFetchingNextPage,
  } = useTechnicianJobs({ view: effectiveView, search: debouncedSearch, ...filters });

  const activeFilterCount = (filters.workflowStatus ? 1 : 0) + (filters.actionRequired ? 1 : 0);

  const openJob = useCallback((jobId: string, jobReference: string, targetAction?: string) => {
    const screen = (targetAction && EXECUTION_ROUTE_FOR_ACTION[targetAction]) || "JobDetail";
    navigation.getParent()?.navigate("JobExecutionStack", { screen, params: { jobId, jobReference, targetAction } });
  }, [navigation]);

  const renderItem = useCallback(({ item }: { item: JobListItemDTO }) => (
    <View style={{ marginBottom: theme.spacing.sm }}>
      <JobListCard
        job={item}
        onPress={() => openJob(item.job_id, item.job_reference)}
        onPrimaryAction={() => openJob(item.job_id, item.job_reference, item.next_required_action.key ?? undefined)}
      />
    </View>
  ), [openJob, theme.spacing.sm]);

  const listHeader = useMemo(() => (
    <View>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end", marginBottom: theme.spacing.sm }}>
        <AppText variant="bodySmall" color="tertiary">
          {showArchive ? "Archive" : TABS.find(t => t.key === view)?.label} · Earliest first
        </AppText>
        <Icon name="swap-vertical-outline" size="compact" color={theme.colors.textTertiary} decorative />
      </View>
      {offline ? <OfflineBanner /> : null}
      {isError && items.length > 0 ? <InlineAlert tone="warning" title="Some jobs may be out of date" message={error?.safeMessage ?? "Pull to refresh."} /> : null}
    </View>
  ), [showArchive, view, offline, isError, items.length, error, theme.spacing.sm]);

  return (
    <SafeAreaScreen style={{ flex: 1, paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.base }}>
      <Heading level="large">Jobs</Heading>
      <AppText color="secondary" style={{ marginBottom: theme.spacing.base }}>Your assigned work</AppText>

      <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginBottom: theme.spacing.base }}>
        <View style={{ flex: 1 }}>
          <SearchField
            placeholder="Search job or service"
            value={searchInput}
            onChangeText={setSearchInput}
            onClear={() => setSearchInput("")}
          />
        </View>
        <IconButton
          icon="filter-outline"
          accessibilityLabel={activeFilterCount > 0 ? `Filters, ${activeFilterCount} active` : "Filters"}
          onPress={() => setFilterSheetOpen(true)}
        />
      </View>

      <View style={{ flexDirection: "row", marginBottom: theme.spacing.base }} accessibilityRole="tablist">
        {TABS.map(tab => {
          const selected = !showArchive && view === tab.key;
          const count = countsByView?.[tab.key];
          return (
            <View key={tab.key} style={{ marginRight: theme.spacing.base }}>
              <AppText
                variant={selected ? "bodyStrong" : "body"}
                color={selected ? "primary" : "tertiary"}
                onPress={() => { setShowArchive(false); setView(tab.key); }}
                accessibilityRole="tab"
                accessibilityState={{ selected }}
                accessibilityLabel={`${tab.label}${count !== undefined ? `, ${count} jobs` : ""}`}
                style={selected ? { borderBottomWidth: 2, borderBottomColor: theme.colors.brandPrimary, paddingBottom: 4 } : { paddingBottom: 4 }}
              >
                {tab.label}{count !== undefined ? ` ${count}` : ""}
              </AppText>
            </View>
          );
        })}
        <AppText
          variant={showArchive ? "bodyStrong" : "body"}
          color={showArchive ? "primary" : "tertiary"}
          onPress={() => setShowArchive(true)}
          accessibilityRole="tab"
          accessibilityState={{ selected: showArchive }}
        >
          Archive
        </AppText>
      </View>

      {isLoading ? (
        <View>
          <Skeleton width="100%" height={160} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={160} radius={theme.radiusUsage.card} />
        </View>
      ) : isError && items.length === 0 ? (
        <EmptyState
          icon={offline ? "cloud-offline-outline" : "alert-circle-outline"}
          title={offline ? "You're offline" : "Couldn't load jobs"}
          message={offline ? "Connect to the internet to view your jobs." : (error?.safeMessage ?? "Please try again.")}
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon="briefcase-outline"
          title={debouncedSearch ? "No matches" : "Nothing here"}
          message={debouncedSearch ? `No jobs match "${debouncedSearch}".` : EMPTY_MESSAGE[effectiveView]}
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={item => item.job_id}
          renderItem={renderItem}
          ListHeaderComponent={listHeader}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
          onEndReached={() => { if (hasNextPage && !isFetchingNextPage) fetchNextPage(); }}
          onEndReachedThreshold={0.4}
          ListFooterComponent={
            isFetchingNextPage ? <View style={{ paddingVertical: theme.spacing.base }}><LoadingSpinner /></View>
              : !hasNextPage && items.length > 0 ? (
                <Caption color="tertiary" style={{ textAlign: "center", paddingVertical: theme.spacing.base }}>
                  Showing all {items.length}
                </Caption>
              ) : null
          }
        />
      )}

      <JobsFilterSheet
        visible={filterSheetOpen}
        initialFilters={filters}
        onApply={next => { setFilters(next); setFilterSheetOpen(false); }}
        onClose={() => setFilterSheetOpen(false)}
      />
    </SafeAreaScreen>
  );
}
