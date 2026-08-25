import React from "react";
import { Pressable, ScrollView, View } from "react-native";

import { useTheme } from "../../design-system/theme";
import { HomeQuickIssue } from "../../domain/customerHome";
import { AppText } from "../AppText";

export interface ProblemCirclesProps {
  issues: readonly HomeQuickIssue[];
  title?: string | null;
  variant?: "showcase" | "expert" | "compact";
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/** Purpose-built browsing surfaces keep adjacent Home sections from repeating. */
export function ProblemCircles({ issues, title, variant = "showcase", onPressIssue }: ProblemCirclesProps) {
  const { theme } = useTheme();
  const tappable = issues.filter(issue => !!issue.categorySlug);
  if (tappable.length === 0) return null;

  return (
    <View>
      <View style={{ marginBottom: theme.spacing.md }}>
        <AppText variant="headingSmall">{title || "More things we fix"}</AppText>
        <AppText variant="caption" color="tertiary" style={{ marginTop: 2 }}>
          {variant === "expert" ? "Describe it once and an expert will take it from there" : "Choose a service need to continue"}
        </AppText>
      </View>
      {variant === "expert" ? (
        <ExpertList issues={tappable} onPressIssue={onPressIssue} />
      ) : variant === "compact" ? (
        <CompactGrid issues={tappable} onPressIssue={onPressIssue} />
      ) : (
        <ShowcaseRail issues={tappable} onPressIssue={onPressIssue} />
      )}
    </View>
  );
}

function ShowcaseRail({ issues, onPressIssue }: { issues: HomeQuickIssue[]; onPressIssue: (issue: HomeQuickIssue) => void }) {
  const { theme } = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: theme.spacing.sm }}>
      {issues.map((issue, index) => {
        const surfaces = [theme.colors.statusSuccessSurface, theme.colors.statusInfoSurface, theme.colors.statusWarningSurface, theme.colors.surfaceSecondary];
        return (
          <Pressable
            key={issue.issueId}
            onPress={() => onPressIssue(issue)}
            accessibilityRole="button"
            accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
            style={({ pressed }) => ({ width: 176, minHeight: 142, padding: theme.spacing.md, borderRadius: theme.radius.radiusSmall, backgroundColor: surfaces[index % surfaces.length], opacity: pressed ? 0.82 : 1 })}
          >
            <View style={{ flex: 1, justifyContent: "space-between" }}>
              <View style={{ alignSelf: "flex-start", width: 36, height: 4, borderRadius: 2, backgroundColor: theme.colors.brandPrimary }} />
              <View>
                <AppText variant="bodyStrong" numberOfLines={3}>{issue.label}</AppText>
                <AppText variant="caption" color="secondary" style={{ marginTop: 6 }}>Explore →</AppText>
              </View>
            </View>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function ExpertList({ issues, onPressIssue }: { issues: HomeQuickIssue[]; onPressIssue: (issue: HomeQuickIssue) => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
      {issues.map(issue => {
        return (
          <Pressable
            key={issue.issueId}
            onPress={() => onPressIssue(issue)}
            accessibilityRole="button"
            accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
            style={({ pressed }) => ({ minHeight: 74, flexDirection: "row", alignItems: "center", gap: theme.spacing.md, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle, opacity: pressed ? 0.72 : 1 })}
          >
            <View style={{ width: 38, height: 38, alignItems: "center", justifyContent: "center", borderRadius: 19, backgroundColor: theme.colors.surfaceSecondary }}>
              <View style={{ width: 12, height: 12, borderRadius: 6, borderWidth: 3, borderColor: theme.colors.brandPrimary }} />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <AppText variant="bodyStrong" numberOfLines={1}>{issue.label}</AppText>
              <AppText variant="caption" color="secondary" numberOfLines={1}>{issue.categoryName}</AppText>
            </View>
            <AppText variant="bodyStrong" color="tertiary">›</AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

function CompactGrid({ issues, onPressIssue }: { issues: HomeQuickIssue[]; onPressIssue: (issue: HomeQuickIssue) => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
      {issues.map(issue => {
        return (
          <Pressable
            key={issue.issueId}
            onPress={() => onPressIssue(issue)}
            accessibilityRole="button"
            accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
            style={({ pressed }) => ({ width: "48%", minHeight: 76, padding: theme.spacing.sm, justifyContent: "space-between", backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.radiusSmall, opacity: pressed ? 0.8 : 1 })}
          >
            <AppText variant="caption" color="secondary" numberOfLines={1} style={{ fontSize: 9, fontWeight: "800", textTransform: "uppercase" }}>{issue.categoryName}</AppText>
            <AppText variant="caption" numberOfLines={2} style={{ fontWeight: "700" }}>{issue.label}</AppText>
          </Pressable>
        );
      })}
    </View>
  );
}
