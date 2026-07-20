import React from "react";
import { View, ScrollView, Modal } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { AppTextArea } from "../../../components/forms/AppTextArea";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useQuoteDecision } from "../hooks/use-quote-decision";
import { useApproveQuote, useRejectQuote, useRequestQuoteRevision } from "../queries/quote-queries";
import { isQuoteActionable, quoteStatusTitleKey } from "../domain/quote-state";
import { toNumber } from "../domain/quote-schema";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";

type QuoteDecisionRouteProp = RouteProp<RootStackParamList, "QuoteDecision">;

function newIdempotencyKey(): string {
  return `qtapprv_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

/**
 * The real production additional-cost/decision screen (CUSTOMER-L5-14).
 * There is no real customer-facing "parts approval" endpoint anywhere in
 * this backend (`execution` engine's `PartsRequest` customer-decision
 * status is unreachable dead code) — the real, live capability this
 * screen implements is the separate `quote_checklist` engine's customer
 * quote-decision flow (approve / reject / request revision), the actual
 * mechanism by which a customer is asked to accept additional cost mid-job.
 * See CUSTOMER-L5-14-contract-matrix.md.
 */
export function QuoteDecisionScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<QuoteDecisionRouteProp>();
  const { bookingId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  React.useEffect(() => {
    logger.info("quote_decision_load_started", {});
  }, []);

  const { bookingQuery, jobId, listQuery, detailQuery } = useQuoteDecision(bookingId);
  const approveMutation = useApproveQuote(jobId ?? "none");
  const rejectMutation = useRejectQuote(jobId ?? "none");
  const revisionMutation = useRequestQuoteRevision(jobId ?? "none");
  const idempotencyKeyRef = React.useRef<string | null>(null);

  const [reasonModal, setReasonModal] = React.useState<"reject" | "revision" | null>(null);
  const [reasonText, setReasonText] = React.useState("");

  const header = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
      <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
        <AppIcon name="chevron-back" size="md" color="iconPrimary" />
      </AppPressable>
      <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
        {t("quoteDecision.title")}
      </AppText>
    </View>
  );

  const isLoading = bookingQuery.isPending || listQuery.isPending || (Boolean(listQuery.data?.length) && detailQuery.isPending);

  if (isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <Skeleton height={120} />
        </View>
      </SafeAreaView>
    );
  }

  if (bookingQuery.isError || listQuery.isError) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <ErrorState
            title={t("quoteDecision.loadErrorTitle")}
            description={t("quoteDecision.loadErrorDescription")}
            onRetry={() => {
              void bookingQuery.refetch();
              void listQuery.refetch();
            }}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (!listQuery.data || listQuery.data.length === 0) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <AppText variant="bodyMedium" color="textSecondary">
            {t("quoteDecision.noneYet")}
          </AppText>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const quote = detailQuery.data;
  if (!quote) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <ErrorState
            title={t("quoteDecision.loadErrorTitle")}
            description={t("quoteDecision.loadErrorDescription")}
            onRetry={() => void detailQuery.refetch()}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  const actionable = isQuoteActionable(quote);
  const isSubmitting = approveMutation.isPending || rejectMutation.isPending || revisionMutation.isPending;

  function handleApprove() {
    if (!idempotencyKeyRef.current) idempotencyKeyRef.current = newIdempotencyKey();
    approveMutation.mutate({ quoteId: quote!.id, idempotencyKey: idempotencyKeyRef.current });
  }

  function openReasonModal(kind: "reject" | "revision") {
    setReasonText("");
    setReasonModal(kind);
  }

  function submitReason() {
    const reason = reasonText.trim();
    if (!reason) return;
    if (reasonModal === "reject") rejectMutation.mutate({ quoteId: quote!.id, reason });
    else if (reasonModal === "revision") revisionMutation.mutate({ quoteId: quote!.id, reason });
    setReasonModal(null);
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        {header}

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="bodySmall" color="textTertiary">
            {quote.quote_number}
          </AppText>
          <AppText variant="titleLarge">{t(quoteStatusTitleKey(quote.status))}</AppText>
        </View>

        {quote.customer_visible_notes ? (
          <AppText variant="bodyMedium" color="textSecondary">
            {quote.customer_visible_notes}
          </AppText>
        ) : null}

        <View style={{ gap: theme.spacing[2] }}>
          <AppText variant="titleSmall">{t("quoteDecision.itemsTitle")}</AppText>
          {quote.items.length === 0 ? (
            <AppText variant="bodySmall" color="textSecondary">
              {t("quoteDecision.noItemsVisible")}
            </AppText>
          ) : (
            quote.items.map((item) => (
              <View key={item.id} style={{ flexDirection: "row", justifyContent: "space-between", gap: theme.spacing[3] }}>
                <View style={{ flex: 1 }}>
                  <AppText variant="bodyMedium">{item.item_name}</AppText>
                  <AppText variant="caption" color="textTertiary">
                    {String(item.quantity)} × {formatCurrency(toNumber(item.unit_price), locale, quote.currency)}
                  </AppText>
                </View>
                <AppText variant="bodyMedium">{formatCurrency(toNumber(item.line_total), locale, quote.currency)}</AppText>
              </View>
            ))
          )}
        </View>

        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            borderTopWidth: 1,
            borderColor: theme.colors.borderDefault,
            paddingTop: theme.spacing[3],
          }}
        >
          <AppText variant="titleSmall">{t("quoteDecision.totalLabel")}</AppText>
          <AppText variant="numericEmphasis">{formatCurrency(toNumber(quote.customer_payable_amount), locale, quote.currency)}</AppText>
        </View>

        {quote.rejection_reason ? (
          <AppText variant="bodySmall" color="textSecondary">
            {t("quoteDecision.rejectionReasonLabel")}: {quote.rejection_reason}
          </AppText>
        ) : null}
        {quote.revision_reason ? (
          <AppText variant="bodySmall" color="textSecondary">
            {t("quoteDecision.revisionReasonLabel")}: {quote.revision_reason}
          </AppText>
        ) : null}

        {actionable ? (
          <View style={{ gap: theme.spacing[3] }}>
            <AppButton
              label={t("quoteDecision.approve")}
              onPress={handleApprove}
              variant="primary"
              size="large"
              loading={approveMutation.isPending}
              disabled={isSubmitting}
              testID="quote-decision-approve-button"
            />
            <AppButton
              label={t("quoteDecision.requestRevision")}
              onPress={() => openReasonModal("revision")}
              variant="secondary"
              size="large"
              disabled={isSubmitting}
              testID="quote-decision-revision-button"
            />
            <AppButton
              label={t("quoteDecision.reject")}
              onPress={() => openReasonModal("reject")}
              variant="destructive"
              size="large"
              disabled={isSubmitting}
              testID="quote-decision-reject-button"
            />
          </View>
        ) : null}

        {approveMutation.isError || rejectMutation.isError || revisionMutation.isError ? (
          <AppText variant="bodySmall" color="textSecondary" accessibilityRole="alert">
            {t("quoteDecision.actionFailed")}
          </AppText>
        ) : null}
      </ScrollView>

      <Modal visible={reasonModal !== null} transparent animationType="fade" onRequestClose={() => setReasonModal(null)}>
        <View style={{ flex: 1, backgroundColor: theme.colors.scrim, alignItems: "center", justifyContent: "center", padding: theme.spacing[7] }}>
          <View
            style={{
              width: "100%",
              maxWidth: 360,
              backgroundColor: theme.colors.backgroundElevated,
              borderRadius: theme.radii.lg,
              padding: theme.spacing[7],
              gap: theme.spacing[4],
            }}
          >
            <AppText variant="headingSmall">{reasonModal === "reject" ? t("quoteDecision.rejectModalTitle") : t("quoteDecision.revisionModalTitle")}</AppText>
            <AppTextArea label={t("quoteDecision.reasonLabel")} value={reasonText} onChangeText={setReasonText} required />
            <View style={{ flexDirection: "row", justifyContent: "flex-end", gap: theme.spacing[3] }}>
              <AppButton label={t("quoteDecision.cancel")} onPress={() => setReasonModal(null)} variant="text" size="medium" />
              <AppButton
                label={t("quoteDecision.submit")}
                onPress={submitReason}
                variant={reasonModal === "reject" ? "destructive" : "primary"}
                size="medium"
                disabled={reasonText.trim().length === 0}
              />
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}
