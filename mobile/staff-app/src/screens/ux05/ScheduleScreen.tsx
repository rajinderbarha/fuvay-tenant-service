import React, { useCallback, useMemo } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { useApi } from "../../hooks/useApi";
import { jobsApi } from "../../lib/api";
import { theme, gs } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";
import { Skeleton } from "../../components/Skeleton";
import { ScheduleCard } from "../../components/ux05/ScheduleCard";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { ScheduleItemView } from "../../types/ux05";

type Props = { navigation: NativeStackNavigationProp<never> };

/**
 * Today/Upcoming schedule (workstream 7). Uses the real myJobs list (the
 * only jobs endpoint that exists); groups client-side by scheduled_date
 * since the backend has no per-day schedule endpoint. Day/Agenda-view
 * toggles from the brief were not built this pass -- Today + Upcoming only
 * (see known-limitations.md).
 *
 * UX-05 Round 7: converted to reactive theme colors.
 */
export function ScheduleScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const jobs = useApi(useCallback(() => jobsApi.myJobs(), []));

  const { today, upcoming } = useMemo(() => {
    const all = jobs.data?.jobs ?? [];
    const now = new Date();
    const isToday = (d:string|null) => !!d && new Date(d).toDateString() === now.toDateString();
    const items = (list: typeof all): ScheduleItemView[] => list.map(job => ({
      meta: { readiness: "production_ready" },
      provenance: { pipeline:"service_booking_service_job", sourceBookingId:job.booking_id, jobId:job.id, jobModel:"ServiceJob" },
      job, timeWindow: job.scheduled_time_window, status: job.status, hasConflict: false,
    }));
    return {
      today: items(all.filter(j => isToday(j.scheduled_date))),
      upcoming: items(all.filter(j => j.scheduled_date && !isToday(j.scheduled_date))),
    };
  }, [jobs.data]);

  if (jobs.loading) return (
    <View style={{ padding:theme.spacing.base, gap:12, backgroundColor:colors.bg, flex:1 }}>
      {[...Array(4)].map((_,i) => <Skeleton key={i} height={80} />)}
    </View>
  );

  const sections = [
    { title: "Today", data: today },
    { title: "Upcoming", data: upcoming },
  ];

  return (
    <FlatList
      style={[gs.screen, { backgroundColor:colors.bg }]}
      contentContainerStyle={{ padding:theme.spacing.base, gap:10, paddingBottom:32 }}
      data={sections.flatMap(sec => [{ header:sec.title, item:null }, ...sec.data.map(item => ({ header:null, item }))])}
      keyExtractor={(row, i) => row.header ?? row.item?.job.id ?? String(i)}
      renderItem={({ item: row }) => row.header
        ? <Text style={[gs.label, { marginTop:8, color:colors.textTertiary }]}>{row.header}</Text>
        : <ScheduleCard item={row.item!} onPress={() => navigation.navigate("JobDetail" as never, { jobId:row.item!.job.id } as never)} />
      }
      ListEmptyComponent={<Text style={{ color:colors.textTertiary, textAlign:"center", marginTop:40 }}>No scheduled jobs</Text>}
    />
  );
}
