import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextArea } from "../../design-system/components/forms/TextArea";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "SupportRequestDetail">;

const formatDateTime = (iso: string) => new Date(iso).toLocaleString();

/**
 * Support Request Detail (Phase Y spec section 12). Renders the real
 * backend lifecycle/conversation -- never unrestricted chat. A technician
 * may add information but cannot set their own request to resolved (the
 * real `confirm-resolution` endpoint only accepts an already-resolved
 * ticket, enforced server-side).
 */
export function SupportRequestDetailScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { requestId } = route.params;
  const queryClient = useQueryClient();
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["support-request", requestId],
    queryFn: async () => {
      const result = await api.getRequestDetail(requestId);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const handleReply = async () => {
    if (!reply.trim()) return;
    setBusy(true);
    setError(null);
    const result = await api.replyToRequest(requestId, reply.trim());
    setBusy(false);
    if (result.ok) {
      setReply("");
      queryClient.invalidateQueries({ queryKey: ["support-request", requestId] });
    } else {
      setError(result.error.safeMessage);
    }
  };

  const handleConfirmResolution = async () => {
    setBusy(true);
    setError(null);
    const result = await api.confirmResolution(requestId);
    setBusy(false);
    if (result.ok) queryClient.invalidateQueries({ queryKey: ["support-request", requestId] });
    else setError(result.error.safeMessage);
  };

  if (query.isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Request detail" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={300} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (query.isError || !query.data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Request detail" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load request" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
      </SafeAreaScreen>
    );
  }

  const req = query.data;
  const canReply = !["closed", "withdrawn"].includes(req.status);
  const canConfirmResolution = req.status === "resolved";

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title={req.ticket_number} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete action" message={error} /></View> : null}

        <Section>
          <Card>
            <AppText variant="bodyStrong">{req.subject}</AppText>
            <View style={{ marginTop: theme.spacing.xs, alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusInfoSurface }}>
              <AppText variant="labelStrong" color="info">{req.status_label}</AppText>
            </View>
            <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.sm }}>{req.description}</AppText>
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Details" />
          <Card>
            <KeyValueList items={[
              { label: "Category", value: req.category_label }, { label: "Impact", value: req.impact_label },
              { label: "Created", value: formatDateTime(req.created_at) }, { label: "SLA", value: req.sla_display },
            ]} />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Conversation" />
          <Card padding="base">
            {req.conversation.length === 0 ? (
              <AppText variant="bodySmall" color="tertiary">No messages yet.</AppText>
            ) : req.conversation.map(msg => (
              <View key={msg.id} style={{ marginBottom: theme.spacing.sm }}>
                <AppText variant="labelStrong">{msg.author_type === "serviceos" ? "ServiceOS Support" : msg.author_name ?? "You"}</AppText>
                <AppText variant="bodySmall">{msg.body}</AppText>
                <AppText variant="caption" color="tertiary">{formatDateTime(msg.created_at)}</AppText>
              </View>
            ))}
          </Card>
        </Section>

        {canReply ? (
          <Section>
            <TextArea label="Add information" value={reply} onChangeText={setReply} minLines={3} />
            <View style={{ height: theme.spacing.sm }} />
            <PrimaryButton label="Send" onPress={handleReply} loading={busy} disabled={!reply.trim()} fullWidth />
          </Section>
        ) : null}

        {canConfirmResolution ? (
          <SecondaryButton label="Confirm resolved" onPress={handleConfirmResolution} loading={busy} fullWidth />
        ) : null}
      </ScrollView>
    </SafeAreaScreen>
  );
}
