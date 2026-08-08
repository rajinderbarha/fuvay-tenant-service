import React from "react";
import { View, Text, Image } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BookingReviewSummary } from "../../domain/bookingReview";
import { resolveMediaUrl } from "../../domain/mediaUrl";

export interface RequestSummaryCardProps {
  summary: BookingReviewSummary;
  /** Renders without its own card chrome, so ReviewSheet can present every
   * section in ONE scrolling column instead of a stack of separate cards. */
  embedded?: boolean;
  /** Formatted "Today, 14:00-15:00" for the chosen slot, or null when the
   * provider could not promise one. */
  slotLabel: string | null;
}

const THUMB = 52;

/**
 * "Here is exactly what we're booking" -- the recap directly above Confirm.
 *
 * The review turn previously showed price and provider but never played back
 * what the customer had actually said, so the last thing before an irreversible
 * action was the least informative. This reflects their own answers back at
 * them, which is both a correctness check (they can spot a wrong answer while it
 * is still free to fix) and the main reason a confirmation feels considered
 * rather than rushed.
 *
 * Every value comes from the backend summary. A section is omitted entirely when
 * its data is absent -- an empty "Photos" heading or a blank address line is
 * noise, and inventing a placeholder would be worse.
 */
export function RequestSummaryCard({ summary, slotLabel, embedded }: RequestSummaryCardProps) {
  const BOT = useBotColors();

  const addressLines = summary.address.lines.filter(line => !!line && line.trim().length > 0);
  const locality = [summary.address.city, summary.address.zipcode]
    .filter(Boolean).join(" · ");
  const answers = summary.answers.filter(a => !!a.value && a.value.trim().length > 0);

  return (
    <View
      style={
        embedded
          ? undefined
          : {
              marginLeft: 36, borderRadius: 20, padding: 16,
              backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle,
            }
      }
    >
      <Text style={{ fontSize: 13, fontWeight: "700", color: BOT.textTertiary, letterSpacing: 0.4 }}>
        YOUR REQUEST
      </Text>

      <Text style={{ fontSize: 18, fontWeight: "700", color: BOT.textPrimary, marginTop: 8 }}>
        {summary.offeringName}
      </Text>
      {summary.jobTypeLabel ? (
        <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 2 }}>
          {summary.jobTypeLabel}
        </Text>
      ) : null}

      {summary.issueSummary ? (
        <Text style={{ fontSize: 15, lineHeight: 21, color: BOT.textSecondary, marginTop: 10 }}>
          {summary.issueSummary}
        </Text>
      ) : null}

      {slotLabel ? (
        <Detail BOT={BOT} icon="time-outline" label="When" value={slotLabel} />
      ) : null}

      {addressLines.length > 0 || locality ? (
        <Detail
          BOT={BOT}
          icon="location-outline"
          label="Where"
          value={[...addressLines, locality].filter(Boolean).join("\n")}
        />
      ) : null}

      {/* What the customer actually told us, played back for a last check. */}
      {answers.length > 0 ? (
        <View style={{ marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle }}>
          <Text style={{ fontSize: 13, fontWeight: "700", color: BOT.textTertiary, marginBottom: 8 }}>
            WHAT YOU TOLD US
          </Text>
          {answers.map(answer => (
            <View
              key={answer.key}
              style={{ flexDirection: "row", alignItems: "flex-start", gap: 10, paddingVertical: 5 }}
            >
              <Text style={{ flex: 1, fontSize: 15, color: BOT.textTertiary }} numberOfLines={2}>
                {answer.label}
              </Text>
              <Text
                style={{
                  fontSize: 15, fontWeight: "600", color: BOT.textPrimary,
                  flexShrink: 1, textAlign: "right", maxWidth: "55%",
                }}
              >
                {answer.value}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      {summary.photoUrls.length > 0 ? (
        <View style={{ marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle }}>
          <Text style={{ fontSize: 13, fontWeight: "700", color: BOT.textTertiary, marginBottom: 8 }}>
            {summary.photoUrls.length === 1 ? "PHOTO YOU SENT" : `${summary.photoUrls.length} PHOTOS YOU SENT`}
          </Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {summary.photoUrls.map(url => (
              <Image
                key={url}
                source={{ uri: resolveMediaUrl(url) ?? url }}
                accessibilityLabel="Photo you attached"
                style={{
                  width: THUMB, height: THUMB, borderRadius: 10,
                  backgroundColor: BOT.surfaceSunken,
                }}
              />
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );
}

function Detail({
  BOT, icon, label, value,
}: {
  BOT: ReturnType<typeof useBotColors>;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  value: string;
}) {
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 10, marginTop: 12 }}>
      <Ionicons name={icon} size={15} color={BOT.textTertiary} style={{ marginTop: 2 }} />
      <View style={{ flex: 1, minWidth: 0 }}>
        <Text style={{ fontSize: 13, color: BOT.textTertiary }}>{label}</Text>
        <Text style={{ fontSize: 15, lineHeight: 21, color: BOT.textPrimary, marginTop: 1 }}>
          {value}
        </Text>
      </View>
    </View>
  );
}
