import React, { useEffect, useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppButton } from "../../components/AppButton";
import { AppInput } from "../../components/AppInput";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { useCustomerBookingsListQuery } from "../../api/customerBookings/useCustomerBookingsListQuery";
import { resolveSupportCategoryPresentation } from "../../domain/supportCategoryPresentation";
import {
  isSupportRequestDraftDirty, validateSupportRequestDetails, SUPPORT_REQUEST_TITLE_MAX_LENGTH,
} from "../../domain/supportRequestDraft";
import { useSupportRequestWizard } from "./SupportRequestWizardContext";
import { SupportRequestWizardParamList } from "../../navigation/supportRequestWizardTypes";

type Nav = NativeStackNavigationProp<SupportRequestWizardParamList, "Details">;

const STEPS = ["Topic", "Details", "Review"] as const;

/**
 * Step 2 of 3 -- title/description only. No attachment section is
 * rendered: the audit confirmed `ComplaintMedia`/`upload_complaint_media`
 * exists server-side but is never wired to any customer (or even
 * provider/admin) route -- a local-only picker that could never actually
 * submit a file would be dishonest, so the capability is hidden entirely
 * rather than half-built (spec section 8, Outcome C). No "Save and exit"
 * either -- no authenticated support-draft endpoint exists. No mutation
 * happens on this screen; "Continue to review" only advances the shared
 * wizard draft.
 */
export function CreateSupportRequestDetailsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const { draft, setDraft } = useSupportRequestWizard();
  const bookingsQuery = useCustomerBookingsListQuery("all");

  const [touchedTitle, setTouchedTitle] = useState(false);
  const [touchedDescription, setTouchedDescription] = useState(false);

  const presentation = draft.categoryCode ? resolveSupportCategoryPresentation(draft.categoryCode) : null;
  const linkedBooking = draft.bookingId ? bookingsQuery.items.find(b => b.bookingId === draft.bookingId) ?? null : null;

  useEffect(() => {
    // Missing/invalid Step 1 context (e.g. deep-linked directly, or a
    // fast-refresh loss of context) -- never render an incomplete form,
    // go back to Topic instead of guessing a placeholder topic (spec
    // section 2).
    if (!presentation) {
      navigation.goBack();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presentation]);

  if (!presentation) {
    return <AppScreen />;
  }

  const validation = validateSupportRequestDetails(draft.subject, draft.description);
  const canContinue = validation.isValid;

  function confirmDiscard(onDiscard: () => void) {
    Alert.alert("Discard this request?", "Your entered details will be removed.", [
      { text: "Keep editing", style: "cancel" },
      { text: "Discard", style: "destructive", onPress: onDiscard },
    ]);
  }

  function handleExit() {
    if (isSupportRequestDraftDirty(draft)) {
      confirmDiscard(() => navigation.getParent()?.goBack());
    } else {
      navigation.getParent()?.goBack();
    }
  }

  function handleContinue() {
    setTouchedTitle(true);
    setTouchedDescription(true);
    if (!validation.isValid) return;
    navigation.navigate("Review");
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">Create request</AppText>
            <AppText variant="bodySmall" color="secondary">Share the details clearly</AppText>
          </View>
        </View>

        <AppCard style={{ gap: theme.spacing.xs }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <AppText variant="labelStrong">Step 2 of 3</AppText>
            <AppText variant="bodySmall" color="secondary">Request details</AppText>
          </View>
          <View
            accessibilityRole="progressbar" accessibilityLabel="Step 2 of 3: Request details"
            style={{ height: 4, borderRadius: 2, backgroundColor: theme.colors.surfaceInteractive, overflow: "hidden" }}
          >
            <View style={{ width: "66%", height: "100%", backgroundColor: theme.colors.brandPrimary }} />
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            {STEPS.map((label, i) => (
              <AppText key={label} variant="caption" color={i === 1 ? "primary" : "tertiary"}>{label}</AppText>
            ))}
          </View>
        </AppCard>

        <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <Icon name={presentation.icon} size="feature" color={theme.colors.textSecondary} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">{presentation.label}</AppText>
            {linkedBooking ? (
              <AppText variant="caption" color="secondary">
                {linkedBooking.serviceName ?? "Service"}{linkedBooking.bookingNumber ? ` · Booking ${linkedBooking.bookingNumber}` : ""}
              </AppText>
            ) : null}
          </View>
          <AppButton label="Edit" tone="secondary" size="compact" onPress={() => navigation.goBack()} />
        </AppCard>

        <View>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <AppText variant="label" color="secondary">Brief title</AppText>
            <AppText variant="caption" color="tertiary">Optional</AppText>
          </View>
          <AppInput
            value={draft.subject}
            onChangeText={t => setDraft(d => ({ ...d, subject: t }))}
            onBlur={() => setTouchedTitle(true)}
            accessibilityLabel="Brief title"
            placeholder="Need help with my AC booking"
            maxLength={SUPPORT_REQUEST_TITLE_MAX_LENGTH}
            error={touchedTitle ? validation.titleError ?? undefined : undefined}
          />
          <AppText variant="caption" color="tertiary" align="right">{draft.subject.length} / {SUPPORT_REQUEST_TITLE_MAX_LENGTH}</AppText>
        </View>

        <View>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <AppText variant="label" color="secondary">Tell us what happened</AppText>
            <AppText variant="caption" color="tertiary">Required</AppText>
          </View>
          <AppInput
            value={draft.description}
            onChangeText={t => setDraft(d => ({ ...d, description: t }))}
            onBlur={() => setTouchedDescription(true)}
            accessibilityLabel="Tell us what happened"
            multiline
            style={{ minHeight: 96, textAlignVertical: "top", paddingTop: theme.spacing.sm }}
            error={touchedDescription ? validation.descriptionError ?? undefined : undefined}
          />
          <AppText variant="caption" color="tertiary">Include the most useful details.</AppText>
        </View>

        <AppCard style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <Icon name="shield-outline" size="standard" color={theme.colors.textSecondary} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">Protect your information</AppText>
            <AppText variant="bodySmall" color="secondary">Do not include passwords, OTPs or payment-card details.</AppText>
          </View>
        </AppCard>

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton label="Continue to review" tone="primary" onPress={handleContinue} disabled={!canContinue} fullWidth />
          <AppButton label="Cancel" tone="tertiary" onPress={handleExit} fullWidth />
        </View>
      </View>
    </AppScreen>
  );
}
