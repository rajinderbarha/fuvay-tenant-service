import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppInput } from "../../components/AppInput";
import { AppIconButton } from "../../components/AppIconButton";
import { useCreateSupportRequestMutation } from "../../api/supportRequests/useSupportRequestsQueries";
import { SUPPORT_REQUEST_TYPES, supportRequestTypeLabel } from "../../domain/supportRequestPresentation";
import { SAFETY_CONCERN_TYPE } from "../../domain/supportRequests";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { isOffline } from "../../api/networkState";
import { DomainError } from "../../domain/errors";
import { Pressable } from "react-native";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "SafetyReport">;

/**
 * Real-backend creation form (`POST /v1/customer/complaints`), used only
 * by `SafetyReportScreen` now (`presetComplaintType="safety_concern"`,
 * locked). The general "Create request" flow was replaced by the 3-step
 * wizard (`CreateSupportRequestTopicScreen` + friends) -- this component
 * itself is unchanged, just no longer reachable via the plain
 * "CreateSupportRequest" route. Only fields the real schema accepts are
 * ever sent: `record_type` (hardcoded "service_booking" -- the picker
 * only ever selects a booking), `record_id`, `complaint_type`,
 * `description`. No category/priority/SLA/agent-assignment is invented.
 */
export function SupportRequestForm({ bookingId, presetComplaintType }: { bookingId: string; presetComplaintType?: string }) {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const isSafetyFlow = presetComplaintType === SAFETY_CONCERN_TYPE;
  const createMutation = useCreateSupportRequestMutation();

  const [complaintType, setComplaintType] = useState<string>(presetComplaintType ?? "");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const offline = isOffline();

  async function handleSubmit() {
    if (offline) {
      setError("Connect to the internet to submit this request.");
      return;
    }
    setError(null);
    try {
      const res = await createMutation.mutateAsync({
        record_type: "service_booking", record_id: bookingId,
        complaint_type: complaintType, description: description.trim(),
      });
      navigation.replace("SupportRequestDetails", { requestId: res.data.id });
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't submit your request.");
    }
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">
              {isSafetyFlow ? "Report a safety concern" : "Create a request"}
            </AppText>
            <AppText variant="bodySmall" color="secondary">
              {isSafetyFlow ? "Tell us what happened. Your account remains active." : "Tell us what happened with this booking."}
            </AppText>
          </View>
        </View>

        {!isSafetyFlow ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">What's this about?</AppText>
            <AppCard style={{ gap: 0 }}>
              {SUPPORT_REQUEST_TYPES.map((type, i) => (
                <Pressable
                  key={type}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: complaintType === type }}
                  accessibilityLabel={supportRequestTypeLabel(type)}
                  onPress={() => setComplaintType(type)}
                  style={{
                    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                    paddingVertical: theme.spacing.sm,
                    borderTopWidth: i > 0 ? 1 : 0, borderTopColor: theme.colors.borderSubtle,
                  }}
                >
                  <AppText variant="bodySmall">{supportRequestTypeLabel(type)}</AppText>
                  {complaintType === type ? (
                    <AppText variant="bodyStrong" color="link">✓</AppText>
                  ) : null}
                </Pressable>
              ))}
            </AppCard>
          </View>
        ) : null}

        <AppInput
          label="Description" value={description} onChangeText={t => { setDescription(t); setError(null); }}
          accessibilityLabel="Description" multiline editable={!createMutation.isPending} maxLength={2000}
        />

        {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}

        <AppButton
          label={isSafetyFlow ? "Submit report" : "Submit request"} tone={isSafetyFlow ? "destructive" : "primary"}
          onPress={handleSubmit} loading={createMutation.isPending}
          disabled={!complaintType || !description.trim() || offline} fullWidth
        />
      </View>
    </AppScreen>
  );
}
