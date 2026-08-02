import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ScheduleStackParamList } from "./routeTypes";
import { ScheduleScreen } from "../screens/schedule/ScheduleScreen";
import { ManageAvailabilityScreen } from "../screens/schedule/ManageAvailabilityScreen";
import { RequestTimeOffScreen } from "../screens/schedule/RequestTimeOffScreen";

const Stack = createNativeStackNavigator<ScheduleStackParamList>();

/** Nested stack hosted by the Schedule tab (Phase P). Opening a job
 * navigates OUT of this stack to the existing canonical JobExecutionStack
 * via a two-level getParent() call from ScheduleScreen -- never a second
 * job-detail implementation. */
export function ScheduleNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="ScheduleHome" component={ScheduleScreen} />
      <Stack.Screen name="ManageAvailability" component={ManageAvailabilityScreen} />
      <Stack.Screen name="RequestTimeOff" component={RequestTimeOffScreen} />
    </Stack.Navigator>
  );
}
