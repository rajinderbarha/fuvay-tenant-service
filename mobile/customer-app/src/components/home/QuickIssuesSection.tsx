import React from "react";
import { View, Pressable, ScrollView } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeQuickIssue } from "../../domain/customerHome";
import { resolveQuickIssueIcon } from "../../domain/quickIssueIcon";

export interface QuickIssuesSectionProps {
  issues: readonly HomeQuickIssue[];
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/** Wide enough for a two-line label without the row feeling like a wall. */
const TILE_WIDTH = 92;
const CIRCLE = 60;

/**
 * "Book in one tap" -- named problems the customer can go straight into.
 *
 * Normally booking means: pick a category, read an issue list, then answer
 * the Assistant's questions. These chips collapse the first two steps --
 * tapping one enters the Assistant with the category AND the issue already
 * chosen, so the very first thing asked is the brand/detail question.
 *
 * No price is shown. Each issue does resolve to a priced service in the
 * catalog, but the amount depends on answers that have not been given yet,
 * so a figure here would be a quote the booking flow might not honour.
 *
 * Only issues whose category is bookable at the customer's ZIP reach this
 * component (the backend scopes them), and one with no category slug is
 * dropped rather than rendered as a chip that cannot open -- the Assistant
 * is entered by slug.
 */
export function QuickIssuesSection({ issues, onPressIssue }: QuickIssuesSectionProps) {
  const { theme } = useTheme();
  const tappable = issues.filter(i => !!i.categorySlug);
  if (tappable.length === 0) return null;

  return (
    <View>
      {/* No section heading by design: the circles are self-explanatory and
          a title over them made the row read as another content block
          competing with the banner above it. */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: theme.spacing.base, paddingRight: theme.spacing.base }}
      >
        {tappable.map(issue => {
          const icon = resolveQuickIssueIcon(issue.label, issue.categoryName);
          return (
            <Pressable
              key={issue.issueId}
              onPress={() => onPressIssue(issue)}
              accessibilityRole="button"
              // The category is spoken as well as shown: "Bad Smell" on
              // its own does not say what is being booked.
              accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
              accessibilityHint="Opens the booking assistant with this problem selected"
              style={({ pressed }) => ({
                width: TILE_WIDTH,
                alignItems: "center",
                gap: theme.spacing.xs,
                opacity: pressed ? 0.7 : 1,
              })}
            >
              <View
                style={{
                  width: CIRCLE, height: CIRCLE, borderRadius: CIRCLE / 2,
                  alignItems: "center", justifyContent: "center",
                  backgroundColor: icon.tint,
                  ...theme.shadow.sm,
                }}
              >
                <Icon name={icon.name} size="navigation" color={icon.onTint} decorative />
              </View>
              <AppText variant="caption" align="center" numberOfLines={2}>
                {issue.label}
              </AppText>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}
