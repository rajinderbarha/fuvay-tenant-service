import React, { useCallback, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Icon } from "../../design-system/components/Icon";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState, EmptyState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { PrimaryButton, SecondaryButton, TertiaryButton } from "../../design-system/components/actions/Buttons";
import { StatusBadge } from "../../design-system/components/data-display/Badges";
import { LineItemRow } from "./components/LineItemRow";
import { PriceSummaryCard } from "./components/PriceSummaryCard";
import { AddItemSheet } from "./components/AddItemSheet";
import { useEstimate } from "./useEstimate";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { QuoteLineItemDTO } from "../../services/estimate/types";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "Estimate">;

const QUOTE_STATUS_LABEL: Record<string, string> = {
  draft: "Draft", submitted_to_provider: "Tenant review", provider_approved: "Tenant approved",
  provider_rejected: "Tenant changes requested", sent_to_customer: "Awaiting customer approval",
  customer_approved: "Approved", customer_rejected: "Rejected", revision_requested: "Revision requested",
  revised: "Revised", expired: "Expired", cancelled: "Cancelled",
};

/**
 * Estimate Builder / Approval Handoff (Phase L). Create/view/revise mode is
 * derived entirely from the backend-projected quote state -- never a
 * separate screen or client-side mode flag (spec section 1).
 */
export function EstimateScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId } = route.params;
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const [itemSheet, setItemSheet] = useState<{ open: boolean; editing: QuoteLineItemDTO | null }>({ open: false, editing: null });

  const {
    data, isLoading, isError, error, isRefetching, refetch,
    mutating, mutationError, createEstimate, createRevision, addItem, updateItem, removeItem, sendForApproval,
  } = useEstimate(jobId);

  const goBack = useCallback(() => navigation.navigate("JobDetail", { jobId }), [navigation, jobId]);

  const handleCreate = useCallback(async () => { await createEstimate(); }, [createEstimate]);
  const handleRevise = useCallback(async () => {
    if (data?.quote) await createRevision(data.quote.quote_id);
  }, [createRevision, data]);

  const handleSubmitItem = useCallback(async (item: { item_type: any; item_name: string; quantity: number; unit_price: number }) => {
    if (!data?.quote) return;
    const result = itemSheet.editing
      ? await updateItem(data.quote.quote_id, itemSheet.editing.id, item)
      : await addItem(data.quote.quote_id, item);
    if (result.ok) setItemSheet({ open: false, editing: null });
  }, [data, itemSheet.editing, addItem, updateItem]);

  const handleSend = useCallback(async () => {
    if (data?.quote) await sendForApproval(data.quote.quote_id);
  }, [sendForApproval, data]);

  if (isLoading) {
    return (
      <SafeAreaScreen>
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="60%" height={20} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={140} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={160} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load estimate" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  const quote = data.quote;
  const isEditable = Boolean(quote && data.allowed_actions.includes("edit_estimate"));
  const canSubmit = data.allowed_actions.includes("send_for_approval");
  const canCreateRevision = data.allowed_actions.includes("create_revision");

  return (
    <SafeAreaScreen edges={["top", "left", "right"]} style={{ flex: 0 }}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        <View style={{ flex: 1, alignItems: "center" }}>
          <AppText variant="bodyStrong">{quote ? (quote.status === "draft" ? "Create estimate" : "Estimate details") : "Create estimate"}</AppText>
          <AppText variant="caption" color="tertiary">{data.job.job_reference}</AppText>
        </View>
        {quote ? (
          <View style={{ width: 90, alignItems: "flex-end" }}>
            <AppText variant="caption" color="tertiary">{QUOTE_STATUS_LABEL[quote.status] ?? quote.status}</AppText>
          </View>
        ) : <View style={{ width: 44 }} />}
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Estimate is read-only until you reconnect." /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete that action" message={mutationError.safeMessage} /></View> : null}

        <Section>
          <Card style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
            <Icon name={data.inspection_source.completed ? "checkmark-circle" : "time-outline"} size="standard" color={data.inspection_source.completed ? theme.colors.statusSuccess : theme.colors.textTertiary} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{data.inspection_source.completed ? "Inspection completed" : "Inspection not yet complete"}</AppText>
              <AppText variant="caption" color="tertiary">
                {[data.inspection_source.diagnosis_summary, data.inspection_source.evidence_count > 0 ? `${data.inspection_source.evidence_count} photos` : null].filter(Boolean).join(" · ") || "No findings recorded"}
              </AppText>
            </View>
          </Card>
        </Section>

        {!quote ? (
          data.readiness.blockers.length > 0 ? (
            <EmptyState icon="lock-closed-outline" title="Complete inspection first" message="An estimate can be created once the required inspection checklist is complete." />
          ) : (
            <EmptyState icon="document-text-outline" title="No estimate yet" message="Create an estimate from the completed inspection findings." actionLabel="Create estimate" onAction={handleCreate} />
          )
        ) : (
          <>
            <Section>
              <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Estimate items</AppText>
              <Card padding="base">
                {quote.line_items.filter(i => i.item_type !== "discount").map(item => (
                  <LineItemRow
                    key={item.id}
                    item={item}
                    editable={isEditable}
                    onEdit={() => setItemSheet({ open: true, editing: item })}
                    onRemove={() => removeItem(quote.quote_id, item.id)}
                  />
                ))}
                {isEditable ? (
                  <TertiaryButton label="+ Add item" onPress={() => setItemSheet({ open: true, editing: null })} fullWidth />
                ) : null}
              </Card>
            </Section>

            <Section>
              <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Price summary</AppText>
              <PriceSummaryCard calculation={data.calculation} />
            </Section>

            {Number(data.calculation.visit_fee_adjustment) !== 0 ? (
              <InlineAlert tone="info" message="Visit fee is adjusted because the customer continues with the work." />
            ) : null}

            <View style={{ marginTop: theme.spacing.base }}>
              <InlineAlert tone="warning" title="Customer approval required" message="Work cannot start until the current estimate is approved." />
            </View>
          </>
        )}
      </ScrollView>

      {quote && isEditable ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Save draft" onPress={() => { void refetch(); }} fullWidth />
          </View>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Send for approval" onPress={handleSend} disabled={!canSubmit || offline} loading={mutating} fullWidth />
          </View>
        </View>
      ) : canCreateRevision ? (
        <View style={{ padding: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
          <PrimaryButton label="Create revision" onPress={handleRevise} loading={mutating} disabled={offline} fullWidth />
        </View>
      ) : null}

      <AddItemSheet
        visible={itemSheet.open}
        onClose={() => setItemSheet({ open: false, editing: null })}
        onSubmit={handleSubmitItem}
        initial={itemSheet.editing}
        submitting={mutating}
      />
    </SafeAreaScreen>
  );
}
