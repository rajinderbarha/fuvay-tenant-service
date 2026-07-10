import React, { useCallback } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { chatApi, type ChatRoom } from "../lib/api";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

type Props = { navigation: NativeStackNavigationProp<never> };

export function ChatListScreen({ navigation }: Props) {
  const rooms = useApi(useCallback(() => chatApi.listRooms(), []));

  function renderRoom({ item:r }: { item:ChatRoom }) {
    const time = r.last_message_at
      ? new Date(r.last_message_at).toLocaleTimeString("en-IN",{ hour:"2-digit", minute:"2-digit" })
      : "";
    return (
      <TouchableOpacity style={s.row} activeOpacity={0.85}
        onPress={() => navigation.navigate("ChatRoom" as never, { roomId:r.room_id, name:r.participant_name } as never)}>
        <View style={s.avatar}>
          <Text style={s.avatarText}>{r.participant_name[0].toUpperCase()}</Text>
        </View>
        <View style={{ flex:1 }}>
          <View style={[gs.row, { justifyContent:"space-between" }]}>
            <Text style={s.name}>{r.participant_name}</Text>
            <Text style={s.time}>{time}</Text>
          </View>
          {r.job_number && <Text style={s.jobRef}>Job: {r.job_number}</Text>}
          {r.last_message && (
            <Text style={s.preview} numberOfLines={1}>{r.last_message}</Text>
          )}
        </View>
        {r.unread_count > 0 && (
          <View style={s.badge}>
            <Text style={s.badgeText}>{r.unread_count > 9 ? "9+" : r.unread_count}</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  }

  return (
    <View style={gs.screen}>
      {rooms.loading ? (
        <View style={{ padding:theme.spacing.base, gap:14 }}>
          {[...Array(5)].map((_,i) => <Skeleton key={i} height={70} />)}
        </View>
      ) : (
        <FlatList
          data={rooms.data?.rooms ?? []}
          renderItem={renderRoom}
          keyExtractor={r => r.room_id}
          onRefresh={rooms.refetch}
          refreshing={rooms.loading}
          ItemSeparatorComponent={() => <View style={gs.sep} />}
          ListEmptyComponent={
            <View style={{ alignItems:"center", paddingTop:80, gap:10 }}>
              <Text style={{ fontSize:48 }}>💬</Text>
              <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textTertiary }}>
                No conversations yet
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  row:        { flexDirection:"row", alignItems:"center", gap:12, padding:14, backgroundColor:theme.colors.surface },
  avatar:     { width:46, height:46, borderRadius:23, backgroundColor:theme.colors.accentLight,
                alignItems:"center", justifyContent:"center" },
  avatarText: { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.accent },
  name:       { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  time:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  jobRef:     { fontSize:theme.font.size.xs, color:theme.colors.accent, fontWeight:"600", marginTop:1 },
  preview:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  badge:      { width:22, height:22, borderRadius:11, backgroundColor:theme.colors.danger,
                alignItems:"center", justifyContent:"center" },
  badgeText:  { fontSize:9, fontWeight:"800", color:"#fff" },
});
