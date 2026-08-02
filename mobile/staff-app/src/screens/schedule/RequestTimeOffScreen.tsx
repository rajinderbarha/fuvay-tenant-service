import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { TextField } from "../../design-system/components/forms/TextField";
import { TextArea } from "../../design-system/components/forms/TextArea";
import { Switch } from "../../design-system/components/forms/Switch";
import { SegmentedControl } from "../../design-system/components/forms/SegmentedControl";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useSchedule } from "./useSchedule";
import { ScheduleStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ScheduleStackParamList, "RequestTimeOff">;

const REASON_OPTIONS = [
  { value: "personal", label: "Personal" },
  { value: "medical", label: "Medical" },
  { value: "family", label: "Family" },
  { value: "other", label: "Other" },
];

/**
 * Request Time Off (Phase P spec section 6). The technician only submits;
 * approval is a separate tenant-owner action this screen never performs.
 */
export function RequestTimeOffScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { submitTimeOff, mutating, mutationError } = useSchedule(new Date());
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isFullDay, setIsFullDay] = useState(true);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [reasonCategory, setReasonCategory] = useState("personal");
  const [note, setNote] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const dateValid = /^\d{4}-\d{2}-\d{2}$/.test(startDate) && /^\d{4}-\d{2}-\d{2}$/.test(endDate);
  const timeValid = isFullDay || (/^\d{2}:\d{2}$/.test(startTime) && /^\d{2}:\d{2}$/.test(endTime));
  const valid = dateValid && timeValid;

  const handleSubmit = async () => {
    const result = await submitTimeOff({
      start_date: startDate, end_date: endDate, is_full_day: isFullDay,
      start_time: isFullDay ? undefined : startTime, end_time: isFullDay ? undefined : endTime,
      reason_category: reasonCategory, note: note.trim() || undefined,
    });
    if (result.ok) setSubmitted(true);
  };

  if (submitted) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <View style={{ alignItems: "center", padding: theme.spacing.xxl }}>
          <AppText variant="title">Request submitted</AppText>
          <AppText color="secondary" style={{ textAlign: "center", marginTop: theme.spacing.xs }}>
            Your tenant will review this request. It's shown as pending until decided.
          </AppText>
          <View style={{ height: theme.spacing.lg }} />
          <PrimaryButton label="Back to schedule" onPress={() => navigation.goBack()} />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={() => navigation.goBack()} />
        <AppText variant="bodyStrong" style={{ flex: 1, textAlign: "center" }}>Request time off</AppText>
        <View style={{ width: 44 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't submit request" message={mutationError.safeMessage} /></View> : null}

        <Section>
          <Card>
            <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              <View style={{ flex: 1 }}><TextField label="Start date" value={startDate} onChangeText={setStartDate} placeholder="2026-08-10" /></View>
              <View style={{ flex: 1 }}><TextField label="End date" value={endDate} onChangeText={setEndDate} placeholder="2026-08-10" /></View>
            </View>
            <View style={{ height: theme.spacing.sm }} />
            <Switch label="Full day" value={isFullDay} onChange={setIsFullDay} />
            {!isFullDay ? (
              <>
                <View style={{ height: theme.spacing.sm }} />
                <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
                  <View style={{ flex: 1 }}><TextField label="Start time" value={startTime} onChangeText={setStartTime} placeholder="09:00" /></View>
                  <View style={{ flex: 1 }}><TextField label="End time" value={endTime} onChangeText={setEndTime} placeholder="13:00" /></View>
                </View>
              </>
            ) : null}
          </Card>
        </Section>

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Reason</AppText>
          <SegmentedControl options={REASON_OPTIONS} value={reasonCategory} onChange={setReasonCategory} />
        </Section>

        <Section>
          <TextArea label="Note (optional)" value={note} onChangeText={setNote} placeholder="Add any additional context…" minLines={3} />
        </Section>

        <PrimaryButton label="Submit request" onPress={handleSubmit} disabled={!valid} loading={mutating} fullWidth />
      </ScrollView>
    </SafeAreaScreen>
  );
}
