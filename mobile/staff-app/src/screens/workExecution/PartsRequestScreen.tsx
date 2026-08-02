import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { EmptyState } from "../../design-system/components/feedback/States";
import { RetryState } from "../../design-system/components/feedback/States";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { RequestPartSheet } from "./components/RequestPartSheet";
import { useWorkExecution } from "./useWorkExecution";
import { PartsRequestStatus } from "../../services/workExecution/types";
import { MobileHeader } from "../../design-system/components/navigation";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "PartsRequest">;

const STATUS_LABEL: Record<PartsRequestStatus, string> = {
  requested: "Waiting for tenant approval",
  business_approved: "Approved -- ready to install",
  customer_approval_pending: "Waiting for customer approval",
  customer_approved: "Customer approved -- ready to install",
  business_rejected: "Rejected by tenant",
  customer_rejected: "Rejected by customer",
  installed: "Installed",
  cancelled: "Cancelled",
};

const STATUS_TONE: Record<PartsRequestStatus, "neutral" | "success" | "warning" | "danger"> = {
  requested: "warning", business_approved: "success", customer_approval_pending: "warning",
  customer_approved: "success", business_rejected: "danger", customer_rejected: "danger",
  installed: "success", cancelled: "neutral",
};

/**
 * Dedicated Parts Request screen (closes the Final-Phase certification's
 * placeholder finding: this route previously rendered only
 * FeaturePlaceholderScreen despite a real create-part flow already
 * existing as an in-sheet action inside Work Execution). Reuses the SAME
 * real projection (`GET .../mobile-work-execution`'s `parts` array) --
 * no new backend endpoint, no second parts-tracking system. The
 * technician can view every real part request's real status here and
 * submit a new one; approval/rejection/install decisions remain entirely
 * server-driven and tenant-owned (never self-approved here).
 */
export function PartsRequestScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId } = route.params;
  const { data, isLoading, isError, error, refetch, requestPart, mutating, mutationError } = useWorkExecution(jobId);
  const [sheetVisible, setSheetVisible] = useState(false);

  const goBack = () => navigation.navigate("JobDetail", { jobId });

  const handleSubmit = async (body: { part_name: string; quantity: number; estimated_cost: number; reason: string }) => {
    const result = await requestPart(body);
    if (result.ok) setSheetVisible(false);
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <MobileHeader title="Parts requests" onBack={goBack} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {isLoading ? (
          <Section><Skeleton height={72} /><View style={{ height: theme.spacing.sm }} /><Skeleton height={72} /></Section>
        ) : isError ? (
          <RetryState title="Couldn't load parts requests" message={error?.safeMessage} onRetry={() => refetch()} />
        ) : !data ? null : data.parts.length === 0 ? (
          <EmptyState icon="construct-outline" title="No parts requested yet" message="Request a part if this job needs materials the tenant needs to approve." />
        ) : (
          <Section>
            {data.parts.map(part => (
              <Card key={part.parts_request_id} style={{ marginBottom: theme.spacing.sm }}>
                <AppText variant="bodyStrong">{part.part_name}</AppText>
                <AppText variant="caption" color="tertiary">Qty {part.quantity} -- ₹{part.estimated_cost}</AppText>
                <AppText variant="bodySmall" color="secondary" style={{ marginTop: 4 }}>{part.reason}</AppText>
                <View style={{ marginTop: theme.spacing.xs }}>
                  <InlineAlert
                    tone={STATUS_TONE[part.status]}
                    message={part.status === "business_rejected" || part.status === "customer_rejected"
                      ? `${STATUS_LABEL[part.status]}${part.rejection_reason ? `: ${part.rejection_reason}` : ""}`
                      : STATUS_LABEL[part.status]}
                  />
                </View>
              </Card>
            ))}
          </Section>
        )}

        {mutationError ? <InlineAlert tone="danger" title="Couldn't submit request" message={mutationError.safeMessage} /> : null}

        {data && !data.job.is_terminal ? (
          <PrimaryButton label="Request a part" onPress={() => setSheetVisible(true)} fullWidth />
        ) : null}
      </ScrollView>

      <RequestPartSheet
        visible={sheetVisible}
        onClose={() => setSheetVisible(false)}
        onSubmit={handleSubmit}
        submitting={mutating}
      />
    </SafeAreaScreen>
  );
}
