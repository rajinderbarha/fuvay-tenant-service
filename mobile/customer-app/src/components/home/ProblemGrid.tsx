import React, { useMemo, useState } from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeQuickIssue } from "../../domain/customerHome";
import { resolveQuickIssueIcon } from "../../domain/quickIssueIcon";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { AllProblemsSheet } from "./AllProblemsSheet";

export interface ProblemGridProps {
  issues: readonly HomeQuickIssue[];
  title?: string | null;
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/** Four across reads as a grid on every phone width; three is sparse and five
 * squeezes two-word labels onto three lines. */
const COLUMNS = 4;
/** Two rows of four, with the last cell spent on "More" -- so seven problems are
 * one tap away and the rest are two, without the section becoming a wall. */
const VISIBLE = COLUMNS * 2 - 1;

/**
 * The problems a customer can book in one tap, as a tile grid.
 *
 * Why a grid rather than the horizontal chip rail this replaces: a rail hides
 * most of its contents off-screen, so whether "AC Not Cooling" was on offer
 * depended on whether the customer thought to swipe. A fixed grid shows the
 * whole shortlist at a glance, and "More" makes the remainder reachable without
 * anyone having to go back and pick a service first.
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
  const [sheetOpen, setSheetOpen] = useState(false);

  // A problem with no category slug cannot open the Assistant, so it is dropped
  // rather than rendered as a tile that does nothing when pressed.
  const tappable = useMemo(() => issues.filter(i => !!i.categorySlug), [issues]);
  if (tappable.length === 0) return null;

  const overflow = tappable.length > VISIBLE;
  const shown = overflow ? tappable.slice(0, VISIBLE) : tappable;
  const rows: HomeQuickIssue[][] = [];
  for (let i = 0; i < shown.length; i += COLUMNS) rows.push(shown.slice(i, i + COLUMNS));

  return (
    <View style={{ gap: theme.spacing.sm }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <AppText variant="headingSmall">{title || "What's the problem?"}</AppText>
        {overflow ? (
          <Pressable
            onPress={() => setSheetOpen(true)}
            accessibilityRole="button"
            accessibilityLabel="See all problems"
            hitSlop={8}
          >
            <AppText variant="labelStrong" color="link">See all</AppText>
          </Pressable>
        ) : null}
      </View>

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
            {/* "More" takes the last cell of the final row when there is
                overflow; otherwise equal-flex spacers keep every tile the same
                width as the rows above rather than stretching a short row. */}
            {rowIndex === rows.length - 1 && overflow ? (
              <MoreTile count={tappable.length - shown.length} onPress={() => setSheetOpen(true)} />
            ) : null}
            {Array.from({
              length: COLUMNS - row.length - (rowIndex === rows.length - 1 && overflow ? 1 : 0),
            }).map((_, i) => <View key={`spacer-${i}`} style={{ flex: 1 }} />)}
          </View>
        ))}
      </View>

      <AllProblemsSheet
        visible={sheetOpen}
        issues={tappable}
        onClose={() => setSheetOpen(false)}
        onPressIssue={issue => { setSheetOpen(false); onPressIssue(issue); }}
      />
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

/** The overflow affordance. Carries the real remaining count -- "More" alone
 * gives no sense of whether one thing or thirty is behind it. */
function MoreTile({ count, onPress }: { count: number; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`See all problems, ${count} more`}
      style={({ pressed }) => ({
        flex: 1,
        alignItems: "center", gap: theme.spacing.xs,
        paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.xxs,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceInteractive,
        borderWidth: 1, borderColor: theme.colors.brandPrimaryMuted,
        opacity: pressed ? 0.85 : 1,
      })}
    >
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radiusUsage.input,
          alignItems: "center", justifyContent: "center",
          backgroundColor: theme.colors.brandPrimaryMuted,
        }}
      >
        <Icon name="grid-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
      </View>
      <AppText variant="caption" color="link" numberOfLines={2} style={{ textAlign: "center" }}>
        {`+${count} more`}
      </AppText>
    </Pressable>
  );
}
