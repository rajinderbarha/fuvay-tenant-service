import React from "react";
import { useRoute, RouteProp } from "@react-navigation/native";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { SupportRequestForm } from "./CreateSupportRequestScreen";
import { SAFETY_CONCERN_TYPE } from "../../domain/supportRequests";

type Route = RouteProp<CustomerAppStackParamList, "SafetyReport">;

/**
 * There is no distinct safety-reporting engine in the audited backend --
 * `safety_concern` is a real value in the complaint engine's extended
 * type set (`COMPLAINT_TYPES_EXT`), so this is the same real complaint
 * creation flow, preset and locked to that category rather than a
 * renamed or fabricated capability (spec section 9). Never claims to be
 * an emergency service, instant response, or 24/7 team.
 */
export function SafetyReportScreen() {
  const route = useRoute<Route>();
  return <SupportRequestForm bookingId={route.params.bookingId} presetComplaintType={SAFETY_CONCERN_TYPE} />;
}
