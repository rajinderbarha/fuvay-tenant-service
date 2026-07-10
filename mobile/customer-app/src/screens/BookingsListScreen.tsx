import React, { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { bookingsApi, type Booking } from "../lib/api";
import { BookingCard } from "../components/BookingCard";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

const TABS = [
  { key:"",                   label:"All"       },
  { key:"pending_confirmation",label:"Pending"  },
  { key:"confirmed",           label:"Confirmed"},
  { key:"cancelled",           label:"Cancelled"},
] as const;

type Props = { navigation: NativeStackNavigationProp<never> };

export function BookingsListScreen({ navigation }: Props) {
  const [tab, setTab] = useState("");
  const bookings = useApi(useCallback(
    () => bookingsApi.list({ limit:"30", ...(tab?{status:tab}:{}) }), [tab]
  ));

  return (
    <View style={gs.screen}>
      {/* Tabs */}
      <View style={s.tabs}>
        {TABS.map(t => (
          <View key={t.key} style={[s.tab, tab===t.key&&s.tabActive]}>
            <Text onPress={()=>setTab(t.key)}
              style={[s.tabText, tab===t.key&&s.tabTextActive]}>{t.label}</Text>
          </View>
        ))}
      </View>

      {bookings.loading ? (
        <View style={{ padding:theme.spacing.base, gap:12 }}>
          {[...Array(4)].map((_,i)=><Skeleton key={i} height={110}/>)}
        </View>
      ) : (
        <FlatList
          data={bookings.data?.bookings ?? []}
          keyExtractor={b=>b.id}
          renderItem={({item:b})=>(
            <BookingCard booking={b}
              onPress={()=>navigation.navigate("BookingDetail" as never,{bookingId:b.id} as never)}/>
          )}
          contentContainerStyle={{ padding:theme.spacing.base, gap:12, paddingBottom:32 }}
          onRefresh={bookings.refetch} refreshing={bookings.loading}
          ListEmptyComponent={
            <View style={{ alignItems:"center", paddingTop:80, gap:10 }}>
              <Text style={{ fontSize:44 }}>📋</Text>
              <Text style={{ color:theme.colors.textTertiary, fontSize:theme.font.size.base }}>
                No bookings {tab?`with status "${tab}"`:"yet"}
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  tabs:        { flexDirection:"row", backgroundColor:theme.colors.surface, borderBottomWidth:1, borderBottomColor:theme.colors.border },
  tab:         { flex:1, alignItems:"center", paddingVertical:13, borderBottomWidth:2, borderBottomColor:"transparent" },
  tabActive:   { borderBottomColor:theme.colors.brand },
  tabText:     { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
  tabTextActive:{ color:theme.colors.brand },
});
