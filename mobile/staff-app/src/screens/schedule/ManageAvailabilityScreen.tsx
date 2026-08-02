import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { TextField } from "../../design-system/components/forms/TextField";
import { TertiaryButton, PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { AvailabilitySelector } from "../home/components/AvailabilitySelector";
import { useTechnicianHome } from "../home/useTechnicianHome";
import { useSchedule } from "./useSchedule";
import { ScheduleStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ScheduleStackParamList, "ManageAvailability">;

/**
 * Manage Availability (Phase P spec section 5). Recurring working hours
 * and tenant/system-created blocks are server-authoritative, read-only
 * here -- only technician-created ad-hoc blocks can be added/removed.
 * Live presence reuses the exact existing selector, never duplicated.
 */
export function ManageAvailabilityScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { data: homeData, updateAvailability } = useTechnicianHome();
  const { data, addBlockedTime, mutating, mutationError } = useSchedule(new Date());
  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [reason, setReason] = useState("");

  const valid = /^\d{4}-\d{2}-\d{2}$/.test(date) && /^\d{2}:\d{2}$/.test(startTime) && /^\d{2}:\d{2}$/.test(endTime);

  const handleAdd = async () => {
    const result = await addBlockedTime({ date, start_time: startTime, end_time: endTime, reason: reason.trim() || undefined });
    if (result.ok) { setDate(""); setStartTime(""); setEndTime(""); setReason(""); }
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={() => navigation.goBack()} />
        <AppText variant="bodyStrong" style={{ flex: 1, textAlign: "center" }}>Manage availability</AppText>
        <View style={{ width: 44 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't add blocked time" message={mutationError.safeMessage} /></View> : null}

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Live presence</AppText>
          <Card>
            <AvailabilitySelector state={homeData?.availability?.state ?? "available"} onChange={updateAvailability} />
          </Card>
        </Section>

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Recurring working hours</AppText>
          <Card>
            {data && data.days.length > 0 ? (
              data.days.map(d => (
                <AppText key={d.date} variant="bodySmall" color="secondary">{d.date}: {d.working_hours_label ?? "Not configured"}</AppText>
              ))
            ) : (
              <AppText variant="bodySmall" color="tertiary">No recurring pattern configured. Contact your tenant to set working hours.</AppText>
            )}
          </Card>
        </Section>

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Add blocked time</AppText>
          <Card>
            <TextField label="Date (YYYY-MM-DD)" value={date} onChangeText={setDate} placeholder="2026-08-05" />
            <View style={{ height: theme.spacing.sm }} />
            <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              <View style={{ flex: 1 }}><TextField label="Start (HH:MM)" value={startTime} onChangeText={setStartTime} placeholder="14:00" /></View>
              <View style={{ flex: 1 }}><TextField label="End (HH:MM)" value={endTime} onChangeText={setEndTime} placeholder="15:00" /></View>
            </View>
            <View style={{ height: theme.spacing.sm }} />
            <TextField label="Reason (optional)" value={reason} onChangeText={setReason} placeholder="Personal" />
            <View style={{ height: theme.spacing.base }} />
            <PrimaryButton label="Add blocked time" onPress={handleAdd} disabled={!valid} loading={mutating} fullWidth />
          </Card>
          <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
            A block cannot be added over an already-assigned job -- the server will reject the conflict and show the job.
          </AppText>
        </Section>
      </ScrollView>
    </SafeAreaScreen>
  );
}
