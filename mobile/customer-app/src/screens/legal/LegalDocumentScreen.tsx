import React from "react";
import { View } from "react-native";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";

import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { useLegalDocumentQuery } from "../../api/legalDocuments/useLegalDocumentQueries";

/**
 * Renders a published legal document from /v1/public/legal/{doc_type}.
 *
 * Reads the document natively rather than opening a browser. The previous
 * design opened `EXPO_PUBLIC_TERMS_URL` / `EXPO_PUBLIC_PRIVACY_URL`, which
 * were never configured — so the footer links did nothing at all and the
 * profile rows were hidden entirely. There is no public web page to point at,
 * and the app already talks to the API, so it renders the text itself.
 */

export type LegalDocumentRouteParams = { docType: string; title?: string };

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

function formatEffective(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
}

export function LegalDocumentScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<RouteProp<Record<string, LegalDocumentRouteParams>, string>>();
  const docType = route.params?.docType;
  const fallbackTitle = route.params?.title ?? "Legal";

  const query = useLegalDocumentQuery(docType);

  const header = (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">
          {query.data?.title ?? fallbackTitle}
        </AppText>
        {query.data ? (
          <AppText variant="caption" color="tertiary">
            Version {query.data.version}
            {formatEffective(query.data.effective_at)
              ? ` · in force since ${formatEffective(query.data.effective_at)}`
              : ""}
          </AppText>
        ) : null}
      </View>
    </View>
  );

  if (query.isPending) {
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          {header}
          <LoadingState label="Loading…" />
        </View>
      </AppScreen>
    );
  }

  if (query.isError || !query.data) {
    // Says so plainly rather than showing a bundled copy. A second copy of
    // the Terms shipped in the app would drift from the published version
    // and nobody would notice.
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          {header}
          <ErrorState
            title="We couldn't load this document."
            actionLabel="Try again"
            onAction={() => query.refetch()}
          />
        </View>
      </AppScreen>
    );
  }

  const blocks = parseLegalMarkdown(query.data.body);

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        {header}

        {query.data.summary ? (
          <AppText variant="bodySmall" color="secondary">{query.data.summary}</AppText>
        ) : null}

        <View style={{ gap: theme.spacing.sm }}>
          {blocks.map((block, i) => {
            if (block.kind === "heading") {
              return (
                <AppText
                  key={i}
                  variant="titleSmall"
                  accessibilityRole="header"
                  style={{ marginTop: theme.spacing.sm }}
                >
                  {block.text}
                </AppText>
              );
            }
            if (block.kind === "bullet") {
              return (
                <View key={i} style={{ flexDirection: "row", gap: theme.spacing.xs, paddingLeft: theme.spacing.sm }}>
                  <AppText variant="body" color="secondary">•</AppText>
                  <AppText variant="body" color="secondary" style={{ flex: 1 }}>{block.text}</AppText>
                </View>
              );
            }
            return (
              <AppText key={i} variant="body" color="secondary">{block.text}</AppText>
            );
          })}
        </View>
      </View>
    </AppScreen>
  );
}
