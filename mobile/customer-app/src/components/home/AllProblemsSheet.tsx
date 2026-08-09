import React, { useMemo, useState } from "react";
import { View, Modal, Pressable, ScrollView, TextInput } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";
import { HomeQuickIssue } from "../../domain/customerHome";
import { resolveQuickIssueIcon } from "../../domain/quickIssueIcon";

export interface AllProblemsSheetProps {
  visible: boolean;
  issues: readonly HomeQuickIssue[];
  onClose: () => void;
  onPressIssue: (issue: HomeQuickIssue) => void;
}

/**
 * Every bookable problem, grouped by the service it belongs to.
 *
 * This exists so a customer whose problem is not in the top row never has to
 * back out to the service list and work down from a category -- the whole
 * shortlist and its overflow live in one place. Search filters on the problem
 * and on its service, because someone who thinks "plumbing" should find
 * "Drain Blocked".
 *
 * Only problems the backend already scoped to this ZIP reach here: the sheet
 * cannot widen what is bookable, only make it findable.
 */
export function AllProblemsSheet({ visible, issues, onClose, onPressIssue }: AllProblemsSheetProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const term = query.trim().toLowerCase();
    const matched = term
      ? issues.filter(i =>
          i.label.toLowerCase().includes(term) || i.categoryName.toLowerCase().includes(term))
      : issues;
    // Insertion order is the backend's ordering, so the first group is the
    // first service it listed rather than an alphabetical reshuffle.
    const byCategory = new Map<string, HomeQuickIssue[]>();
    for (const issue of matched) {
      const list = byCategory.get(issue.categoryName) ?? [];
      list.push(issue);
      byCategory.set(issue.categoryName, list);
    }
    return [...byCategory.entries()];
  }, [issues, query]);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
        <Pressable
          style={{ flex: 1 }}
          accessibilityRole="button"
          accessibilityLabel="Close all problems"
          onPress={onClose}
        />
        <View
          style={{
            maxHeight: "85%",
            backgroundColor: theme.colors.surfaceDefault,
            borderTopLeftRadius: theme.radiusUsage.card,
            borderTopRightRadius: theme.radiusUsage.card,
          }}
        >
          <View
            style={{
              flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
              paddingHorizontal: theme.spacing.base,
              paddingTop: theme.spacing.base, paddingBottom: theme.spacing.sm,
            }}
          >
            <View style={{ flex: 1, minWidth: 0 }}>
              <AppText variant="headingSmall">What do you need fixed?</AppText>
              <AppText variant="caption" color="tertiary">
                {`${issues.length} ${issues.length === 1 ? "problem" : "problems"} bookable near you`}
              </AppText>
            </View>
            <AppIconButton name="close" onPress={onClose} accessibilityLabel="Close" />
          </View>

          <View style={{ paddingHorizontal: theme.spacing.base, paddingBottom: theme.spacing.sm }}>
            <View
              style={{
                flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
                minHeight: theme.touchTargets.comfortable,
                paddingHorizontal: theme.spacing.base,
                borderRadius: theme.radiusUsage.input,
                backgroundColor: theme.colors.surfaceSecondary,
              }}
            >
              <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
              <TextInput
                value={query}
                onChangeText={setQuery}
                placeholder="Search a problem or service"
                placeholderTextColor={theme.colors.textTertiary}
                autoCorrect={false}
                accessibilityLabel="Search problems"
                style={{ flex: 1, color: theme.colors.textPrimary, ...theme.typography.body }}
              />
              {query.length > 0 ? (
                <Pressable
                  onPress={() => setQuery("")}
                  accessibilityRole="button"
                  accessibilityLabel="Clear search"
                  hitSlop={8}
                >
                  <Icon name="close-circle" size="compact" color={theme.colors.iconDefault} decorative />
                </Pressable>
              ) : null}
            </View>
          </View>

          <ScrollView
            style={{ flexGrow: 0 }}
            contentContainerStyle={{ paddingBottom: theme.spacing.base + insets.bottom }}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {groups.length === 0 ? (
              // Says what was searched for, so it reads as "no match for that"
              // rather than "nothing is available".
              <View style={{ paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.lg, gap: theme.spacing.xxs }}>
                <AppText variant="bodyStrong">{`No problem matches "${query.trim()}"`}</AppText>
                <AppText variant="bodySmall" color="secondary">
                  Try a different word, or start a chat and describe it in your own words.
                </AppText>
              </View>
            ) : (
              groups.map(([categoryName, list]) => (
                <View key={categoryName}>
                  <View
                    style={{
                      paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.xs,
                      backgroundColor: theme.colors.surfaceSecondary,
                    }}
                  >
                    <AppText variant="labelStrong" color="secondary">{categoryName}</AppText>
                  </View>
                  {list.map(issue => {
                    const glyph = resolveQuickIssueIcon(issue.label, issue.categoryName);
                    return (
                      <Pressable
                        key={issue.issueId}
                        onPress={() => onPressIssue(issue)}
                        accessibilityRole="button"
                        accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
                        style={({ pressed }) => ({
                          flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
                          paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
                          borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle,
                          backgroundColor: pressed ? theme.colors.surfaceSecondary : "transparent",
                        })}
                      >
                        <View
                          style={{
                            width: 36, height: 36, borderRadius: theme.radiusUsage.input,
                            alignItems: "center", justifyContent: "center",
                            backgroundColor: `${glyph.tint}1A`,
                          }}
                        >
                          <Icon name={glyph.name} size="compact" color={glyph.tint} decorative />
                        </View>
                        <AppText variant="body" style={{ flex: 1 }} numberOfLines={2}>{issue.label}</AppText>
                        <Icon name="chevron-forward" size="compact" color={theme.colors.iconDefault} decorative />
                      </Pressable>
                    );
                  })}
                </View>
              ))
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
