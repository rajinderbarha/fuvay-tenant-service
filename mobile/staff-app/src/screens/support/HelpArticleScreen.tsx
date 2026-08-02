import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { SecondaryButton } from "../../design-system/components/actions/Buttons";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "HelpArticle">;

/** Help Article (Phase Y). No article-detail-by-slug endpoint exists
 * server-side (confirmed by audit) -- the list endpoint already returns
 * full bodies, so this screen fetches the same list and finds its article,
 * rather than inventing a new backend route. */
export function HelpArticleScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { slug } = route.params;
  const [feedbackGiven, setFeedbackGiven] = useState<"helpful" | "not_helpful" | null>(null);

  const query = useQuery({
    queryKey: ["help-article", slug],
    queryFn: async () => {
      const result = await api.searchArticles({ search: slug });
      if (!result.ok) throw result.error;
      return result.data.articles.find(a => a.slug === slug) ?? null;
    },
  });

  const handleFeedback = async (helpful: boolean) => {
    if (!query.data) return;
    setFeedbackGiven(helpful ? "helpful" : "not_helpful");
    await api.submitArticleFeedback(query.data.id, helpful);
  };

  if (query.isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Article" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={300} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (!query.data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Article" onBack={() => navigation.goBack()} />
        <ErrorState icon="document-text-outline" title="Article not found" message="This article may have been moved or unpublished." actionLabel="Retry" onAction={() => query.refetch()} />
      </SafeAreaScreen>
    );
  }

  const article = query.data;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Article" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <AppText variant="title">{article.title}</AppText>
          {article.summary ? <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs }}>{article.summary}</AppText> : null}
        </Section>
        <Section>
          <Card>
            <AppText variant="body">{article.body ?? "Content unavailable."}</AppText>
          </Card>
        </Section>
        <Section>
          {feedbackGiven ? (
            <AppText variant="bodySmall" color="success">Thanks for your feedback.</AppText>
          ) : (
            <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              <AppText variant="bodySmall" color="tertiary" style={{ alignSelf: "center" }}>Was this helpful?</AppText>
              <SecondaryButton label="Yes" onPress={() => handleFeedback(true)} />
              <SecondaryButton label="No" onPress={() => handleFeedback(false)} />
            </View>
          )}
        </Section>
      </ScrollView>
    </SafeAreaScreen>
  );
}
