import React, { useCallback, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi, useAction } from "../../hooks/useApi";
import { jobsApi } from "../../lib/api";
import { NEXT_ACTION, ACTION_LABEL, STATUS_LABEL, type JobAction } from "../../lib/transitions";
import { JobStatusBadge } from "../../components/JobStatusBadge";
import { Skeleton } from "../../components/Skeleton";
import { PipelineBadge } from "../../components/ux05/PipelineBadge";
import { CustomerContactCard } from "../../components/ux05/CustomerContactCard";
import { AddressCard } from "../../components/ux05/AddressCard";
import { NextActionBar } from "../../components/ux05/NextActionBar";
import { theme, gs } from "../../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { ActionPermissionView, CustomerContactView } from "../../types/ux05";

type Params = { jobId: string };
type Props = NativeStackScreenProps<{ CurrentJob: Params }, "CurrentJob">;

const ACTION_FN: Record<JobAction, (jobId: string, arg?: string) => Promise<unknown>> = {
  accept: (id) => jobsApi.accept(id),
  reject: (id, reason) => jobsApi.reject(id, reason ?? ""),
  onTheWay: (id) => jobsApi.onTheWay(id),
  reachedSite: (id) => jobsApi.reachedSite(id),
  startInspection: (id) => jobsApi.startInspection(id),
  completeInspection: (id) => jobsApi.completeInspection(id),
  startService: (id) => jobsApi.startService(id),
  workDone: (id) => jobsApi.workDone(id),
  complete: () => Promise.reject(new Error("complete requires work_summary/collected_amount -- use JobDetailScreen's modal for this step")),
};

/**
 * Current Job mode (workstream 9): a focused single-job view for the job
 * a technician is actively working, distinct from the full JobDetailScreen
 * (which also handles browsing any assigned job, including ones not yet
 * started). Sticky primary action at the bottom, no tabs -- everything a
 * technician needs mid-job is one scroll away. Reuses the same real
 * jobsApi/transitions.ts state machine as JobDetailScreen (no parallel
 * transition logic invented).
 */
export function CurrentJobScreen({ route }: Props) {
  const { jobId } = route.params;
  const detail = useApi(useCallback(() => jobsApi.get(jobId), [jobId]));
  const actionState = useAction(useCallback(async (action: JobAction, arg?: string) => {
    if (action === "reject") return jobsApi.reject(jobId, arg ?? "");
    return ACTION_FN[action](jobId, arg);
  }, [jobId]));
  const [offline] = useState(false); // NetworkStatusBanner/offline detection not wired here yet -- see known-limitations.md

  const j = detail.data?.job;
  const booking = detail.data?.booking;
  const nextActions = j ? (NEXT_ACTION[j.status] ?? []) : [];
  const primary: ActionPermissionView | null = nextActions.length > 0
    ? { action: nextActions[0], label: ACTION_LABEL[nextActions[0]], available: true, reason: null, offlineAllowed: false }
    : null;

  async function handlePrimary() {
    if (!primary) return;
    if (primary.action === "reject" || primary.action === "complete") {
      Alert.alert("Use Job Detail", "This action requires additional input -- open the full Job Detail screen.");
      return;
    }
    const res = await actionState.execute(primary.action);
    if (res) detail.refetch();
  }

  if (detail.loading) return (
    <ScrollView style={gs.screen} contentContainerStyle={{ padding: theme.spacing.base, gap: 14 }}>
      {[...Array(4)].map((_, i) => <Skeleton key={i} height={80} />)}
    </ScrollView>
  );

  if (!j) return (
    <View style={[gs.screen, { alignItems: "center", justifyContent: "center" }]}>
      <Text style={s.notFound}>Job not found or not assigned to you.</Text>
    </View>
  );

  const contact: CustomerContactView | null = booking ? {
    meta: { readiness: "production_ready" },
    name: booking.customer_name, city: booking.city, zipcode: booking.zipcode,
    issueSummary: booking.issue_summary, preferredDate: booking.preferred_date,
    preferredTimeWindow: booking.preferred_time_window, callSupported: false, messageSupported: false,
  } : null;

  return (
    <View style={gs.screen} testID="current-job-screen">
      <ScrollView contentContainerStyle={[s.content, { paddingBottom: 100 }]}>
        <View style={[gs.card, s.header]}>
          <View style={[gs.row, { justifyContent: "space-between" }]}>
            <Text style={s.jobNum}>{j.job_number}</Text>
            <JobStatusBadge status={j.status} />
          </View>
          <PipelineBadge provenance={{ pipeline: "service_booking_service_job", sourceBookingId: j.booking_id, jobId: j.id, jobModel: "ServiceJob" }} />
          <Text style={s.currentState}>Current state: {STATUS_LABEL[j.status] ?? j.status}</Text>
        </View>

        {contact && <CustomerContactCard contact={contact} />}
        {contact && <AddressCard contact={contact} />}

        {j.completion_data && (
          <View style={[gs.card, { gap: 6 }]}>
            <Text style={gs.label}>Completion</Text>
            <Text style={s.body}>{String(j.completion_data.work_summary ?? "")}</Text>
          </View>
        )}

        {/* Inspection/checklist/parts/media -- MOCK_DESIGN_ONLY placeholders;
            see InspectionChecklistShowcaseScreen / JobNotesMediaShowcaseScreen
            / PartsRequestShowcaseScreen for the real interaction patterns.
            Not duplicated here to avoid two divergent implementations of the
            same not-yet-backed workflow. */}
        <View style={[gs.card, { gap: 4 }]}>
          <Text style={gs.label}>Inspection · Checklist · Parts · Media</Text>
          <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live endpoint for any of these yet. See the dev showcases for the interaction patterns.</Text>
        </View>

        {actionState.error && <Text style={s.errText}>{actionState.error}</Text>}
      </ScrollView>
      <NextActionBar action={primary} onPress={handlePrimary} offline={offline} />
    </View>
  );
}

const s = StyleSheet.create({
  content:      { padding: theme.spacing.base, gap: 12 },
  header:       { gap: 8 },
  jobNum:       { fontSize: theme.font.size.base, fontWeight: "700", color: theme.colors.textPrimary },
  currentState: { fontSize: theme.font.size.sm, color: theme.colors.textSecondary, fontWeight: "600" },
  body:         { fontSize: theme.font.size.sm, color: theme.colors.textSecondary },
  mockNote:     { fontSize: theme.font.size.xs, color: theme.colors.textTertiary },
  errText:      { fontSize: theme.font.size.sm, color: theme.colors.dangerText },
  notFound:     { fontSize: theme.font.size.base, color: theme.colors.textTertiary },
});
