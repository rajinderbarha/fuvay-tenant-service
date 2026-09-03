import React from "react";
import { useRoute, RouteProp } from "@react-navigation/native";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { SupportRequestForm } from "./CreateSupportRequestScreen";
import { SAFETY_CONCERN_TYPE } from "../../domain/supportRequests";

type Route = RouteProp<CustomerAppStackParamList, "SafetyReport">;

/**
 * Safety reports use the complaint case record so the customer and provider
 * keep one evidence trail. The backend marks this type critical and gives the
 * provider a one-hour first-response SLA. It is not an emergency service.
 */
export function SafetyReportScreen() {
  const route = useRoute<Route>();
  return <SupportRequestForm bookingId={route.params.bookingId} presetComplaintType={SAFETY_CONCERN_TYPE} />;
}
