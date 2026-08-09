import React from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeQuickIssue } from "../../domain/customerHome";
import { resolveQuickIssueIcon } from "../../domain/quickIssueIcon";
import { resolveMediaUrl } from "../../domain/mediaUrl";

export interface ProblemCirclesProps {
  issues: readonly HomeQuickIssue[];
  title?: string | null;
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/** Four across, three rows deep at twelve items. */
const COLUMNS = 4;
const CIRCLE = 56;

/**
 * The second, larger problem surface, further down the screen.
 *
 * Circles rather than the cards used higher up, and deliberately so: a customer
 * arriving here has already passed the shortlist, so this is browsing, not
 * choosing. Lighter chrome (no card, no border, just the glyph and its label)
 * lets twelve fit without the section feeling like a second attempt at the same
 * thing.
 *
 * Same real problems, same one-tap route into the assistant with the category and
 * problem already chosen. No price, no severity -- for the same reasons as the
 * tile grid: the amount depends on answers not yet given, and a customer already
 * knows how bad their own fault is.
 */
export function ProblemCircles({ issues, title, onPressIssue }: ProblemCirclesProps) {
  const { theme } = useTheme();
  const tappable = issues.filter(i => !!i.categorySlug);
  if (tappable.length === 0) return null;

  const rows: HomeQuickIssue[][] = [];
  for (let i = 0; i < tappable.length; i += COLUMNS) rows.push(tappable.slice(i, i + COLUMNS));

  return (
    <View>
      <View style={{ gap: 2, marginBottom: theme.spacing.sm }}>
        <AppText variant="headingSmall">{title || "More things we fix"}</AppText>
        <AppText variant="caption" color="tertiary">Tap one to book it in a couple of taps</AppText>
      </View>

      <View style={{ gap: theme.spacing.base }}>
        {rows.map((row, rowIndex) => (
          <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            {row.map(issue => (
              <ProblemCircle key={issue.issueId} issue={issue} onPress={() => onPressIssue(issue)} />
            ))}
            {/* Equal-flex spacers keep a short final row's circles the same size
                and position as the rows above, rather than spreading them. */}
            {Array.from({ length: COLUMNS - row.length }).map((_, i) => (
              <View key={`spacer-${i}`} style={{ flex: 1 }} />
            ))}
          </View>
        ))}
      </View>
    </View>
  );
}

function ProblemCircle({ issue, onPress }: { issue: HomeQuickIssue; onPress: () => void }) {
  const { theme } = useTheme();
  const glyph = resolveQuickIssueIcon(issue.label, issue.categoryName);
  const artwork = issue.iconUrl ? resolveMediaUrl(issue.iconUrl) : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
      accessibilityHint="Opens the booking assistant with this problem selected"
      style={({ pressed }) => ({
        flex: 1, alignItems: "center", gap: theme.spacing.xs, opacity: pressed ? 0.8 : 1,
      })}
    >
      <View
        style={{
          width: CIRCLE, height: CIRCLE, borderRadius: CIRCLE / 2,
          alignItems: "center", justifyContent: "center", overflow: "hidden",
          // The wording-derived tint, so a wall of twelve reads as distinct
          // things rather than twelve grey discs.
          backgroundColor: artwork ? theme.colors.surfaceSecondary : `${glyph.tint}1F`,
        }}
      >
        {artwork ? (
          <Image source={{ uri: artwork }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
        ) : (
          <Icon name={glyph.name} size="navigation" color={glyph.tint} decorative />
        )}
      </View>
      <AppText variant="caption" numberOfLines={2} align="center">{issue.label}</AppText>
    </Pressable>
  );
}
