import React, { useCallback } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { notificationsApi, type AppNotification } from "../lib/api";
import { Skeleton } from "../components/Skeleton";
import { Button } from "../components/Button";
import { theme, gs } from "../styles/theme";

const TYPE_ICON: Record<string,string> = {
  booking:     "📋", job_update:"🔧", payment:"💳",
  promotion:"🎉", review:"⭐", system:"⚙️",
};

const TYPE_COLOR: Record<string,string> = {
  booking:"var(--info)", job_update:theme.colors.accent,
  payment:theme.colors.success, promotion:theme.colors.warning,
  system:theme.colors.textTertiary,
};

export function NotificationsScreen() {
  const notifs     = useApi(useCallback(() => notificationsApi.list(50), []));
  const markRead   = useAction(useCallback((id:string) => notificationsApi.markRead(id), []));
  const markAll    = useAction(useCallback(() => notificationsApi.markAllRead(), []));

  async function handleMarkRead(n: AppNotification) {
    if (n.is_read) return;
    await markRead.execute(n.id);
    notifs.refetch();
  }

  async function handleMarkAll() {
    await markAll.execute();
    notifs.refetch();
  }

  const data    = notifs.data?.notifications ?? [];
  const unread  = notifs.data?.unread_count ?? 0;
  const fmtTime = (d:string) => {
    const ms = Date.now() - new Date(d).getTime();
    if (ms < 60000)   return "Just now";
    if (ms < 3600000) return `${Math.floor(ms/60000)}m ago`;
    if (ms < 86400000)return `${Math.floor(ms/3600000)}h ago`;
    return new Date(d).toLocaleDateString("en-IN",{day:"numeric",month:"short"});
  };

  function renderItem({ item:n }: { item:AppNotification }) {
    return (
      <TouchableOpacity style={[s.row, !n.is_read && s.rowUnread]}
        onPress={() => handleMarkRead(n)} activeOpacity={0.85}>
        <View style={[s.iconWrap, { backgroundColor:n.is_read?theme.colors.surfaceSunken:theme.colors.accentLight }]}>
          <Text style={{ fontSize:20 }}>{TYPE_ICON[n.type] ?? "🔔"}</Text>
        </View>
        <View style={{ flex:1 }}>
          <Text style={[s.title, !n.is_read&&{fontWeight:"700"}]}>{n.title}</Text>
          <Text style={s.body} numberOfLines={2}>{n.body}</Text>
          <Text style={s.time}>{fmtTime(n.created_at)}</Text>
        </View>
        {!n.is_read && <View style={s.dot}/>}
      </TouchableOpacity>
    );
  }

  return (
    <View style={gs.screen}>
      {/* Header row */}
      {unread > 0 && (
        <View style={[gs.row,{justifyContent:"space-between",padding:12,
          backgroundColor:theme.colors.surface, borderBottomWidth:1,
          borderBottomColor:theme.colors.border}]}>
          <Text style={{fontSize:theme.font.size.sm,color:theme.colors.textSecondary}}>
            {unread} unread notification{unread!==1?"s":""}
          </Text>
          <TouchableOpacity onPress={handleMarkAll} disabled={markAll.loading}>
            <Text style={{fontSize:theme.font.size.sm,color:theme.colors.accent,fontWeight:"600"}}>
              {markAll.loading?"Marking…":"Mark all read"}
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {notifs.loading ? (
        <View style={{padding:16,gap:12}}>{[...Array(6)].map((_,i)=><Skeleton key={i} height={72}/>)}</View>
      ) : data.length === 0 ? (
        <View style={{flex:1,alignItems:"center",justifyContent:"center",gap:14}}>
          <Text style={{fontSize:44}}>🔔</Text>
          <Text style={{fontSize:theme.font.size.lg,fontWeight:"700",color:theme.colors.textPrimary}}>All caught up!</Text>
          <Text style={{fontSize:theme.font.size.base,color:theme.colors.textSecondary,textAlign:"center",paddingHorizontal:32}}>
            Booking confirmations, job updates, and offers will appear here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={data}
          keyExtractor={n=>n.id}
          renderItem={renderItem}
          onRefresh={notifs.refetch}
          refreshing={notifs.loading}
          ItemSeparatorComponent={()=><View style={gs.sep}/>}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  row:      { flexDirection:"row", alignItems:"flex-start", gap:12, padding:14, backgroundColor:theme.colors.surface },
  rowUnread:{ backgroundColor:theme.colors.accentLight+"30" },
  iconWrap: { width:44, height:44, borderRadius:22, alignItems:"center", justifyContent:"center", flexShrink:0 },
  title:    { fontSize:theme.font.size.base, fontWeight:"500", color:theme.colors.textPrimary, marginBottom:3 },
  body:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, lineHeight:18 },
  time:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:4 },
  dot:      { width:8, height:8, borderRadius:4, backgroundColor:theme.colors.accent, marginTop:6, flexShrink:0 },
});
