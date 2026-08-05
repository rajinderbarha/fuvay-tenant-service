import React, { useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { AppInput } from "../AppInput";
import { Icon } from "../Icon";
import { CustomerPartsRequestList } from "../../domain/customerParts";
import { PartsPresentationKind, resolvePartsPresentation } from "../../domain/partsApprovalPresentation";

export interface PartsApprovalCardProps {
  parts: CustomerPartsRequestList;
  kind: PartsPresentationKind;
  /** The single actionable item when `kind === "actionable"` -- there is
   * at most one item awaiting a customer decision at a time (the backend's
   * own model has no concept of batching multiple pending decisions into
   * one submission). */
  actionableItemId: string | null;
  onApprove: (partsRequestId: string) => void;
  onDecline: (partsRequestId: string, reason: string) => void;
  approving: boolean;
  declining: boolean;
}

/** Extends the existing `BookingDetailsScreen` (mission: no second parts
 * route). Renders whichever real workflow the backend proves for THIS
 * request -- `customer_approval_required` (Outcome C: real customer
 * decision) or not (Outcome B: informational only, decision already made
 * by the business). Every amount comes from `parts` as computed
 * server-side; this component never sums or discounts a total itself. */
export function PartsApprovalCard({ parts, kind, actionableItemId, onApprove, onDecline, approving, declining }: PartsApprovalCardProps) {
  const { theme } = useTheme();
  const [decliningOpen, setDecliningOpen] = useState(false);
  const [reason, setReason] = useState("");
  const presentation = resolvePartsPresentation(kind);
  const actionable = kind === "actionable" && !!actionableItemId;
  const busy = approving || declining;

  return (
    <View style={{ gap: theme.spacing.base }}>
      <AppCard style={{ borderColor: theme.colors.brandPrimary, borderWidth: 1 }}>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radiusUsage.card, alignItems: "center", justifyContent: "center",
              backgroundColor: theme.colors.brandPrimaryMuted,
            }}
          >
            <Icon name="build-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1, gap: theme.spacing.xxs }}>
            <AppText variant="bodyStrong" accessibilityRole="header">{presentation.title}</AppText>
            {presentation.explanation ? <AppText variant="bodySmall" color="secondary">{presentation.explanation}</AppText> : null}
          </View>
        </View>
      </AppCard>

      <View style={{ gap: theme.spacing.xs }}>
        <AppText variant="labelStrong" color="secondary">Part requested</AppText>
        {parts.items.map(item => (
          <AppCard key={item.id}>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <View style={{ flex: 1 }}>
                <AppText variant="bodyStrong">{item.partName}</AppText>
                <AppText variant="bodySmall" color="secondary">Quantity {item.quantity}</AppText>
                <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>{item.reason}</AppText>
              </View>
              <AppText
                variant="bodyStrong"
                style={{ color: theme.colors.brandPrimaryStrong }}
                accessibilityLabel={`Additional amount: +${parts.currency} ${item.lineTotal}`}
              >
                +{parts.currency} {item.lineTotal}
              </AppText>
            </View>
          </AppCard>
        ))}
      </View>

      <View style={{ gap: theme.spacing.xs }}>
        <AppText variant="labelStrong" color="secondary">Updated estimate</AppText>
        <AppCard style={{ gap: 0 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xs, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
            <AppText variant="body" color="secondary">Previously approved</AppText>
            <AppText variant="body">{parts.currency} {parts.previousEstimatedTotal}</AppText>
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xs, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
            <AppText variant="body" color="secondary">Additional part</AppText>
            <AppText variant="body">+{parts.currency} {parts.additionalTotal}</AppText>
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between", paddingTop: theme.spacing.sm }}>
            <AppText variant="bodyStrong">Updated estimated total</AppText>
            <AppText
              variant="bodyStrong"
              style={{ color: theme.colors.brandPrimaryStrong }}
              accessibilityLabel={`Updated estimated total: ${parts.currency} ${parts.newEstimatedTotal}`}
            >
              {parts.currency} {parts.newEstimatedTotal}
            </AppText>
          </View>
        </AppCard>
      </View>

      <View
        style={{
          flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm,
          borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive,
        }}
      >
        <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.textSecondary} decorative />
        <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>
          Pay the provider directly after service. Fuvay does not collect job payment.
        </AppText>
      </View>

      {actionable && actionableItemId ? (
        <View style={{ gap: theme.spacing.sm }}>
          <AppText variant="labelStrong" color="secondary">Your decision</AppText>
          <AppText variant="bodySmall" color="secondary">Approve to allow the repair to continue.</AppText>
          {!decliningOpen ? (
            <>
              <AppButton
                label={approving ? "Submitting your decision…" : `Approve additional cost · ${parts.currency} ${parts.additionalTotal}`}
                tone="primary" fullWidth disabled={busy} onPress={() => onApprove(actionableItemId)}
              />
              <AppButton label="Decline additional cost" tone="secondary" fullWidth disabled={busy} onPress={() => setDecliningOpen(true)} />
            </>
          ) : (
            <View style={{ gap: theme.spacing.sm }}>
              <AppInput
                label="Why are you declining?" value={reason} onChangeText={setReason}
                multiline placeholder="Tell us why this additional cost doesn't work for you"
              />
              <AppButton
                label={declining ? "Submitting your decision…" : "Confirm decline"}
                tone="destructive" fullWidth disabled={busy || !reason.trim()}
                onPress={() => onDecline(actionableItemId, reason.trim())}
              />
              <AppButton label="Back" tone="secondary" fullWidth disabled={busy} onPress={() => setDecliningOpen(false)} />
            </View>
          )}
        </View>
      ) : kind === "declined" ? (
        (() => {
          const declinedItem = parts.items.find(i => i.rejectionReason);
          return declinedItem?.rejectionReason ? (
            <View style={{ gap: theme.spacing.xxs }}>
              <AppText variant="labelStrong" color="secondary">Your reason</AppText>
              <AppText variant="bodySmall">{declinedItem.rejectionReason}</AppText>
            </View>
          ) : null;
        })()
      ) : kind === "informational" ? (
        <View style={{ gap: theme.spacing.xxs }}>
          <AppText variant="labelStrong" color="secondary">What happens next</AppText>
          <AppText variant="bodySmall" color="secondary">
            This part has been approved and added to your repair. No action is needed from you.
          </AppText>
        </View>
      ) : null}
    </View>
  );
}
