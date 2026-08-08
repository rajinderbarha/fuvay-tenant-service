import React from "react";
import { View, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { ReviewProvider } from "../../domain/bookingReview";

export interface ProviderTrustCardProps {
  provider: ReviewProvider;
  /** Renders without its own card chrome so it can sit as a section inside
   * ReviewSheet's single scrolling column. */
  embedded?: boolean;
}

/** Enough reviews for an average to mean something. Below this the rating is
 * still shown, but never as a headline stat -- one happy customer is not a
 * track record, and presenting it as one is the kind of thing that makes a
 * customer distrust every other number on the screen. */
const MIN_REVIEWS_FOR_HEADLINE = 3;

/**
 * Who is coming, and why the customer can believe it.
 *
 * Every figure here is a counted fact from the backend (`provider.facts`):
 * approved-review average, real verification status, completed-job count. The
 * card shows nothing where there is nothing -- no "0 reviews", no "0% jobs", no
 * "Verified" for a provider whose verification never started (a live bug this
 * replaces: the API used to add that badge unconditionally).
 *
 * A provider with no history gets an honest "New on Fuvay" line instead of
 * borrowed credibility. That is deliberately better for trust overall: a
 * customer who catches one inflated claim stops believing the true ones.
 */
export function ProviderTrustCard({ provider, embedded }: ProviderTrustCardProps) {
  const BOT = useBotColors();
  const facts = provider.facts;
  const rating = facts?.rating ?? provider.rating ?? null;
  const reviewCount = facts?.reviewCount ?? 0;
  const showHeadlineRating = rating != null && reviewCount >= MIN_REVIEWS_FOR_HEADLINE;

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
        YOUR TECHNICIAN
      </Text>

      <View style={{ flexDirection: "row", alignItems: "center", gap: 12, marginTop: 10 }}>
        <View
          style={{
            width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center",
            backgroundColor: BOT.brandTint,
          }}
        >
          <Ionicons name="construct" size={22} color={BOT.brand} />
        </View>

        <View style={{ flex: 1, minWidth: 0 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Text
              numberOfLines={1}
              style={{ fontSize: 18, fontWeight: "700", color: BOT.textPrimary, flexShrink: 1 }}
            >
              {provider.providerName}
            </Text>
            {/* Only when the platform genuinely verified them. */}
            {facts?.verified ? (
              <Ionicons name="checkmark-circle" size={17} color={BOT.brand} />
            ) : null}
          </View>

          {showHeadlineRating ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginTop: 3 }}>
              <Stars BOT={BOT} rating={rating!} />
              <Text style={{ fontSize: 15, fontWeight: "700", color: BOT.textPrimary, marginLeft: 2 }}>
                {rating!.toFixed(1)}
              </Text>
              <Text style={{ fontSize: 13, color: BOT.textTertiary }}>
                ({reviewCount} {reviewCount === 1 ? "review" : "reviews"})
              </Text>
            </View>
          ) : rating != null && reviewCount > 0 ? (
            // Real but thin: shown with its count, never as a headline stat.
            <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 3 }}>
              {rating.toFixed(1)} from {reviewCount} {reviewCount === 1 ? "review" : "reviews"}
            </Text>
          ) : rating != null ? (
            // A rating with no known count (an older payload predating `facts`).
            // Stated without a count rather than claiming "no reviews yet",
            // which would contradict the rating sitting right next to it.
            <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 3 }}>
              {rating.toFixed(1)} average rating
            </Text>
          ) : (
            <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 3 }}>
              New on Fuvay — no reviews yet
            </Text>
          )}
        </View>
      </View>

      {/* Backend-authored badges only. Empty is a valid, honest state. */}
      {provider.publicBadges.length > 0 ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
          {provider.publicBadges.map(badge => (
            <View
              key={badge.name}
              style={{
                flexDirection: "row", alignItems: "center", gap: 4,
                paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12,
                backgroundColor: BOT.brandTint,
              }}
            >
              <Ionicons name="ribbon-outline" size={12} color={BOT.brand} />
              <Text style={{ fontSize: 12, fontWeight: "600", color: BOT.brandLight }}>
                {badge.name}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      {/* Facts, each rendered only when it exists. */}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 16, marginTop: 14 }}>
        {facts && facts.jobsCompleted > 0 ? (
          <Stat BOT={BOT} icon="briefcase-outline"
                value={String(facts.jobsCompleted)} label="jobs done" />
        ) : null}
        {facts?.completionRate != null ? (
          <Stat BOT={BOT} icon="checkmark-done-outline"
                value={`${facts.completionRate}%`} label="completed" />
        ) : null}
        {facts?.onPlatformSince ? (
          <Stat BOT={BOT} icon="calendar-outline"
                value={sinceLabel(facts.onPlatformSince)} label="on Fuvay" />
        ) : null}
      </View>

      <View
        style={{
          flexDirection: "row", alignItems: "flex-start", gap: 8,
          marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle,
        }}
      >
        <Ionicons name="lock-closed-outline" size={13} color={BOT.textTertiary} style={{ marginTop: 2 }} />
        <Text style={{ flex: 1, fontSize: 13, lineHeight: 19, color: BOT.textTertiary }}>
          Calls go through Fuvay, so your number stays private. Every visit is tracked and
          covered by Fuvay support.
        </Text>
      </View>
    </View>
  );
}

/** Five stars, filled to the real average. Half-stars are shown rather than
 * rounded up -- rounding 4.3 to 5 would be exactly the small lie this card
 * exists to avoid. */
function Stars({ BOT, rating }: { BOT: ReturnType<typeof useBotColors>; rating: number }) {
  return (
    <View style={{ flexDirection: "row", gap: 1 }}>
      {[1, 2, 3, 4, 5].map(position => {
        const name =
          rating >= position ? "star"
            : rating >= position - 0.5 ? "star-half"
              : "star-outline";
        return <Ionicons key={position} name={name} size={13} color={BOT.warning} />;
      })}
    </View>
  );
}

function Stat({
  BOT, icon, value, label,
}: {
  BOT: ReturnType<typeof useBotColors>;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  value: string;
  label: string;
}) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
      <Ionicons name={icon} size={14} color={BOT.textTertiary} />
      <Text style={{ fontSize: 15, fontWeight: "700", color: BOT.textPrimary }}>{value}</Text>
      <Text style={{ fontSize: 13, color: BOT.textTertiary }}>{label}</Text>
    </View>
  );
}

/** "Jul 2026" from an ISO timestamp. Returns null-safe text; an unparseable
 * value yields an empty string so the stat is simply blank rather than "Invalid
 * Date" reaching a customer. */
function sinceLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}
