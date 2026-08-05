import React, { useState } from "react";
import { View, Modal, Pressable } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppInput } from "../../components/AppInput";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { Icon } from "../../components/Icon";
import { AcknowledgementCheckbox } from "../../components/privacy/AcknowledgementCheckbox";
import { usePrivacyRequestsQuery, useCreatePrivacyRequestMutation } from "../../api/privacyData/usePrivacyDataQueries";
import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../../api/idempotency/idempotencyStore";
import {
  CORRECTION_CATEGORIES, CorrectionCategoryPresentation, CORRECTION_FIELD_MAX_LENGTH,
  buildCorrectionReason,
} from "../../domain/correctionCategories";
import { PrivacyRequest } from "../../domain/privacyData";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { DomainError } from "../../domain/errors";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "DataCorrectionRequest">;

const OPEN_STATUSES = new Set(["submitted", "identity_verification_pending", "under_review", "approved", "processing"]);
const IDEMPOTENCY_SCOPE = "privacy-request-create:data_correction";

function hasActiveCorrection(requests: PrivacyRequest[]): PrivacyRequest | null {
  return requests.find(r => r.requestType === "data_correction" && OPEN_STATUSES.has(r.status)) ?? null;
}

/**
 * Opened from Privacy & Data -> "Correct my data". The real backend
 * (`app/engines/compliance/customer_router.py`, request_type=
 * data_correction) has only one text field (`reason`) -- no category, no
 * separate current/requested-value fields, no attachments. The category
 * selector below is a client-side routing aid only: `account_details` and
 * `address_information` already have a real, existing direct-edit screen
 * (Personal Details / Saved Addresses), so those hand off there instead
 * of creating an unnecessary formal request; everything else has no
 * direct-edit path and proceeds to the real correction mutation with the
 * category folded into the one `reason` field for reviewer context.
 */
