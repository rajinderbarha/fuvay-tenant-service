import React, { useState } from "react";
import { View } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppInput } from "../../components/AppInput";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { AcknowledgementCheckbox } from "../../components/privacy/AcknowledgementCheckbox";
import { useCreatePrivacyRequestMutation } from "../../api/privacyData/usePrivacyDataQueries";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../../api/idempotency/idempotencyStore";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { DomainError } from "../../domain/errors";

type Route = RouteProp<CustomerAppStackParamList, "DeleteAccountFinalConfirmation">;
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "DeleteAccountFinalConfirmation">;

const IDEMPOTENCY_SCOPE = "privacy-request-create:right_to_erasure";

/**
 * Real identity verification for `right_to_erasure` is current-password
 * confirmation, validated server-side (`verify_password`) in the SAME
 * call that creates the request (`app/engines/compliance/
 * customer_router.py::create_my_request`) -- there is no separate
 * challenge/proof-issuance endpoint, so there is no opaque proof token to
 * carry in flow state (spec section 3's "narrowly scoped flow store"
 * collapses to nothing extra here). This screen therefore collects the
 * password directly and submits it, `reason` (carried forward from the
 * Review step), `confirm_understanding` and a fresh idempotency key in
 * one real, atomic request. The approved design shows a pre-verified
 * "Identity verified" state with no password field -- that assumes a
 * separate verification step this backend does not have. Rather than
 * fabricate a fake "already verified" claim, this screen honestly asks
 * for the password here and only shows success after the real backend
 * call confirms it (disclosed deviation).
 */
export function DeleteAccountFinalConfirmationScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { reason } = route.params;
  const createMutation = useCreatePrivacyRequestMutation();
  const profileQuery = useCustomerProfileQuery();

  const [password, setPassword] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const offline = isOffline();

  const profile = profileQuery.data;
  const displayName = profile?.displayName ?? profile?.fullName ?? "";

  const canSubmit = acknowledged && !!password && !offline && !createMutation.isPending;

  async function handleSubmit() {
    if (!canSubmit) return;
    setError(null);
    try {
      const idempotencyKey = await getOrCreateIdempotencyKey(IDEMPOTENCY_SCOPE);
      const res = await createMutation.mutateAsync({
        request_type: "right_to_erasure", reason, confirm_understanding: true,
        idempotency_key: idempotencyKey, password,
      });
      await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
      setPassword("");
      navigation.replace("PrivacyRequestSubmitted", { requestId: res.data.request_id });
    } catch (err) {
      if (err instanceof DomainError) {
        const existingRequestId = err.telemetryMeta?.existingRequestId;
        if (typeof existingRequestId === "string") {
          await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
          setPassword("");
          navigation.replace("PrivacyRequestDetails", { requestId: existingRequestId });
          return;
        }
        if (err.telemetryMeta?.backendCode === "INVALID_PASSWORD") {
          // A wrong password never invalidates the idempotency key --
          // no request was created, so the same key is safe to reuse for
          // the next real attempt (spec section 9: proof reuse policy).
          setPassword("");
          setError(err.diagnostic);
          return;
        }
        if (err.category !== "NETWORK_UNAVAILABLE" && err.category !== "TIMEOUT" && err.category !== "BACKEND_UNAVAILABLE") {
          await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
        }
        setError(err.diagnostic);
      } else {
        setError("Couldn't submit your deletion request.");
      }
    }
  }

  function handleKeepAccount() {
    setPassword("");
    setAcknowledged(false);
    navigation.goBack();
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <Header onBack={() => navigation.goBack()} />

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive }}>
          <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.statusSuccess} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">Confirm your password</AppText>
            <AppText variant="bodySmall" color="secondary">Enter your current password to verify it's you before submitting.</AppText>
          </View>
        </View>

        <AppInput
          label="Password"
          value={password}
          onChangeText={t => { setPassword(t); setError(null); }}
          accessibilityLabel="Password"
          secureTextEntry
          editable={!createMutation.isPending}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.statusDangerSurface, borderWidth: 1, borderColor: theme.colors.statusDanger }}>
          <Icon name="person-remove-outline" size="standard" color={theme.colors.statusDanger} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong" style={{ color: theme.colors.statusDanger }}>Submit deletion request?</AppText>
            <AppText variant="caption" color="secondary">Your account will not be deleted immediately. This request must be reviewed and processed.</AppText>
          </View>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Request summary</AppText>
          <AppCard style={{ gap: 0 }}>
            <SummaryRow icon="person-outline" label="Request type" value="Account deletion" />
            <SummaryRow icon="person-outline" label="Account" value={displayName || "Your account"} />
            <SummaryRow icon="checkmark-circle-outline" label="Current access" value="Remains active during review" last />
          </AppCard>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">After you submit</AppText>
          <AppCard style={{ gap: theme.spacing.sm }}>
            <SimpleRow icon="document-text-outline" label="A deletion request is created" />
            <SimpleRow icon="time-outline" label="Track its status in Privacy requests" />
            <SimpleRow icon="lock-closed-outline" label="Your account stays active unless its status changes" />
          </AppCard>
        </View>

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.statusDangerSurface, borderWidth: 1, borderColor: theme.colors.statusDanger }}>
          <Icon name="warning-outline" size="standard" color={theme.colors.statusDanger} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong" style={{ color: theme.colors.statusDanger }}>This action submits a request</AppText>
            <AppText variant="caption" color="secondary">It does not immediately delete your account or sign you out.</AppText>
          </View>
        </View>

        <AcknowledgementCheckbox
          checked={acknowledged}
          onChange={setAcknowledged}
          label="I understand and want to submit this deletion request."
        />

        {error ? <AppText variant="bodySmall" color="danger" accessibilityLiveRegion="polite">{error}</AppText> : null}
        {offline ? <AppText variant="bodySmall" color="secondary">Connect to the internet to submit this request.</AppText> : null}

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton
            label="Submit deletion request" tone="destructive" onPress={() => { void handleSubmit(); }}
            loading={createMutation.isPending} disabled={!canSubmit} fullWidth
          />
          <AppButton label="Keep my account" tone="secondary" onPress={handleKeepAccount} disabled={createMutation.isPending} fullWidth />
        </View>
      </View>
    </AppScreen>
  );
}

function Header({ onBack }: { onBack: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <AppText variant="headingSmall" accessibilityRole="header" style={{ flex: 1, textAlign: "center", marginRight: 44 }}>
        Final confirmation
      </AppText>
    </View>
  );
}

function SimpleRow({ icon, label }: { icon: React.ComponentProps<typeof Icon>["name"]; label: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <Icon name={icon} size="standard" color={theme.colors.textSecondary} decorative />
      <AppText variant="bodySmall" style={{ flex: 1 }}>{label}</AppText>
    </View>
  );
}

function SummaryRow({
  icon, label, value, last,
}: { icon: React.ComponentProps<typeof Icon>["name"]; label: string; value: string; last?: boolean }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.sm,
        borderBottomWidth: last ? 0 : 1, borderBottomColor: theme.colors.borderSubtle,
      }}
    >
      <Icon name={icon} size="compact" color={theme.colors.textSecondary} decorative />
      <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>{label}</AppText>
      <AppText variant="bodyStrong">{value}</AppText>
    </View>
  );
}
