import React, { useCallback, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { TextField } from "../../design-system/components/forms/TextField";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { SegmentedControl } from "../../design-system/components/forms/SegmentedControl";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { AmountDueCard } from "./components/AmountDueCard";
import { ClosureReadinessList, ReadinessRow } from "./components/ClosureReadinessList";
import { useDirectPayment } from "./useDirectPayment";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { DirectPaymentMethod } from "../../services/directPayment/types";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "DirectPaymentConfirmation">;

const METHOD_OPTIONS: { value: DirectPaymentMethod; label: string }[] = [
  { value: "onsite_cash", label: "Cash" },
  { value: "onsite_upi", label: "UPI" },
  { value: "onsite_card", label: "Card to provider" },
  { value: "onsite_bank_transfer", label: "Bank transfer" },
];

const STATUS_LABEL: Record<string, string> = {
  not_declared: "Not recorded", awaiting_provider: "Awaiting provider", awaiting_customer: "Awaiting customer confirmation",
  confirmed: "Confirmed", mismatched: "Amount mismatch", disputed: "Disputed", cancelled: "Cancelled", reversed: "Reversed",
};

/**
 * Direct Payment Confirmation & Final Job Closure (Phase O). ServiceOS
 * never collects this payment -- it only records the provider's assertion
 * and the customer's independent confirmation (spec section 1).
 */
export function DirectPaymentScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId } = route.params;
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";

  const [method, setMethod] = useState<DirectPaymentMethod>("onsite_cash");
  const [reference, setReference] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  const { data, isLoading, isError, error, isRefetching, refetch, mutating, mutationError, declarePayment, remindCustomer, finalizeJob } = useDirectPayment(jobId);

  const goBack = useCallback(() => navigation.navigate("JobDetail", { jobId }), [navigation, jobId]);

  const handleDeclare = useCallback(async () => {
    if (!data?.amount.expected_amount) return;
    await declarePayment({ amount: data.amount.expected_amount, method, reference_id: reference.trim() || undefined });
  }, [data, declarePayment, method, reference]);

  const handleFinalize = useCallback(async () => {
    const result = await finalizeJob();
    if (result.ok) goBack();
  }, [finalizeJob, goBack]);

  if (isLoading) {
    return (
      <SafeAreaScreen>
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="60%" height={20} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={140} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load payment confirmation" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  if (data.job.workflow_status === "completed") {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
          <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        </View>
        <View style={{ alignItems: "center", padding: theme.spacing.xxl }}>
          <AppText variant="title">Job completed</AppText>
          <AppText color="secondary" style={{ textAlign: "center", marginTop: theme.spacing.xs }}>
            Payment recorded as paid directly to the provider.
          </AppText>
        </View>
      </SafeAreaScreen>
    );
  }

  const hasRecord = Boolean(data.provider_record);
  const canDeclare = data.allowed_actions.includes("declare_payment");
  const canRemind = data.allowed_actions.includes("remind_customer");
  const canFinalize = data.allowed_actions.includes("finalize_job");

  const readinessRows: ReadinessRow[] = [
    { label: "Completion proof", complete: data.prerequisites.completion_proof_submitted },
    { label: "Customer handover", complete: data.prerequisites.customer_handover_status === "acknowledged" },
    { label: "Provider payment record", complete: hasRecord },
    { label: "Customer payment confirmation", complete: data.provider_record?.status === "confirmed" },
  ];

  return (
    <SafeAreaScreen edges={["top", "left", "right"]} style={{ flex: 0 }}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        <View style={{ flex: 1, alignItems: "center" }}>
          <AppText variant="bodyStrong">Payment confirmation</AppText>
          <AppText variant="caption" color="tertiary">{data.job.job_reference}</AppText>
        </View>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Payment confirmation is read-only until you reconnect." /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete that action" message={mutationError.safeMessage} /></View> : null}

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginBottom: theme.spacing.base }}>
          <InlineAlert tone={data.prerequisites.completion_proof_submitted ? "success" : "neutral"} message="Completion proof submitted" />
        </View>

        <Section>
          <AmountDueCard amount={data.amount} />
        </Section>

        <InlineAlert tone="info" message="Customer pays the provider directly. ServiceOS does not collect this payment." />

        {!hasRecord ? (
          <Section>
            <AppText variant="title" style={{ marginTop: theme.spacing.base, marginBottom: theme.spacing.xs }}>Payment received by provider</AppText>
            <SegmentedControl options={METHOD_OPTIONS} value={method} onChange={setMethod} disabled={!canDeclare || offline} />
            <View style={{ height: theme.spacing.sm }} />
            {method !== "onsite_cash" ? (
              <TextField label="Transaction reference" value={reference} onChangeText={setReference} placeholder="Enter UPI/reference ID" editable={canDeclare && !offline} />
            ) : null}
            <View style={{ height: theme.spacing.sm }} />
            <Checkbox
              label={data.amount.expected_amount ? `I confirm the provider received ₹${data.amount.expected_amount} directly from the customer.` : "I confirm the provider received payment directly from the customer."}
              checked={confirmed}
              onChange={setConfirmed}
              disabled={!canDeclare || offline}
            />
          </Section>
        ) : (
          <Section>
            <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Customer confirmation</AppText>
            <Card>
              <AppText variant="bodyStrong">{STATUS_LABEL[data.provider_record!.status] ?? data.provider_record!.status}</AppText>
              <AppText variant="caption" color="tertiary">A confirmation request was sent in the ServiceOS app.</AppText>
              {canRemind ? (
                <View style={{ marginTop: theme.spacing.sm }}>
                  <SecondaryButton label="Send reminder" onPress={() => { void remindCustomer(); }} disabled={mutating || offline} />
                </View>
              ) : null}
            </Card>
          </Section>
        )}

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Final closure readiness</AppText>
          <Card padding="base">
            <ClosureReadinessList rows={readinessRows} />
          </Card>
        </Section>

        <InlineAlert tone="warning" message="Job completes only after all required confirmations pass." />
      </ScrollView>

      <View style={{ flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
        <View style={{ flex: 1 }}>
          <SecondaryButton label="Save draft" onPress={() => { void refetch(); }} fullWidth disabled={offline} />
        </View>
        <View style={{ flex: 1 }}>
          {!hasRecord ? (
            <PrimaryButton label="Submit payment record" onPress={handleDeclare} disabled={!canDeclare || !confirmed || offline} loading={mutating} fullWidth />
          ) : (
            <PrimaryButton label="Complete job" onPress={handleFinalize} disabled={!canFinalize || offline} loading={mutating} fullWidth />
          )}
        </View>
      </View>
    </SafeAreaScreen>
  );
}