export function DataCorrectionRequestScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const requestsQuery = usePrivacyRequestsQuery(1);
  const createMutation = useCreatePrivacyRequestMutation();
  const offline = isOffline();

  const [category, setCategory] = useState<CorrectionCategoryPresentation>(CORRECTION_CATEGORIES[0]);
  const [pickerVisible, setPickerVisible] = useState(false);
  const [whatIsIncorrect, setWhatIsIncorrect] = useState("");
  const [whatItShouldSay, setWhatItShouldSay] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (requestsQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Checking your correction requests…" />
      </AppScreen>
    );
  }

  const active = hasActiveCorrection(requestsQuery.data?.requests ?? []);

  const trimmedIncorrect = whatIsIncorrect.trim();
  const trimmedShouldSay = whatItShouldSay.trim();
  const formValid = trimmedIncorrect.length > 0 && trimmedShouldSay.length > 0;
  const canSubmit = formValid && acknowledged && !offline && !createMutation.isPending;

  async function handleSubmit() {
    if (!canSubmit) return;
    setError(null);
    try {
      const idempotencyKey = await getOrCreateIdempotencyKey(IDEMPOTENCY_SCOPE);
      const reason = buildCorrectionReason({
        categoryLabel: category.label, whatIsIncorrect: trimmedIncorrect, whatItShouldSay: trimmedShouldSay,
      });
      const res = await createMutation.mutateAsync({
        request_type: "data_correction", reason, confirm_understanding: true, idempotency_key: idempotencyKey,
      });
      await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
      navigation.replace("PrivacyRequestSubmitted", { requestId: res.data.request_id });
    } catch (err) {
      if (err instanceof DomainError) {
        const existingRequestId = err.telemetryMeta?.existingRequestId;
        if (typeof existingRequestId === "string") {
          await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
          navigation.replace("PrivacyRequestDetails", { requestId: existingRequestId });
          return;
        }
        if (err.category !== "NETWORK_UNAVAILABLE" && err.category !== "TIMEOUT" && err.category !== "BACKEND_UNAVAILABLE") {
          await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
        }
        setError(err.diagnostic);
      } else {
        setError("Couldn't submit your correction request.");
      }
    }
  }

  if (active) {
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          <Header onBack={() => navigation.goBack()} />
          <AppCard style={{ gap: theme.spacing.sm, alignItems: "center" }}>
            <Icon name="hourglass-outline" size="feature" color={theme.colors.textSecondary} decorative />
            <AppText variant="bodyStrong" align="center">You already have a correction request in progress</AppText>
            <AppText variant="bodySmall" color="secondary" align="center">{active.statusLabel}</AppText>
            <AppButton
              label="View request" tone="primary" fullWidth
              onPress={() => navigation.replace("PrivacyRequestDetails", { requestId: active.id })}
            />
          </AppCard>
        </View>
      </AppScreen>
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <Header onBack={() => navigation.goBack()} />

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <View
            style={{
              width: 56, height: 56, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
              backgroundColor: theme.colors.brandPrimaryMuted,
            }}
          >
            <Icon name="create-outline" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1 }}>
            <AppText variant="title">Tell us what needs correcting</AppText>
            <AppText variant="bodySmall" color="secondary">
              Describe the information that may be inaccurate and what it should say.
            </AppText>
          </View>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Information category</AppText>
          <Pressable
            onPress={() => setPickerVisible(true)}
            accessibilityRole="button" accessibilityLabel={`Information category: ${category.label}`}
            style={{
              minHeight: 44, flexDirection: "row", alignItems: "center", justifyContent: "space-between",
              borderWidth: 1, borderColor: theme.colors.borderDefault, borderRadius: theme.radiusUsage.input,
              paddingHorizontal: theme.spacing.base,
            }}
          >
            <AppText variant="body">{category.label}</AppText>
            <Icon name="chevron-down" size="compact" color={theme.colors.textSecondary} decorative />
          </Pressable>
        </View>

        {category.capability === "direct_edit" ? (
          <AppCard style={{ gap: theme.spacing.xs }}>
            <AppText variant="bodyStrong">This can be updated right away</AppText>
            <AppText variant="bodySmall" color="secondary">{category.description}</AppText>
            <AppButton
              label={category.directEditActionLabel ?? "Edit"} tone="primary" fullWidth
              onPress={() => navigation.navigate(category.directEditRoute as "EditProfile" | "SavedAddresses")}
            />
          </AppCard>
        ) : (
          <>
            <View style={{ gap: theme.spacing.xs }}>
              <AppInput
                label="What is incorrect?"
                placeholder="Describe the information you believe is inaccurate…"
                value={whatIsIncorrect}
                onChangeText={t => { setWhatIsIncorrect(t); setError(null); }}
                accessibilityLabel="What is incorrect?"
                multiline numberOfLines={4}
                maxLength={CORRECTION_FIELD_MAX_LENGTH}
                editable={!createMutation.isPending}
                style={{ minHeight: 96, textAlignVertical: "top", paddingTop: theme.spacing.sm }}
              />
              <AppText variant="caption" color="tertiary" align="right">
                {whatIsIncorrect.length} / {CORRECTION_FIELD_MAX_LENGTH}
              </AppText>
            </View>

            <View style={{ gap: theme.spacing.xs }}>
              <AppInput
                label="What should it say?"
                placeholder="Enter the corrected information…"
                value={whatItShouldSay}
                onChangeText={t => { setWhatItShouldSay(t); setError(null); }}
                accessibilityLabel="What should it say?"
                multiline numberOfLines={4}
                maxLength={CORRECTION_FIELD_MAX_LENGTH}
                editable={!createMutation.isPending}
                style={{ minHeight: 96, textAlignVertical: "top", paddingTop: theme.spacing.sm }}
              />
              <AppText variant="caption" color="tertiary" align="right">
                {whatItShouldSay.length} / {CORRECTION_FIELD_MAX_LENGTH}
              </AppText>
            </View>

            <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive }}>
              <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.textSecondary} decorative />
              <View style={{ flex: 1 }}>
                <AppText variant="bodyStrong">We'll review your request</AppText>
                <AppText variant="bodySmall" color="secondary">
                  Submitting a request does not change your account immediately. Track its status in Privacy requests.
                </AppText>
              </View>
            </View>

            <AcknowledgementCheckbox
              checked={acknowledged}
              onChange={setAcknowledged}
              label="I confirm the information I've provided is accurate."
            />

            {offline ? <AppText variant="bodySmall" color="secondary">Connect to the internet to submit this request.</AppText> : null}
            {error ? <AppText variant="bodySmall" color="danger" accessibilityLiveRegion="polite">{error}</AppText> : null}

            <View style={{ gap: theme.spacing.sm }}>
              <AppButton
                label="Submit correction request" tone="primary" onPress={handleSubmit}
                loading={createMutation.isPending} disabled={!canSubmit} fullWidth
              />
              <AppText
                variant="labelStrong" color="danger" align="center" onPress={createMutation.isPending ? undefined : () => navigation.goBack()}
                accessibilityRole="button" accessibilityLabel="Cancel"
              >
                Cancel
              </AppText>
            </View>
          </>
        )}
      </View>

      <Modal visible={pickerVisible} transparent animationType="fade" onRequestClose={() => setPickerVisible(false)}>
        <Pressable
          style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "flex-end" }}
          onPress={() => setPickerVisible(false)}
        >
          <Pressable
            style={{ backgroundColor: theme.colors.surfaceDefault, borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card, padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.xs }}
            onPress={e => e.stopPropagation()}
          >
            <AppText variant="labelStrong" color="secondary">Information category</AppText>
            {CORRECTION_CATEGORIES.map(c => (
              <Pressable
                key={c.code}
                onPress={() => { setCategory(c); setPickerVisible(false); }}
                accessibilityRole="button" accessibilityLabel={c.label}
                style={{ minHeight: 44, justifyContent: "center", paddingVertical: theme.spacing.sm }}
              >
                <AppText variant={c.code === category.code ? "bodyStrong" : "body"}>{c.label}</AppText>
                <AppText variant="caption" color="tertiary">{c.description}</AppText>
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </AppScreen>
  );
}

function Header({ onBack }: { onBack: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <AppText variant="headingSmall" accessibilityRole="header" style={{ flex: 1, textAlign: "center", marginRight: 44 }}>
        Correct my data
      </AppText>
    </View>
  );
}
