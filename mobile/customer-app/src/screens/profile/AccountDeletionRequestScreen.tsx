import React, { useState } from "react";
import { View } from "react-native";
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
import { DeletionWarningPanel } from "../../components/privacy/DeletionWarningPanel";
import { DeletionInfoRow } from "../../components/privacy/DeletionInfoRow";
import { usePrivacyRequestsQuery } from "../../api/privacyData/usePrivacyDataQueries";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "AccountDeletionRequest">;

const OPEN_STATUSES = new Set(["submitted", "identity_verification_pending", "under_review", "approved", "processing"]);

/**
 * Opened from Privacy & Data -> "Delete my account". This is the REVIEW
 * step only (spec section 3) -- it never mutates on open and never
 * submits anything itself. Classification: REQUEST_BASED_DELETION
 * (traced into `enterprise_service.process_request` ->
 * `service.process_deletion`, a real, admin-triggered anonymization pass
 * that explicitly exempts financial/audit records with a recorded reason
 * -- confirms "Some records may be retained" is accurate, not invented).
 *
 * No customer-facing eligibility/blocker endpoint exists anywhere in the
 * audited compliance engine (only an ADMIN-triggered legal-hold check at
 * PROCESS time, which must never be exposed to the customer pre-
 * submission) -- the "Active services may be affected" row is therefore
 * forward-looking boilerplate, never a claim that this app checked
 * anything.
 *
 * Continue carries the collected `reason` forward to
 * `DeleteAccountFinalConfirmation`, which owns the real identity
 * verification (current-password confirmation, a real backend contract
 * confirmed this phase) and the actual submission -- this screen performs
 * neither.
 */
export function AccountDeletionRequestScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const requestsQuery = usePrivacyRequestsQuery(1);
  const profileQuery = useCustomerProfileQuery();

  const [reason, setReason] = useState("");

  if (requestsQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Checking for an existing request…" />
      </AppScreen>
    );
  }

  const existingErasure = (requestsQuery.data?.requests ?? []).find(
    r => r.requestType === "right_to_erasure" && OPEN_STATUSES.has(r.status),
  );

  if (existingErasure) {
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          <Header onBack={() => navigation.goBack()} />
          <AppCard style={{ gap: theme.spacing.sm, alignItems: "center" }}>
            <Icon name="hourglass-outline" size="feature" color={theme.colors.textSecondary} decorative />
            <AppText variant="bodyStrong" align="center">You already have a deletion request in progress</AppText>
            <AppText variant="bodySmall" color="secondary" align="center">{existingErasure.statusLabel}</AppText>
            <AppButton label="Back to Privacy & data" tone="secondary" onPress={() => navigation.goBack()} fullWidth />
          </AppCard>
        </View>
      </AppScreen>
    );
  }

  const profile = profileQuery.data;
  const displayName = profile?.displayName ?? profile?.fullName ?? "";
  const initials = displayName ? displayName.charAt(0).toUpperCase() : "";
  const canContinue = !!reason.trim();

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <Header onBack={() => navigation.goBack()} />

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.brandPrimaryMuted, borderWidth: 1, borderColor: theme.colors.brandPrimary }}>
          <Icon name="person-remove-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>Request account deletion</AppText>
            <AppText variant="caption" color="secondary">Review what this request means before you continue.</AppText>
          </View>
        </View>

        <DeletionWarningPanel />

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Before you continue</AppText>
          <AppCard style={{ gap: theme.spacing.xs }}>
            <DeletionInfoRow
              icon="search-outline" title="Your request will be reviewed"
              subtitle="Deletion happens only after the request is approved and processed."
            />
            <DeletionInfoRow
              icon="document-lock-outline" title="Some records may be retained"
              subtitle="Information may be kept when required for security, legal, or transaction records."
            />
            <DeletionInfoRow
              icon="calendar-outline" title="Active services may be affected"
              subtitle="We'll show any actions required before you submit."
            />
          </AppCard>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Account</AppText>
          <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
            <View
              style={{
                width: 40, height: 40, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
                backgroundColor: theme.colors.brandPrimaryMuted,
              }}
            >
              <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>{initials}</AppText>
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{displayName || "Your account"}</AppText>
              <AppText variant="bodySmall" color="secondary">Fuvay customer account</AppText>
            </View>
          </AppCard>
        </View>

        {/* No reason field exists in the approved design, but the real
            backend requires one for right_to_erasure -- kept here rather
            than fabricating a generic value (see file-level comment). */}
        <AppInput
          label="Reason for deletion"
          value={reason}
          onChangeText={setReason}
          accessibilityLabel="Reason for deletion"
          multiline
          maxLength={1000}
        />

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton
            label="Continue" tone="destructive"
            onPress={() => navigation.navigate("DeleteAccountFinalConfirmation", { reason: reason.trim() })}
            disabled={!canContinue}
            fullWidth
          />
          <AppButton label="Keep my account" tone="secondary" onPress={() => navigation.goBack()} fullWidth />
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
        Delete my account
      </AppText>
    </View>
  );
}
