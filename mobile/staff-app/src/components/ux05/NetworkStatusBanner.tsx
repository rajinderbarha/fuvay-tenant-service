import React, { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";
import { theme } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";
import type { OfflineSyncStateView } from "../../types/ux05";

/** UX-05 Round 5: reactive theme colors -- requires a ThemeProvider ancestor
 * (mounted in App.tsx; also used directly in NavigationContainer). */
export function NetworkStatusBanner({ state }: { state:OfflineSyncStateView }) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  if (state.networkState === "online" && state.syncState === "idle") return null;
  const label =
    state.networkState === "offline" ? "You're offline — showing cached work. Status changes, parts requests, and completion require a connection."
    : state.networkState === "slow" ? "Slow connection — some actions may take longer."
    : state.syncState === "sync_pending" ? `${state.pendingDrafts} draft${state.pendingDrafts===1?"":"s"} waiting to sync.`
    : state.syncState === "sync_failed" ? "Sync failed — will retry automatically."
    : state.syncState === "conflict_detected" ? "This job changed on the server — review before continuing."
    : null;
  if (!label) return null;
  return (
    <View style={s.banner} testID="network-status-banner" accessibilityRole="alert">
      <Text style={s.text}>{label}</Text>
    </View>
  );
}

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    banner: { backgroundColor:colors.warningBg, borderBottomWidth:1, borderBottomColor:colors.warningBorder,
              padding:10 },
    text:   { fontSize:theme.font.size.sm, color:colors.warningText, fontWeight:"600", textAlign:"center" },
  });
}
