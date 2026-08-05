import React, { useEffect, useRef, useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppButton } from "../../components/AppButton";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { OfflineBanner } from "../../components/OfflineBanner";
import { useCustomerBookingsListQuery } from "../../api/customerBookings/useCustomerBookingsListQuery";
import { useCreateSupportRequestMutation } from "../../api/supportRequests/useSupportRequestsQueries";
import { resolveSupportCategoryPresentation } from "../../domain/supportCategoryPresentation";
import { buildCreateSupportRequestPayload, isSupportRequestDraftDirty } from "../../domain/supportRequestDraft";
import { useSupportRequestWizard } from "./SupportRequestWizardContext";
import { SupportRequestWizardParamList } from "../../navigation/supportRequestWizardTypes";
import { isOffline } from "../../api/networkState";
import { DomainError } from "../../domain/errors";

type Nav = NativeStackNavigationProp<SupportRequestWizardParamList, "Review">;
type ParentNav = { replace: (name: string, params?: object) => void; goBack: () => void; navigate: (name: string, params?: object) => void };

const STEPS = ["Topic", "Details", "Review"] as const;

/** Categories that mean "we genuinely don't know if this was created" --
 * only these get the honest unknown-result copy (spec section 8). A
 * clear validation/auth/conflict/rate-limit response is a definitive
 * result, not an unknown one. */
const UNCERTAIN_CATEGORIES = new Set(["NETWORK_UNAVAILABLE", "TIMEOUT", "BACKEND_UNAVAILABLE"]);

/**
 * Step 3 of 3 -- review + the one real mutation in this wizard
 * (`POST /v1/customer/complaints`). No attachments section is rendered
 * (same Outcome-C finding as Step 2: no customer attachment route
 * exists anywhere). No "Save & exit" either -- no draft endpoint exists
 * (spec's own fallback instruction, already applied consistently since
 * Step 2). A booking link is mandatory here even though Step 1 labeled
 * it "Optional" -- the real backend requires `record_id` on every
 * create call; Step 3 is where that real constraint is finally
 * enforced, honestly, rather than silently failing at submit time.
 */
export function CreateSupportRequestReviewScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const parentNavigation = navigation.getParent() as unknown as ParentNav | undefined;
  const { draft, resetDraft } = useSupportRequestWizard();
  const bookingsQuery = useCustomerBookingsListQuery("all");
  const createMutation = useCreateSupportRequestMutation();
  const offline = isOffline();

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uncertainOutcome, setUncertainOutcome] = useState(false);
  // Guards against a second mutation firing from a double tap, a
  // re-render, or a stray focus event while the first call is still in
  // flight -- the real backend has no idempotency-key contract for this
  // route (confirmed during the audit: the global `IdempotencyMiddleware`
  // in `app/core/idempotency.py` is never registered in `app/main.py`,
  // and even if it were, it reads `X-Idempotency-Key` while this app's
  // client sends `Idempotency-Key`). This ref only prevents a second tap
  // from this screen instance; it is not a substitute for real
  // server-side idempotency, and is disclosed as a gap in the final
  // report rather than presented as equivalent protection.
  const submissionInFlight = useRef(false);

  const presentation = draft.categoryCode ? resolveSupportCategoryPresentation(draft.categoryCode) : null;
  const linkedBooking = draft.bookingId ? bookingsQuery.items.find(b => b.bookingId === draft.bookingId) ?? null : null;

  useEffect(() => {
    // Missing/invalid Step 1 or Step 2 context -- never render an
    // incomplete review, go back rather than guessing (spec section 5).
    if (!presentation || !draft.description.trim()) {
      navigation.goBack();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presentation, draft.description]);

  if (!presentation) {
    return <AppScreen />;
  }

  // The booking picker in Step 1 presented linking as "Optional," but the
  // real backend requires `record_id` on every create call -- enforced
  // here rather than silently failing at submit.
  const missingRequiredBooking = presentation.bookingApplicable && !draft.bookingId;
  const bookingNoLongerAvailable = !!draft.bookingId && !bookingsQuery.isPending && !linkedBooking;
  const canSubmit = !missingRequiredBooking && !bookingNoLongerAvailable && !offline && !createMutation.isPending;

  async function handleSubmit() {
    if (submissionInFlight.current || !canSubmit) return;
    submissionInFlight.current = true;
    setSubmitError(null);
    setUncertainOutcome(false);
    try {
      const payload = buildCreateSupportRequestPayload(draft, presentation!.submissionComplaintType ?? "other");
      const res = await createMutation.mutateAsync(payload);
      resetDraft();
      parentNavigation?.replace("SupportRequestDetails", { requestId: res.data.id });
    } catch (err) {
      if (err instanceof DomainError && UNCERTAIN_CATEGORIES.has(err.category)) {
        setUncertainOutcome(true);
        setSubmitError("We couldn't confirm whether your request was submitted. Check My support requests before trying again.");
      } else {
        setSubmitError(err instanceof DomainError ? err.diagnostic : "Couldn't submit your request.");
      }
    } finally {
      submissionInFlight.current = false;
    }
  }

  function handleBackToEdit() {
    navigation.goBack();
  }

  function handleExit() {
    if (isSupportRequestDraftDirty(draft)) {
      Alert.alert("Discard this request?", "Your entered details will be removed.", [
        { text: "Keep editing", style: "cancel" },
        { text: "Discard", style: "destructive", onPress: () => { resetDraft(); parentNavigation?.goBack(); } },
      ]);
    } else {
      parentNavigation?.goBack();
    }
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={handleBackToEdit} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">Create request</AppText>
          </View>
        </View>

        <View>
          <AppText variant="title">Review before submitting</AppText>
          <AppText variant="bodySmall" color="secondary">Make sure everything looks right.</AppText>
        </View>

        {offline ? <OfflineBanner /> : null}

        <AppCard style={{ gap: theme.spacing.xs }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <AppText variant="labelStrong">Step 3 of 3</AppText>
            <AppText variant="bodySmall" color="secondary">Review & submit</AppText>
          </View>
          <View
            accessibilityRole="progressbar" accessibilityLabel="Step 3 of 3: Review & submit"
            style={{ height: 4, borderRadius: 2, backgroundColor: theme.colors.surfaceInteractive, overflow: "hidden" }}
          >
            <View style={{ width: "100%", height: "100%", backgroundColor: theme.colors.brandPrimary }} />
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            {STEPS.map((label, i) => (
              <AppText key={label} variant="caption" color={i === 2 ? "primary" : "tertiary"}>
                {label}{i < 2 ? " ✓" : ""}
              </AppText>
            ))}
          </View>
        </AppCard>

        <AppCard style={{ gap: theme.spacing.xs }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
            <AppText variant="labelStrong">Topic & booking</AppText>
            <AppText variant="labelStrong" color="link" onPress={() => navigation.navigate("Topic")} accessibilityRole="button" accessibilityLabel="Edit topic and booking">Edit</AppText>
          </View>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "center" }}>
            <Icon name={presentation.icon} size="feature" color={theme.colors.textSecondary} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{presentation.label}</AppText>
              {linkedBooking ? (
                <AppText variant="caption" color="secondary">
                  {linkedBooking.serviceName ?? "Service"}{linkedBooking.bookingNumber ? ` · Booking ${linkedBooking.bookingNumber}` : ""}
                </AppText>
              ) : null}
            </View>
          </View>
          {missingRequiredBooking ? (
            <AppText variant="bodySmall" color="danger">A booking is required to submit this request.</AppText>
          ) : null}
          {bookingNoLongerAvailable ? (
            <AppText variant="bodySmall" color="danger">This booking is no longer available. Choose another.</AppText>
          ) : null}
        </AppCard>

        <AppCard style={{ gap: theme.spacing.xs }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
            <AppText variant="labelStrong">Request details</AppText>
            <AppText variant="labelStrong" color="link" onPress={() => navigation.navigate("Details")} accessibilityRole="button" accessibilityLabel="Edit request details">Edit</AppText>
          </View>
          {draft.subject.trim() ? <AppText variant="bodyStrong">{draft.subject.trim()}</AppText> : null}
          <AppText variant="bodySmall" color="secondary">{draft.description}</AppText>
        </AppCard>

        <AppCard style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <Icon name="checkmark-circle-outline" size="standard" color={theme.colors.textSecondary} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">Before you submit</AppText>
            <AppText variant="bodySmall" color="secondary">You can follow updates from My support requests.</AppText>
          </View>
        </AppCard>

        {submitError ? (
          <AppText variant="bodySmall" color="danger" accessibilityLiveRegion="polite">{submitError}</AppText>
        ) : null}
        {uncertainOutcome ? (
          <AppButton
            label="Check My support requests" tone="secondary"
            onPress={() => parentNavigation?.replace("SupportRequests")}
            fullWidth
          />
        ) : null}

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton
            label={createMutation.isPending ? "Submitting…" : "Submit request"} tone="primary"
            onPress={handleSubmit} disabled={!canSubmit || createMutation.isPending} fullWidth
          />
          <AppButton label="Back to edit" tone="tertiary" onPress={handleBackToEdit} disabled={createMutation.isPending} fullWidth />
          <AppText
            variant="labelStrong" color="danger" align="center" onPress={createMutation.isPending ? undefined : handleExit}
            accessibilityRole="button" accessibilityLabel="Cancel and discard this request"
          >
            Cancel
          </AppText>
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" align="center">Your request is linked to your Fuvay account.</AppText>
        </View>
      </View>
    </AppScreen>
  );
}
