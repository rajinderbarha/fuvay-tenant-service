import React, { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { jobsApi, type Job } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

type Props = { navigation: NativeStackNavigationProp<never> };

const SERVICE_FILTERS = ["All","AC Service","Plumbing","Electrical","Cleaning","Carpentry","Pest Control"];

export function ServiceHistoryScreen({ navigation }: Props) {
  const [filter, setFilter] = useState("All");
  const jobs = useApi(useCallback(() => jobsApi.myJobs({ status:"completed", limit:"50" }), []));

  const filtered = (jobs.data?.jobs ?? []).filter(j =>
    filter === "All" || j.service_type.toLowerCase().includes(filter.toLowerCase())
  );

  const totalSpend = (jobs.data?.jobs ?? []).reduce((s,j) => s + (j.job_value??0), 0);
  const fmtMoney = (n:number) => `₹${n.toLocaleString("en-IN")}`;
  const fmtDate  = (d:string) => new Date(d).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"});

  function renderJob({ item:j, index:i }: { item:Job; index:number }) {
    return (
      <TouchableOpacity style={s.jobRow} activeOpacity={0.85}
        onPress={()=>navigation.navigate("BookingDetail" as never,{bookingId:j.id} as never)}>
        <View style={s.dateCol}>
          <Text style={s.dateDay}>{new Date(j.created_at).getDate()}</Text>
          <Text style={s.dateMon}>{new Date(j.created_at).toLocaleString("en-IN",{month:"short"})}</Text>
        </View>
        <View style={{flex:1}}>
          <Text style={s.serviceType}>{j.service_type}</Text>
          <Text style={s.meta}>{j.city}{j.assigned_staff?` · ${j.assigned_staff}`:""}</Text>
        </View>
        <View style={{alignItems:"flex-end",gap:5}}>
          <JobStatusBadge status={j.status} size="sm"/>
          {j.job_value != null && (
            <Text style={s.value}>{fmtMoney(j.job_value)}</Text>
          )}
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <View style={gs.screen}>
      {/* Summary banner */}
      <View style={s.banner}>
        <View style={s.bannerStat}>
          <Text style={s.bannerVal}>{jobs.data?.total ?? "—"}</Text>
          <Text style={s.bannerLabel}>Services</Text>
        </View>
        <View style={s.bannerDivider}/>
        <View style={s.bannerStat}>
          <Text style={s.bannerVal}>{fmtMoney(totalSpend)}</Text>
          <Text style={s.bannerLabel}>Total Spent</Text>
        </View>
        <View style={s.bannerDivider}/>
        <View style={s.bannerStat}>
          <Text style={s.bannerVal}>{new Set((jobs.data?.jobs??[]).map(j=>j.service_type)).size}</Text>
          <Text style={s.bannerLabel}>Service Types</Text>
        </View>
      </View>

      {/* Service type filter */}
      <FlatList
        horizontal data={SERVICE_FILTERS} keyExtractor={x=>x}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={s.filterList}
        renderItem={({item:f})=>(
          <TouchableOpacity onPress={()=>setFilter(f)}
            style={[s.filterChip, filter===f&&s.filterChipActive]}>
            <Text style={[s.filterText, filter===f&&s.filterTextActive]}>{f}</Text>
          </TouchableOpacity>
        )}
      />

      {/* Jobs list */}
      {jobs.loading ? (
        <View style={{padding:16,gap:10}}>{[...Array(5)].map((_,i)=><Skeleton key={i} height={66}/>)}</View>
      ) : filtered.length === 0 ? (
        <View style={{flex:1,alignItems:"center",justifyContent:"center",gap:12}}>
          <Text style={{fontSize:44}}>🔧</Text>
          <Text style={{color:theme.colors.textTertiary,fontSize:theme.font.size.base}}>
            No {filter!=="All"?filter:"completed"} services yet
          </Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={j=>j.id}
          renderItem={renderJob}
          onRefresh={jobs.refetch}
          refreshing={jobs.loading}
          ItemSeparatorComponent={()=><View style={gs.sep}/>}
          contentContainerStyle={{backgroundColor:theme.colors.surface}}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  banner:       { flexDirection:"row", backgroundColor:theme.colors.brand, padding:16, gap:0 },
  bannerStat:   { flex:1, alignItems:"center", gap:4 },
  bannerVal:    { fontSize:theme.font.size.xxl, fontWeight:"800", color:"#fff" },
  bannerLabel:  { fontSize:theme.font.size.xs, color:"rgba(255,255,255,0.65)", fontWeight:"600", textTransform:"uppercase", letterSpacing:0.5 },
  bannerDivider:{ width:1, backgroundColor:"rgba(255,255,255,0.2)", marginVertical:6 },
  filterList:   { paddingHorizontal:14, paddingVertical:10, gap:8, backgroundColor:theme.colors.surface,
                  borderBottomWidth:1, borderBottomColor:theme.colors.border },
  filterChip:   { paddingHorizontal:14, paddingVertical:6, borderRadius:99, borderWidth:1, borderColor:theme.colors.border, backgroundColor:theme.colors.surfaceSunken },
  filterChipActive:{ borderColor:theme.colors.brand, backgroundColor:theme.colors.brand },
  filterText:   { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
  filterTextActive:{ color:"#fff" },
  jobRow:       { flexDirection:"row", alignItems:"center", gap:14, padding:14, backgroundColor:theme.colors.surface },
  dateCol:      { width:36, alignItems:"center", backgroundColor:theme.colors.surfaceSunken,
                  borderRadius:theme.radius.sm, padding:5 },
  dateDay:      { fontSize:theme.font.size.xl, fontWeight:"800", color:theme.colors.brand, lineHeight:22 },
  dateMon:      { fontSize:9, fontWeight:"700", color:theme.colors.textTertiary, textTransform:"uppercase" },
  serviceType:  { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  meta:         { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  value:        { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.successText },
});
