import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, View } from "react-native";
import { RouteProp, useNavigation, useRoute } from "@react-navigation/native";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppIconButton } from "../../components/AppIconButton";
import { AppInput } from "../../components/AppInput";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { ErrorState } from "../../components/States";
import { LoadingState } from "../../components/LoadingState";
import { useTheme } from "../../design-system/theme";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useCustomerBookingDetailsQuery } from "../../api/customerBookings/useCustomerBookingDetailsQuery";
import {
  escalateRefundRequest, escalateWarrantyClaim, listMyRefundRequests, listMyWarrantyClaims,
  submitRefundRequest, submitWarrantyClaim,
} from "../../api/customerRemedies/customerRemediesApi";
import { RefundRequest, WarrantyClaim } from "../../api/contracts/customerRemedies";

type Route = RouteProp<CustomerAppStackParamList, "ServiceRemedies">;
type Mode = "warranty" | "refund";

export function ServiceRemediesScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const { bookingId, mode: initialMode } = useRoute<Route>().params;
  const booking = useCustomerBookingDetailsQuery(bookingId);
  const [mode, setMode] = useState<Mode>(initialMode);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [claim, setClaim] = useState<WarrantyClaim | null>(null);
  const [refund, setRefund] = useState<RefundRequest | null>(null);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const details = booking.data?.kind === "found" ? booking.data.details : null;
  const jobId = details?.job?.jobId ?? "";

  const refreshRecords = useCallback(async () => {
    if (!jobId) return;
    setLoadingRecords(true);
    try {
      const [claims, refunds] = await Promise.all([listMyWarrantyClaims(), listMyRefundRequests()]);
      setClaim(claims.data.claims.find(item => item.job_id === jobId) ?? null);
      setRefund(refunds.data.find(item => item.job_id === jobId || item.booking_id === bookingId) ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load protection requests.");
    } finally {
      setLoadingRecords(false);
    }
  }, [bookingId, jobId]);

  useEffect(() => { void refreshRecords(); }, [refreshRecords]);
  useEffect(() => {
    const collected = details?.job?.completion?.collectedAmount;
    if (collected && !amount) setAmount(String(collected));
  }, [amount, details?.job?.completion?.collectedAmount]);

  const activeRecord = mode === "warranty" ? claim : refund;
  const deadline = activeRecord?.provider_response_due_at ? new Date(activeRecord.provider_response_due_at) : null;
  const canEscalate = !!activeRecord && (
    ("provider_resolution" in activeRecord && !!activeRecord.provider_resolution)
    || (!!deadline && deadline.getTime() <= Date.now())
    || activeRecord.status === "rejected"
  );
  const descriptionValid = description.trim().length >= 20;
  const parsedAmount = Number(amount);
  const canSubmit = descriptionValid && (mode === "warranty" || (Number.isFinite(parsedAmount) && parsedAmount > 0));
  const warrantyUnavailable = mode === "warranty" && !details?.job?.warrantyActive;

  const statusCopy = useMemo(() => {
    if (!activeRecord) return null;
    if (activeRecord.status === "provider_action_required" || activeRecord.status === "requested") return "Waiting for provider response";
    if (activeRecord.status === "provider_in_progress" || activeRecord.status === "provider_review") return "Provider is working on this";
    if (activeRecord.status === "admin_review") return "Returned to provider for review";
    if (activeRecord.status === "credit_issued" || activeRecord.status === "verified") return "Service points issued / resolution verified";
    return activeRecord.status.replace(/_/g, " ");
  }, [activeRecord]);

  async function submit() {
    if (!jobId || !canSubmit || warrantyUnavailable) return;
    setBusy(true); setError(null);
    try {
      if (mode === "warranty") await submitWarrantyClaim(jobId, description.trim(), parsedAmount > 0 ? parsedAmount : undefined);
      else await submitRefundRequest(jobId, description.trim(), parsedAmount);
      setDescription("");
      await refreshRecords();
      Alert.alert("Request sent", "Your provider has been notified and has 24 hours to respond.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to send your request.");
    } finally { setBusy(false); }
  }

  async function escalate() {
    if (!activeRecord) return;
    setBusy(true); setError(null);
    const reason = description.trim() || "The provider has not resolved this service issue.";
    try {
      if (mode === "warranty" && claim) await escalateWarrantyClaim(claim.claim_id, reason);
      if (mode === "refund" && refund) await escalateRefundRequest(refund.id, reason);
      await refreshRecords();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to ask the provider to review this request again.");
    } finally { setBusy(false); }
  }

  if (booking.isPending) return <AppScreen><LoadingState label="Loading service protection" /></AppScreen>;
  if (!details?.job) return <AppScreen><ErrorState title="Service record unavailable" message="This booking has no completed job record." actionLabel="Go back" onAction={() => navigation.goBack()} /></AppScreen>;

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}><AppText variant="headingSmall">Service protection</AppText><AppText variant="bodySmall" color="secondary">Provider-owned refund and warranty support</AppText></View>
        </View>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
          <AppButton label="Warranty" tone={mode === "warranty" ? "primary" : "secondary"} onPress={() => setMode("warranty")} />
          <AppButton label="Refund" tone={mode === "refund" ? "primary" : "secondary"} onPress={() => setMode("refund")} />
        </View>
        <AppCard style={{ gap: theme.spacing.xs }}>
          <AppText variant="bodyStrong">{details.service.name ?? "Completed service"}</AppText>
          <AppText variant="bodySmall" color="secondary">
            Warranty: {details.job.warrantyDays ?? 5} days{details.job.warrantyExpiresAt ? ` · until ${new Date(details.job.warrantyExpiresAt).toLocaleDateString()}` : ""}
          </AppText>
          <AppText variant="caption" color="tertiary">The provider reviews the issue and works directly with you on rework, refund, credit, or another mutually agreed resolution.</AppText>
        </AppCard>
        {loadingRecords ? <LoadingState label="Checking existing requests" /> : activeRecord ? (
          <AppCard style={{ gap: theme.spacing.sm }}>
            <AppText variant="bodyStrong">{statusCopy}</AppText>
            {deadline ? <AppText variant="bodySmall" color="secondary">Provider response due {deadline.toLocaleString()}</AppText> : null}
            {"provider_resolution" in activeRecord && typeof activeRecord.provider_resolution === "string" ? <AppText variant="bodySmall">{activeRecord.provider_resolution}</AppText> : null}
            {canEscalate ? <AppButton label="Ask provider to review again" tone="secondary" onPress={escalate} loading={busy} fullWidth /> : null}
          </AppCard>
        ) : (
          <AppCard style={{ gap: theme.spacing.sm }}>
            {warrantyUnavailable ? <AppText variant="bodySmall" color="danger">The provider warranty period has expired.</AppText> : null}
            <AppInput label="What went wrong?" value={description} onChangeText={setDescription} multiline maxLength={2000} style={{ minHeight: 104, textAlignVertical: "top" }} />
            <AppInput label={mode === "refund" ? "Requested amount" : "Requested settlement amount (optional)"} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />
            <AppButton label={mode === "warranty" ? "Send warranty claim" : "Send refund request"} onPress={submit} loading={busy} disabled={!canSubmit || warrantyUnavailable} fullWidth />
          </AppCard>
        )}
        {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}
      </View>
    </AppScreen>
  );
}
