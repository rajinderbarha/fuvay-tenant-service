import React from "react";
import { createNativeStackNavigator, NativeStackScreenProps } from "@react-navigation/native-stack";
import { JobExecutionStackParamList } from "./routeTypes";
import { FeaturePlaceholderScreen } from "./placeholders/FeaturePlaceholderScreen";
import { MobileHeader } from "../design-system/components/navigation";
import { IconProps } from "../design-system/components/Icon";
import { JobDetailScreen } from "../screens/jobDetail/JobDetailScreen";
import { JobTimelineScreen } from "../screens/jobDetail/JobTimelineScreen";
import { InspectionScreen } from "../screens/inspection/InspectionScreen";
import { EstimateScreen } from "../screens/estimate/EstimateScreen";
import { WorkExecutionScreen } from "../screens/workExecution/WorkExecutionScreen";
import { CompletionProofScreen } from "../screens/completionProof/CompletionProofScreen";
import { DirectPaymentScreen } from "../screens/directPayment/DirectPaymentScreen";
import { PartsRequestScreen } from "../screens/workExecution/PartsRequestScreen";

const Stack = createNativeStackNavigator<JobExecutionStackParamList>();

const SCREEN_META: Record<Exclude<keyof JobExecutionStackParamList, "JobDetail" | "JobTimeline" | "Inspection" | "Estimate" | "Checklist" | "CompletionProof" | "DirectPaymentConfirmation" | "PartsRequest">, { title: string; icon: IconProps["name"] }> = {
  EstimateRevision:        { title: "Estimate Revision",         icon: "create-outline" },
};

/**
 * Job-execution stack (spec sections 1, 10). Back behavior: every
 * execution child screen (Inspection/Estimate/.../DirectPaymentConfirmation)
 * always returns to Job Detail for the SAME jobId -- even if it was opened
 * directly via deep link/push with no Job Detail beneath it in the native
 * stack -- rather than falling through to whatever screen happens to be
 * under it. Job Detail itself falls back to the Jobs tab when there's
 * nothing safe to pop to.
 */
type PlaceholderScreenName = Exclude<keyof JobExecutionStackParamList, "JobDetail" | "JobTimeline" | "Inspection" | "Estimate" | "Checklist" | "CompletionProof" | "DirectPaymentConfirmation" | "PartsRequest">;

function makeScreen(name: PlaceholderScreenName) {
  const meta = SCREEN_META[name];
  return function JobExecutionScreen({ route, navigation }: NativeStackScreenProps<JobExecutionStackParamList, typeof name>) {
    const { jobId } = route.params;
    const goBack = () => navigation.navigate("JobDetail", { jobId });
    return (
      <>
        <MobileHeader title={`${meta.title} · ${jobId}`} onBack={goBack} />
        <FeaturePlaceholderScreen title={meta.title} icon={meta.icon} note="Job-execution UI is built in a later phase. Navigation only." />
      </>
    );
  };
}

/**
 * JobDetail, Inspection, Estimate and Checklist (Work Execution) render the
 * real command-center screens (Phases J, K, L, M); every other child
 * screen in this stack remains a guarded-navigation placeholder until its
 * own phase builds it (spec section 23/27/25). EstimateRevision has no
 * dedicated screen -- revision mode is derived by EstimateScreen itself
 * from the backend-projected quote state. "Checklist" hosts
 * WorkExecutionScreen (start/pause/resume, work checklist, parts,
 * evidence, Finish Work) -- actionRouting.ts's `start_service` action
 * already routed here; the route name was kept to avoid a wider rename.
 */
export function JobExecutionNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="JobDetail" component={JobDetailScreen} />
      <Stack.Screen name="JobTimeline" component={JobTimelineScreen} />
      <Stack.Screen name="Inspection" component={InspectionScreen} />
      <Stack.Screen name="Estimate" component={EstimateScreen} />
      <Stack.Screen name="EstimateRevision" component={makeScreen("EstimateRevision")} />
      <Stack.Screen name="PartsRequest" component={PartsRequestScreen} />
      <Stack.Screen name="Checklist" component={WorkExecutionScreen} />
      <Stack.Screen name="CompletionProof" component={CompletionProofScreen} />
      <Stack.Screen name="DirectPaymentConfirmation" component={DirectPaymentScreen} />
    </Stack.Navigator>
  );
}
