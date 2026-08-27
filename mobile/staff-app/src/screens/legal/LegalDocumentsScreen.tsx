import React from "react";
import { ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import { ListRow } from "../../design-system/components/data-display/InfoRow";
import * as legalApi from "../../services/legal/legalApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "LegalDocuments">;

/**
 * Index of the legal documents currently in force.
 *
 * The backend returns only document types that actually have a published,
 * already-effective version, so every row here is guaranteed to open real
 * text rather than an empty screen.
 */
export function LegalDocumentsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const query = useQuery({
    queryKey: ["legal", "index", legalApi.STAFF_AUDIENCE],
    queryFn: async () => {
      const result = await legalApi.listLegalDocuments();
      if (!result.ok) throw result.error;
      return result.data.documents;
    },
    // Published legal text changes on the order of months; re-fetching it on
    // every visit would be pure waste.
    staleTime: 60 * 60 * 1000,
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Legal" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {query.isLoading ? (
          <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
        ) : query.isError ? (
          <ErrorState
            icon="cloud-offline-outline"
            title="Couldn't load documents"
            message="Please try again."
            actionLabel="Retry"
            onAction={() => query.refetch()}
          />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState
            icon="document-text-outline"
            title="Nothing published yet"
            message="Legal documents will appear here once they are published."
          />
        ) : (
          <Section>
            <Card padding="base">
              {query.data.map(doc => (
                <ListRow
                  key={doc.doc_type}
                  title={doc.title}
                  subtitle={`Version ${doc.version}`}
                  onPress={() => navigation.navigate("LegalDocumentDetail", {
                    docType: doc.doc_type,
                    title: doc.title,
                  })}
                />
              ))}
            </Card>
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
