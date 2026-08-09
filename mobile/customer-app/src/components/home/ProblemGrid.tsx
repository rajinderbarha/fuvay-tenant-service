import React from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeQuickIssue } from "../../domain/customerHome";
import { resolveQuickIssueIcon } from "../../domain/quickIssueIcon";
import { resolveMediaUrl } from "../../domain/mediaUrl";

export interface ProblemGridProps {
  issues: readonly HomeQuickIssue[];
  title?: string | null;
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/** Four across reads as a grid on every phone width; three is sparse and five
 * squeezes two-word labels onto three lines. */
const COLUMNS = 4;

/**
 * The problems a customer can book in one tap, as a tile grid.
 *
 * Why a grid rather than the horizontal chip rail this replaces: a rail hides
 * most of its contents off-screen, so whether "AC Not Cooling" was on offer
 * depended on whether the customer thought to swipe. A fixed grid shows the whole
 * shortlist at a glance.
 *
 * It shows exactly what it is given -- no overflow tile, no "See all". The caller
 * decides how many (see selectProblems), and the larger circles section further
 * down the screen carries a different selection, so browsing beyond the shortlist
 * happens in the page rather than behind a sheet.
 *
 * What is deliberately NOT shown here:
 *
 *  - Severity. It is in the payload (dispatch grades it) but the customer
 *    already knows how bad their own fault is; a red "critical" chip on it
 *    would read as alarm, not information.
 *  - Prices. Each problem resolves to a priced service, but the amount depends
 *    on answers not yet given, so a figure here would be a quote the booking
 *    flow might not honour.
 *
 * Ordering is the backend's (display_order, then name), not a client guess at
 * what is popular.
 */
export function ProblemGrid({ issues, title, onPressIssue }: ProblemGridProps) {
  const { theme } = useTheme();

  // A problem with no category slug cannot open the assistant, so it is dropped
  // rather than rendered as a tile that does nothing when pressed.
  const tappable = issues.filter(i => !!i.categorySlug);
  if (tappable.length === 0) return null;

  const rows: HomeQuickIssue[][] = [];
  for (let i = 0; i < tappable.length; i += COLUMNS) rows.push(tappable.slice(i, i + COLUMNS));

  return (
    <View style={{ gap: theme.spacing.sm }}>
      <AppText variant="headingSmall">{title || "What's the problem?"}</AppText>

      <View style={{ gap: theme.spacing.sm }}>
        {rows.map((row, rowIndex) => (
          <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            {row.map(issue => (
              <ProblemTile
                key={issue.issueId}
                issue={issue}
                onPress={() => onPressIssue(issue)}
              />
            ))}
            {/* Equal-flex spacers keep a short final row's tiles the same width
                as the rows above rather than stretching them. */}
            {Array.from({ length: COLUMNS - row.length }).map((_, i) => (
              <View key={`spacer-${i}`} style={{ flex: 1 }} />
            ))}
          </View>
        ))}
      </View>
    </View>
  );
}

function ProblemTile({ issue, onPress }: { issue: HomeQuickIssue; onPress: () => void }) {
  const { theme } = useTheme();
  const glyph = resolveQuickIssueIcon(issue.label, issue.categoryName);
  const artwork = issue.iconUrl ? resolveMediaUrl(issue.iconUrl) : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      // The category is spoken as well as shown: "Bad Smell" alone does not say
      // what is being booked.
      accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
      accessibilityHint="Opens the booking assistant with this problem selected"
      style={({ pressed }) => ({
        flex: 1,
        alignItems: "center", gap: theme.spacing.xs,
        paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.xxs,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
        opacity: pressed ? 0.85 : 1,
      })}
    >
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radiusUsage.input,
          alignItems: "center", justifyContent: "center", overflow: "hidden",
          // The wording-derived tint, so the row is legible at a glance rather
          // than eight identical grey squares.
          backgroundColor: artwork ? theme.colors.surfaceSecondary : `${glyph.tint}1A`,
        }}
      >
        {artwork ? (
          <Image source={{ uri: artwork }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
        ) : (
          <Icon name={glyph.name} size="standard" color={glyph.tint} decorative />
        )}
      </View>
      <AppText variant="caption" numberOfLines={2} style={{ textAlign: "center" }}>
        {issue.label}
      </AppText>
    </Pressable>
  );
}
