import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useAppTheme } from "../../context/ThemeContext";
import { ThemeToggle } from "../../components/ux05/ThemeToggle";
import { PipelineBadge } from "../../components/ux05/PipelineBadge";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";
import { NetworkStatusBanner } from "../../components/ux05/NetworkStatusBanner";

/**
 * Dev-only showcase demonstrating the real dark-theme mechanism (workstream
 * 29) -- every element below is a real, currently-theme-reactive component,
 * not a static mockup. Toggling Light/Dark/System via ThemeToggle above
 * immediately re-renders everything below it.
 */
export function ThemeShowcaseScreen() {
  const { colors, scheme } = useAppTheme();
  return (
    <ScrollView style={{ flex:1, backgroundColor:colors.bg }} contentContainerStyle={s.content} testID="theme-showcase">
      <ThemeToggle />
      <View style={[s.card, { backgroundColor:colors.surface }]}>
        <Text style={[s.label, { color:colors.textPrimary }]}>Resolved scheme: {scheme}</Text>
        <PipelineBadge provenance={{ pipeline:"service_booking_service_job", sourceBookingId:"bk_theme_demo", jobId:"sj_1", jobModel:"ServiceJob" }} />
      </View>
      <NetworkStatusBanner state={{ meta:{readiness:"mock_design_only"}, networkState:"offline", cacheState:"stale_cached", pendingDrafts:0, syncState:"idle" }} />
      <PermissionRestrictedState reason="Example restricted state under the current theme." />
      <Text style={[s.note, { color:colors.textTertiary }]}>
        Reactive: PipelineBadge, PermissionRestrictedState, NetworkStatusBanner, NotificationCard, AvailabilityControl,
        ThemeToggle, both tab navigators, and AppNavigator's header/nav chrome. Not yet converted: most pre-existing
        screens (Home, JobsList, JobDetail, Profile's remaining sections, etc.) -- see light-dark-theme-report.md.
      </Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding:16, gap:12, paddingBottom:32 },
  card:    { borderRadius:12, padding:16, gap:8 },
  label:   { fontSize:14, fontWeight:"700" },
  note:    { fontSize:11, lineHeight:16 },
});
