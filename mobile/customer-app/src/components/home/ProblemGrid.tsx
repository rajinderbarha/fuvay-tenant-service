import React from "react";
import { Pressable, ScrollView, View } from "react-native";

import { useTheme } from "../../design-system/theme";
import { HomeQuickIssue } from "../../domain/customerHome";
import { AppText } from "../AppText";

export interface ProblemGridProps {
  issues: readonly HomeQuickIssue[];
  title?: string | null;
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/** Asymmetric problem picker: one editorial lead and a compact swipe rail. */
export function ProblemGrid({ issues, title, onPressIssue }: ProblemGridProps) {
  const { theme } = useTheme();
  const tappable = issues.filter(issue => !!issue.categorySlug);
  const [lead, ...rest] = tappable;
  if (!lead) return null;

  return (
    <View>
      <View style={{ marginBottom: theme.spacing.md }}>
        <AppText variant="headingSmall">{title || "What's the problem?"}</AppText>
        <AppText variant="caption" color="tertiary" style={{ marginTop: 2 }}>
          Pick the closest match. We will ask only what is needed.
        </AppText>
      </View>

      <LeadProblem issue={lead} onPress={() => onPressIssue(lead)} />

      {rest.length > 0 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingTop: theme.spacing.sm, gap: theme.spacing.sm }}>
          {rest.map((issue, index) => (
            <ProblemCard key={issue.issueId} issue={issue} index={index} onPress={() => onPressIssue(issue)} />
          ))}
        </ScrollView>
      ) : null}
    </View>
  );
}

function LeadProblem({ issue, onPress }: { issue: HomeQuickIssue; onPress: () => void }) {
  const { theme } = useTheme();

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
      accessibilityHint="Opens the booking assistant with this problem selected"
      style={({ pressed }) => ({
        minHeight: 126,
        borderRadius: theme.radius.radiusSmall,
        backgroundColor: theme.colors.surfaceSecondary,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        opacity: pressed ? 0.84 : 1,
      })}
    >
      <View style={{ padding: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <AppText variant="caption" color="secondary" style={{ fontWeight: "800", letterSpacing: 0.8 }}>MOST RELEVANT</AppText>
          <View style={{ width: 34, height: 3, borderRadius: 2, backgroundColor: theme.colors.brandPrimary }} />
        </View>
        <AppText variant="title" numberOfLines={2} style={{ marginTop: theme.spacing.sm }}>{issue.label}</AppText>
        <View style={{ marginTop: theme.spacing.sm, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <AppText variant="caption" color="secondary">{issue.categoryName}</AppText>
          <AppText variant="bodySmall" style={{ fontWeight: "800" }}>Start booking →</AppText>
        </View>
      </View>
    </Pressable>
  );
}

function ProblemCard({ issue, index, onPress }: { issue: HomeQuickIssue; index: number; onPress: () => void }) {
  const { theme } = useTheme();
  const accentSurfaces = [theme.colors.statusInfoSurface, theme.colors.statusSuccessSurface, theme.colors.statusWarningSurface, theme.colors.accentVioletSurface];

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
      accessibilityHint="Opens the booking assistant with this problem selected"
      style={({ pressed }) => ({
        width: 172,
        minHeight: 126,
        overflow: "hidden",
        borderRadius: theme.radius.radiusSmall,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        opacity: pressed ? 0.82 : 1,
      })}
    >
      <View style={{ flex: 1, padding: theme.spacing.md, backgroundColor: accentSurfaces[index % accentSurfaces.length], justifyContent: "space-between" }}>
        <View style={{ alignSelf: "flex-start", paddingHorizontal: 7, paddingVertical: 3, borderRadius: 3, backgroundColor: theme.colors.surfaceDefault }}>
          <AppText variant="caption" color="secondary" numberOfLines={1} style={{ fontSize: 9, fontWeight: "800", textTransform: "uppercase" }}>{issue.categoryName}</AppText>
        </View>
        <View>
          <AppText variant="bodyStrong" numberOfLines={3} style={{ lineHeight: 19 }}>{issue.label}</AppText>
          <AppText variant="caption" color="secondary" numberOfLines={1} style={{ marginTop: 5, fontWeight: "700" }}>Book this service â†’</AppText>
        </View>
      </View>
    </Pressable>
  );
}
