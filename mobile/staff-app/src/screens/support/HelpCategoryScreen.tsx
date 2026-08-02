import React from "react";
import { ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState } from "../../design-system/components/feedback/States";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "HelpCategory">;

export function HelpCategoryScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { areaKey, areaLabel } = route.params;
  const query = useQuery({
    queryKey: ["help-category", areaKey],
    queryFn: async () => {
      const result = await api.searchArticles({ area: areaKey });
      if (!result.ok) throw result.error;
      return result.data.articles;
    },
  });

  // "Schedule & leave" shares the real "bookings_jobs" area with "Job
  // execution" -- a client-side keyword filter (never a fabricated backend
  // category) narrows to the relevant subset for that specific tile.
  const isScheduleTile = areaLabel === "Schedule & leave";
  const articles = (query.data ?? []).filter(a =>
    !isScheduleTile || a.keywords.some(k => ["schedule", "leave", "time off", "availability"].includes(k)));

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title={areaLabel} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {query.isLoading ? (
          <Skeleton width="100%" height={300} radius={theme.radiusUsage.card} />
        ) : articles.length === 0 ? (
          <EmptyState icon="document-text-outline" title="No articles yet" message="Content for this category is on its way." />
        ) : (
          <Section>
            {articles.map(article => (
              <Card key={article.id} style={{ marginBottom: theme.spacing.sm }} onTouchEnd={() => navigation.navigate("HelpArticle", { slug: article.slug })}>
                <AppText variant="bodyStrong">{article.title}</AppText>
                {article.summary ? <AppText variant="bodySmall" color="tertiary">{article.summary}</AppText> : null}
              </Card>
            ))}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
