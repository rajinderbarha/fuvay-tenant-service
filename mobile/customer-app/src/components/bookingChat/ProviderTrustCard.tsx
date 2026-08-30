import React from "react";
import { View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { ReviewProvider } from "../../domain/bookingReview";
import { distinctBadges } from "../../domain/providerBadges";
import { BotText } from "./BotText";
import { BOT_GUTTER } from "./BotPrimitives";

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

  // Only stars that actually have reviews behind them, highest first. Rendering
  // all five would show four empty rows for a provider with a single review --
  // visual bulk standing in for evidence that is not there.
  const breakdown = facts?.ratingBreakdown ?? {};
  const breakdownTotal = Object.values(breakdown).reduce((sum, n) => sum + n, 0);
  // reviewCount is also required: the two come from the same query and cannot
  // disagree in practice, so a breakdown arriving beside a zero count means a
  // stale payload, and a stale bar chart is worse than none.
  const starRows = breakdownTotal > 0 && reviewCount > 0
    ? [5, 4, 3, 2, 1]
        .map(star => ({ star, count: breakdown[String(star)] ?? 0 }))
        .filter(row => row.count > 0)
    : [];

  return (
    <View
      style={
        embedded
          ? undefined
          : {
              marginLeft: BOT_GUTTER, borderRadius: 20, padding: 16,
              backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle,
            }
      }
    >
      <BotText style={{ fontSize: 13, fontWeight: "700", color: BOT.textTertiary, letterSpacing: 0.4 }}>
        YOUR TECHNICIAN
      </BotText>

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
            <BotText
              numberOfLines={1}
              style={{ fontSize: 18, fontWeight: "700", color: BOT.textPrimary, flexShrink: 1 }}
            >
              {provider.providerName}
            </BotText>
            {/* Only when the platform genuinely verified them. */}
            {facts?.verified ? (
              <Ionicons name="checkmark-circle" size={17} color={BOT.brand} />
            ) : null}
          </View>

          {showHeadlineRating ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginTop: 3 }}>
              <Stars BOT={BOT} rating={rating!} />
              <BotText style={{ fontSize: 15, fontWeight: "700", color: BOT.textPrimary, marginLeft: 2 }}>
                {rating!.toFixed(1)}
              </BotText>
              <BotText style={{ fontSize: 13, color: BOT.textTertiary }}>
                ({reviewCount} {reviewCount === 1 ? "review" : "reviews"})
              </BotText>
            </View>
          ) : rating != null && reviewCount > 0 ? (
            // Real but thin: shown with its count, never as a headline stat.
            <BotText style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 3 }}>
              {rating.toFixed(1)} from {reviewCount} {reviewCount === 1 ? "review" : "reviews"}
            </BotText>
          ) : rating != null ? (
            // A rating with no known count (an older payload predating `facts`).
            // Stated without a count rather than claiming "no reviews yet",
            // which would contradict the rating sitting right next to it.
            <BotText style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 3 }}>
              {rating.toFixed(1)} average rating
            </BotText>
          ) : (
            <BotText style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 3 }}>
              New on Fuvay — no reviews yet
            </BotText>
          )}
        </View>
      </View>

      {/* Backend-authored badges only. Empty is a valid, honest state. */}
      {distinctBadges(provider.publicBadges).length > 0 ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
          {distinctBadges(provider.publicBadges).map(badge => (
            <View
              key={badge.name}
              style={{
                flexDirection: "row", alignItems: "center", gap: 4,
                paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12,
                backgroundColor: BOT.brandTint,
              }}
            >
              <Ionicons name="ribbon-outline" size={12} color={BOT.brand} />
              <BotText style={{ fontSize: 12, fontWeight: "600", color: BOT.brandLight }}>
                {badge.name}
              </BotText>
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
        {/* Experience with the service actually being booked -- a general total
            says nothing about whether they have done THIS job before. */}
        {facts?.jobsCompletedForService != null && facts.jobsCompletedForService > 0 ? (
          <Stat BOT={BOT} icon="build-outline"
                value={String(facts.jobsCompletedForService)} label="of this service" />
        ) : null}
        {facts?.completionRate != null ? (
          <Stat BOT={BOT} icon="checkmark-done-outline"
                value={`${facts.completionRate}%`} label="completed" />
        ) : null}
        {facts?.onPlatformSince ? (
          <Stat BOT={BOT} icon="calendar-outline"
                value={sinceLabel(facts.onPlatformSince)} label="on Fuvay" />
        ) : null}
        {facts?.city ? (
          <Stat BOT={BOT} icon="location-outline" value={facts.city} label="based in" />
        ) : null}
      </View>

      {/* How the reviews are actually distributed. Counts, not bars invented to
          look full: a customer reads "9 of 10 gave 5 stars" very differently
          from a bare average, and this is the same data the average comes
          from. Hidden entirely when there are no approved reviews. */}
      {starRows.length > 0 ? (
        <View style={{ marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, gap: 6 }}>
          <BotText style={{ fontSize: 12, fontWeight: "700", color: BOT.textTertiary, letterSpacing: 0.3 }}>
            RATING BREAKDOWN
          </BotText>
          {starRows.map(({ star, count }) => (
            <View key={star} style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <BotText style={{ fontSize: 12, color: BOT.textTertiary, width: 28 }}>{star}★</BotText>
              <View style={{ flex: 1, height: 6, borderRadius: 3, backgroundColor: BOT.surfaceRaised, overflow: "hidden" }}>
                <View
                  style={{
                    width: `${Math.round((count / breakdownTotal) * 100)}%`,
                    height: 6, borderRadius: 3, backgroundColor: BOT.warning,
                  }}
                />
              </View>
              <BotText style={{ fontSize: 12, color: BOT.textTertiary, width: 28, textAlign: "right" }}>
                {count}
              </BotText>
            </View>
          ))}
        </View>
      ) : null}

      {/* Real customer words, in full sentences rather than clipped. No
          reviewer identity -- the backend never sends one. */}
      {facts?.recentReviews && facts.recentReviews.length > 0 ? (
        <View style={{ marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, gap: 10 }}>
          <BotText style={{ fontSize: 12, fontWeight: "700", color: BOT.textTertiary, letterSpacing: 0.3 }}>
            WHAT CUSTOMERS SAID
          </BotText>
          {facts.recentReviews.map((review, index) => (
            <View key={`${review.createdAt ?? "r"}-${index}`} style={{ gap: 4 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <Stars BOT={BOT} rating={review.rating} />
                {review.createdAt ? (
                  <BotText style={{ fontSize: 12, color: BOT.textTertiary }}>
                    {sinceLabel(review.createdAt)}
                  </BotText>
                ) : null}
              </View>
              {review.title ? (
                <BotText style={{ fontSize: 14, fontWeight: "600", color: BOT.textPrimary }}>
                  {review.title}
                </BotText>
              ) : null}
              <BotText style={{ fontSize: 14, lineHeight: 20, color: BOT.textSecondary }}>
                {review.text}
              </BotText>
            </View>
          ))}
        </View>
      ) : null}

      <View
        style={{
          flexDirection: "row", alignItems: "flex-start", gap: 8,
          marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle,
        }}
      >
        <Ionicons name="lock-closed-outline" size={13} color={BOT.textTertiary} style={{ marginTop: 2 }} />
        <BotText style={{ flex: 1, fontSize: 13, lineHeight: 19, color: BOT.textTertiary }}>
          Calls go through Fuvay, so your number stays private. Every visit is tracked and
          covered by Fuvay support.
        </BotText>
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
      <BotText style={{ fontSize: 15, fontWeight: "700", color: BOT.textPrimary }}>{value}</BotText>
      <BotText style={{ fontSize: 13, color: BOT.textTertiary }}>{label}</BotText>
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
