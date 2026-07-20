import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { NetworkStatusBanner } from "../../components/ux05/NetworkStatusBanner";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";
import type { OfflineSyncStateView } from "../../types/ux05";

const SCENARIOS: Array<{ title:string; state:OfflineSyncStateView }> = [
  { title:"Cached work (online, fresh)", state:{ meta:{readiness:"mock_design_only"}, networkState:"online", cacheState:"fresh", pendingDrafts:0, syncState:"idle" } },
  { title:"Offline -- viewing cached work", state:{ meta:{readiness:"mock_design_only"}, networkState:"offline", cacheState:"stale_cached", pendingDrafts:0, syncState:"idle" } },
  { title:"Slow connection", state:{ meta:{readiness:"mock_design_only"}, networkState:"slow", cacheState:"fresh", pendingDrafts:0, syncState:"idle" } },
  { title:"Sync pending (drafts queued)", state:{ meta:{readiness:"mock_design_only"}, networkState:"online", cacheState:"fresh", pendingDrafts:2, syncState:"sync_pending" } },
  { title:"Sync failed", state:{ meta:{readiness:"mock_design_only"}, networkState:"online", cacheState:"fresh", pendingDrafts:1, syncState:"sync_failed" } },
  { title:"Sync conflict detected", state:{ meta:{readiness:"mock_design_only"}, networkState:"online", cacheState:"fresh", pendingDrafts:0, syncState:"conflict_detected" } },
];

/**
 * Dev-only showcase covering workstream 23/28's offline + system-state
 * examples (cached-work / sync-pending / sync-conflict / read-only /
 * restricted / session-expired-adjacent) in one screen, using the real
 * NetworkStatusBanner + PermissionRestrictedState components rather than
 * one-off mockups, so the actual banner copy/behavior is what's reviewed.
 */
export function OfflineStatesShowcaseScreen() {
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="offline-states-showcase">
      {SCENARIOS.map(sc => (
        <View key={sc.title} style={[gs.card, { padding:0, overflow:"hidden" }]}>
          <Text style={s.title}>{sc.title}</Text>
          <NetworkStatusBanner state={sc.state} />
          {sc.state.networkState === "online" && sc.state.syncState === "idle" && (
            <Text style={s.noBanner}>(no banner shown -- online + idle is the default, non-intrusive state)</Text>
          )}
        </View>
      ))}
      <View style={[gs.card, { padding:0 }]}>
        <Text style={s.title}>Restricted (permission-gated screen)</Text>
        <PermissionRestrictedState reason="Example: parts_request:approve not granted." />
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:  { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  title:    { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textPrimary, padding:theme.spacing.base, paddingBottom:6 },
  noBanner: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, padding:theme.spacing.base, paddingTop:0 },
});
