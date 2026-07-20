import React, { useEffect, useRef, useState } from "react";
import { View, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { ConfirmationModal } from "../../../components/feedback/ConfirmationModal";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useAuthSession } from "../../auth/hooks/use-auth-session";
import { useBookingDraft } from "../hooks/use-booking-draft";
import { useUpdateDraft, useCancelDraft } from "../queries/draft-queries";
import { clearActiveDraftId } from "../state/draft-local-store";
import { isTerminalDraftStatus } from "../domain/draft-schema";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { BookingDraftId } from "../../../navigation/route-params";

type BookingDraftRouteProp = RouteProp<RootStackParamList, "BookingDraft">;

/**
 * The real production booking-draft screen (CUSTOMER-L5-06). Creates or
 * restores a real, backend-authoritative draft — see
 * CUSTOMER-L5-06-draft-architecture.md. A draft is never presented as a
 * confirmed booking (CUSTOMER-L5-06 §53).
 */
export function BookingDraftScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BookingDraftRouteProp>();
  const { serviceId, categoryId, brandId, offeringTypeId, issueSummary } = route.params;
  const { session } = useAuthSession();
  const [discardConfirmVisible, setDiscardConfirmVisible] = useState(false);

  const bookingDraft = useBookingDraft({ customerId: session?.userId, categorySlug: categoryId, offeringSlug: serviceId });
  const updateDraft = useUpdateDraft();
  const cancelDraft = useCancelDraft();
  const syncedAnswersRef = useRef(false);

  useEffect(() => {
    if (!bookingDraft.draftId || !bookingDraft.draft || syncedAnswersRef.current) return;
    const payload: Record<string, unknown> = {};
    if (brandId && !bookingDraft.draft.brand_id) payload.brand_id = brandId;
    if (offeringTypeId && !bookingDraft.draft.offering_type_id) payload.offering_type_id = offeringTypeId;
    if (issueSummary && !bookingDraft.draft.issue_summary) payload.issue_summary = issueSummary;

    if (Object.keys(payload).length > 0) {
      syncedAnswersRef.current = true;
      updateDraft.mutate({ draftId: bookingDraft.draftId, payload });
    } else {
      syncedAnswersRef.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once per resolved draft; must not re-fire on every draft refetch.
  }, [bookingDraft.draftId, bookingDraft.draft]);

  if (bookingDraft.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="60%" />
          <Skeleton height={120} />
        </View>
      </SafeAreaView>
    );
  }

  if (bookingDraft.isError || !bookingDraft.draft) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState
            title={t("draft.serviceUnavailableTitle")}
            description={t("draft.serviceUnavailableDescription")}
            onContactSupport={() => navigation.navigate("ServiceDetails", { serviceId, categoryId })}
          />
        </View>
      </SafeAreaView>
    );
  }

  const draft = bookingDraft.draft;

  if (draft.status === "expired") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState
            title={t("draft.expiredTitle")}
            description={t("draft.expiredDescription")}
            onRetry={async () => {
              if (session?.userId) await clearActiveDraftId(session.userId);
              navigation.navigate("ServiceDetails", { serviceId, categoryId });
            }}
          />
        </View>
      </SafeAreaView>
    );
  }

  if (draft.status === "cancelled") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState
            title={t("draft.cancelledTitle")}
            onRetry={async () => {
              if (session?.userId) await clearActiveDraftId(session.userId);
              navigation.navigate("ServiceDetails", { serviceId, categoryId });
            }}
          />
        </View>
      </SafeAreaView>
    );
  }

  const canMutate = !isTerminalDraftStatus(draft.status);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.navigate("ServiceDetails", { serviceId, categoryId })}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {t("draft.title")}
          </AppText>
        </View>

        <AppText variant="caption" color="textTertiary">
          {t("draft.notASavedBooking")}
        </AppText>

        <View style={{ gap: theme.spacing[2] }}>
          <AppText variant="titleLarge">{draft.offering_name ?? draft.category_name ?? ""}</AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {updateDraft.isPending ? t("draft.saving") : updateDraft.isError ? t("draft.saveFailed") : t("draft.saved")}
          </AppText>
        </View>

        {draft.issue_summary ? (
          <View>
            <AppText variant="titleSmall" color="textSecondary" style={{ textTransform: "uppercase" }}>
              {t("draft.summaryHeading")}
            </AppText>
            <AppText variant="bodyMedium">{draft.issue_summary}</AppText>
          </View>
        ) : null}

        <AppText variant="bodySmall" color="textSecondary">
          {draft.photo_urls.length} photo(s) added
        </AppText>

        <View style={{ flex: 1 }} />

        <AppButton
          label={t("draft.continueToMedia")}
          onPress={() => navigation.navigate("BookingMedia", { draftId: draft.id as BookingDraftId })}
          variant="primary"
          size="large"
          disabled={!canMutate}
          testID="draft-continue-button"
        />
        <AppButton label={t("draft.discardTitle")} onPress={() => setDiscardConfirmVisible(true)} variant="text" size="medium" disabled={!canMutate} />
      </ScrollView>

      <ConfirmationModal
        visible={discardConfirmVisible}
        title={t("draft.discardTitle")}
        description={t("draft.discardDescription")}
        confirmLabel={t("draft.discardConfirm")}
        cancelLabel={t("draft.discardCancel")}
        destructive
        onConfirm={async () => {
          setDiscardConfirmVisible(false);
          try {
            await cancelDraft.mutateAsync({ draftId: draft.id });
          } catch (err) {
            logger.warn("draft_cancel_failed", { category: err instanceof ApiError ? err.category : "unknown" });
          }
          if (session?.userId) await clearActiveDraftId(session.userId);
          navigation.navigate("ServiceDetails", { serviceId, categoryId });
        }}
        onCancel={() => setDiscardConfirmVisible(false)}
      />
    </SafeAreaView>
  );
}
