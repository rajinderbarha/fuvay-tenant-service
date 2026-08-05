import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerJobCompletion } from "../../domain/customerBookingDetails";
import { toDisplayDate, parseServerTimestamp } from "../../domain/dates";

function formatCompletedDate(iso: string | null): string | null {
  if (!iso) return null;
  return toDisplayDate(parseServerTimestamp(iso, "completed_at")).toLocaleDateString(undefined, {
    day: "numeric", month: "short", year: "numeric",
  });
}

export interface WorkCompletedCardProps {
  serviceName: string | null;
  completion: CustomerJobCompletion;
  /** True once the review is also submitted -- this is the mission's
   * terminal "Booking closed" state (job complete AND review complete,
   * no pending customer decision remains). False renders the intermediate
   * "Service completed" acknowledgment (job complete, review still open). */
  closed?: boolean;
}

/** Status card + Work summary ("Service record") + Final service amount --
 * every value comes from `completion` (the real `completion_data` record
 * `complete_job()` writes), never invented. `work_summary` is a single
 * free-text field the technician entered -- there is no itemized
 * "finding"/"part replaced" breakdown on the real backend for the
 * completion record itself, so this renders the summary as one paragraph
 * rather than fabricating a bulleted structure the data doesn't have. */
export function WorkCompletedCard({ serviceName, completion, closed }: WorkCompletedCardProps) {
  const { theme } = useTheme();
  const completedDate = formatCompletedDate(completion.completedAt);

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
            <Icon name={closed ? "checkmark-done-circle-outline" : "checkmark-circle-outline"} size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1, gap: theme.spacing.xxs }}>
            <AppText variant="bodyStrong" accessibilityRole="header">{closed ? "Booking closed" : "Service completed"}</AppText>
            <AppText variant="bodySmall" color="secondary">
              {closed
                ? "Your service and review are complete."
                : serviceName
                ? `Your ${serviceName} has been marked complete.`
                : "Your service has been marked complete."}
            </AppText>
          </View>
        </View>
      </AppCard>

      {completion.workSummary ? (
        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">{closed ? "Service record" : "Work summary"}</AppText>
          <AppCard>
            <AppText variant="body">{completion.workSummary}</AppText>
            {completedDate ? (
              <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>Completed {completedDate}</AppText>
            ) : null}
          </AppCard>
        </View>
      ) : null}

      {completion.collectedAmount !== null ? (
        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Final service amount</AppText>
          <AppCard>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <AppText variant="bodyStrong">Total</AppText>
              <AppText
                variant="bodyStrong"
                style={{ color: theme.colors.brandPrimaryStrong }}
                accessibilityLabel={`Final service amount: ${completion.collectedAmount}`}
              >
                {completion.collectedAmount}
              </AppText>
            </View>
          </AppCard>
        </View>
      ) : null}

      <View
        style={{
          flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm,
          borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive,
        }}
      >
        <Icon name="information-circle-outline" size="standard" color={theme.colors.textSecondary} decorative />
        <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>
          Payment is made directly to the provider. Fuvay does not verify or collect job payment.
        </AppText>
      </View>
    </View>
  );
}
