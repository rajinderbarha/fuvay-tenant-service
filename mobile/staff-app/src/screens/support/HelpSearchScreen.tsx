import React, { useEffect, useState } from "react";
import { View, ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextField } from "../../design-system/components/forms/TextField";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState } from "../../design-system/components/feedback/States";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "HelpSearch">;

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 350;

/** Help Search (Phase Y spec section 7). Debounced, minimum-length, stale
 * requests superseded by TanStack Query's own query-key change (never a
 * manually-tracked race condition). */
export function HelpSearchScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [input, setInput] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(input.trim()), DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [input]);

  const query = useQuery({
    queryKey: ["help-search", debounced],
    queryFn: async ({ signal }) => {
      const result = await api.searchArticles({ search: debounced }, signal);
      if (!result.ok) throw result.error;
      return result.data.articles;
    },
    enabled: debounced.length >= MIN_QUERY_LENGTH,
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Search help" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <TextField label="" placeholder="Search help articles" value={input} onChangeText={setInput} autoFocus />
        <View style={{ height: theme.spacing.base }} />

        {debounced.length < MIN_QUERY_LENGTH ? (
          <AppText variant="bodySmall" color="tertiary">Type at least {MIN_QUERY_LENGTH} characters to search.</AppText>
        ) : query.isLoading ? (
          <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState icon="search-outline" title="No results" message="Try a different word, or create a support request." />
        ) : (
          <Section>
            {query.data.map(article => (
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
