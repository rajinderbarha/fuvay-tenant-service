import React from "react";
import { View, ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import * as legalApi from "../../services/legal/legalApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "LegalDocumentDetail">;

type Block =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "bullet"; text: string };

/**
 * The same narrow Markdown subset the authoring console documents: `##`
 * headings, paragraphs and `-` bullets. The text is written by the platform
 * team, not by users, so a full Markdown engine is not worth the bundle.
 */
export function parseLegalMarkdown(markdown: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];

  const flush = () => {
    if (paragraph.length) {
      blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  };

  for (const raw of markdown.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) { flush(); continue; }

    const heading = /^#{1,6}\s+(.*)$/.exec(line);
    if (heading) { flush(); blocks.push({ kind: "heading", text: heading[1] }); continue; }

    const bullet = /^[-*]\s+(.*)$/.exec(line);
    if (bullet) { flush(); blocks.push({ kind: "bullet", text: bullet[1] }); continue; }

    paragraph.push(line);
  }
  flush();
  return blocks;
}

/** Renders one published legal document from /v1/public/legal/{doc_type}. */
export function LegalDocumentDetailScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { docType, title } = route.params;

  const query = useQuery({
    queryKey: ["legal", "document", docType, legalApi.STAFF_AUDIENCE],
    queryFn: async () => {
      const result = await legalApi.getLegalDocument(docType);
      if (!result.ok) throw result.error;
      return result.data;
    },
    staleTime: 60 * 60 * 1000,
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title={query.data?.title ?? title ?? "Legal"} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {query.isLoading ? (
          <Skeleton width="100%" height={400} radius={theme.radiusUsage.card} />
        ) : query.isError || !query.data ? (
          // Says so plainly rather than showing a bundled copy — a second copy
          // of the Terms shipped in the app would drift from the published
          // version and nobody would notice.
          <ErrorState
            icon="cloud-offline-outline"
            title="Couldn't load this document"
            message="Please try again."
            actionLabel="Retry"
            onAction={() => query.refetch()}
          />
        ) : (
          <Section>
            <AppText variant="caption" color="tertiary">
              Version {query.data.version}
              {query.data.effective_at
                ? ` · in force since ${new Date(query.data.effective_at).toLocaleDateString()}`
                : ""}
            </AppText>
            {query.data.summary ? (
              <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.sm }}>
                {query.data.summary}
              </AppText>
            ) : null}

            {parseLegalMarkdown(query.data.body).map((block, i) => {
              if (block.kind === "heading") {
                return (
                  <AppText key={i} variant="bodyStrong" style={{ marginTop: theme.spacing.base }}>
                    {block.text}
                  </AppText>
                );
              }
              if (block.kind === "bullet") {
                return (
                  <View key={i} style={{ flexDirection: "row", gap: theme.spacing.xs, marginTop: theme.spacing.xs, paddingLeft: theme.spacing.sm }}>
                    <AppText variant="bodySmall" color="secondary">•</AppText>
                    <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>{block.text}</AppText>
                  </View>
                );
              }
              return (
                <AppText key={i} variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xs }}>
                  {block.text}
                </AppText>
              );
            })}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
