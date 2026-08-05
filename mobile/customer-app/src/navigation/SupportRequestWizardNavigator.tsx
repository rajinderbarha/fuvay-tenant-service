import React from "react";
import { createNativeStackNavigator, NativeStackScreenProps } from "@react-navigation/native-stack";
import { SupportRequestWizardParamList } from "./supportRequestWizardTypes";
import { CustomerAppStackParamList } from "./routeTypes";
import { SupportRequestWizardProvider } from "../screens/support/SupportRequestWizardContext";
import { CreateSupportRequestTopicScreen } from "../screens/support/CreateSupportRequestTopicScreen";
import { CreateSupportRequestDetailsScreen } from "../screens/support/CreateSupportRequestDetailsScreen";
import { CreateSupportRequestReviewScreen } from "../screens/support/CreateSupportRequestReviewScreen";

const Stack = createNativeStackNavigator<SupportRequestWizardParamList>();

type Props = NativeStackScreenProps<CustomerAppStackParamList, "CreateSupportRequest">;

/** Owns the wizard-scoped draft (`SupportRequestWizardProvider`) and the
 * 3 inner steps. Registered as the single `CreateSupportRequest` screen
 * in `CustomerAppNavigator` -- the outer route's params are forwarded
 * only to the wizard's own entry screen. */
export function SupportRequestWizardNavigator({ route }: Props) {
  return (
    <SupportRequestWizardProvider>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Topic" component={CreateSupportRequestTopicScreen} initialParams={route.params} />
        <Stack.Screen name="Details" component={CreateSupportRequestDetailsScreen} />
        <Stack.Screen name="Review" component={CreateSupportRequestReviewScreen} />
      </Stack.Navigator>
    </SupportRequestWizardProvider>
  );
}
