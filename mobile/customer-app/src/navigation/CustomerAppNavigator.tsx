import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { CustomerAppStackParamList } from "./routeTypes";
import { CustomerTabs } from "./CustomerTabs";
import { BookingReviewScreen } from "../screens/booking-review/BookingReviewScreen";
import { BookingConfirmationScreen } from "../screens/booking-confirmation/BookingConfirmationScreen";
import { BookingDetailsScreen } from "../screens/booking-details/BookingDetailsScreen";
import { NotificationCenterScreen } from "../screens/notifications/NotificationCenterScreen";
import { EditProfileScreen } from "../screens/profile/EditProfileScreen";
import { SecurityScreen } from "../screens/profile/SecurityScreen";
import { SavedAddressesScreen } from "../screens/profile/SavedAddressesScreen";
import { AddressFormScreen } from "../screens/address-form/AddressFormScreen";
import { MfaManageScreen } from "../screens/security/MfaManageScreen";
import { ManageSessionsScreen } from "../screens/security/ManageSessionsScreen";
import { LoginActivityScreen } from "../screens/security/LoginActivityScreen";
import { PrivacyDataScreen } from "../screens/profile/PrivacyDataScreen";
import { LegalDocumentScreen } from "../screens/legal/LegalDocumentScreen";
import { PrivacyRequestsScreen } from "../screens/profile/PrivacyRequestsScreen";
import { PrivacyRequestSubmittedScreen } from "../screens/profile/PrivacyRequestSubmittedScreen";
import { PrivacyConsentScreen } from "../screens/profile/PrivacyConsentScreen";
import { AssistantDataInfoScreen } from "../screens/profile/AssistantDataInfoScreen";
import { AccountDeletionRequestScreen } from "../screens/profile/AccountDeletionRequestScreen";
import { DeleteAccountFinalConfirmationScreen } from "../screens/profile/DeleteAccountFinalConfirmationScreen";
import { PrivacyRequestDetailsScreen } from "../screens/profile/PrivacyRequestDetailsScreen";
import { DataExportRequestScreen } from "../screens/profile/DataExportRequestScreen";
import { DataCorrectionRequestScreen } from "../screens/profile/DataCorrectionRequestScreen";
import { BookingSupportEntryScreen } from "../screens/support/BookingSupportEntryScreen";
import { SupportRequestsScreen } from "../screens/support/SupportRequestsScreen";
import { SupportRequestDetailsScreen } from "../screens/support/SupportRequestDetailsScreen";
import { SafetyReportScreen } from "../screens/support/SafetyReportScreen";
import { SupportRequestWizardNavigator } from "./SupportRequestWizardNavigator";
import { ServiceRemediesScreen } from "../screens/service-remedies/ServiceRemediesScreen";

const Stack = createNativeStackNavigator<CustomerAppStackParamList>();

/** Owns authenticated customer tabs and authenticated modal/detail routes
 * reached via validated deep links (spec section 6/16) -- Service Match/
 * Review/Confirmation (spec: no bottom navigation inside this focused
 * flow, hence a stack screen rather than a tab). */
export function CustomerAppNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="CustomerTabs" component={CustomerTabs} />
      <Stack.Screen name="BookingReview" component={BookingReviewScreen} />
      <Stack.Screen name="BookingConfirmation" component={BookingConfirmationScreen} />
      <Stack.Screen name="BookingDetails" component={BookingDetailsScreen} />
      <Stack.Screen name="ServiceRemedies" component={ServiceRemediesScreen} />
      <Stack.Screen name="Notifications" component={NotificationCenterScreen} />
      <Stack.Screen name="EditProfile" component={EditProfileScreen} />
      <Stack.Screen name="Security" component={SecurityScreen} />
      <Stack.Screen name="SavedAddresses" component={SavedAddressesScreen} />
      <Stack.Screen name="AddAddress" component={AddressFormScreen} />
      <Stack.Screen name="EditAddress" component={AddressFormScreen} />
      <Stack.Screen name="MfaManage" component={MfaManageScreen} />
      <Stack.Screen name="ManageSessions" component={ManageSessionsScreen} />
      <Stack.Screen name="LoginActivity" component={LoginActivityScreen} />
      <Stack.Screen name="PrivacyData" component={PrivacyDataScreen} />
      <Stack.Screen name="PrivacyRequests" component={PrivacyRequestsScreen} />
      <Stack.Screen name="PrivacyRequestSubmitted" component={PrivacyRequestSubmittedScreen} />
      <Stack.Screen name="PrivacyConsent" component={PrivacyConsentScreen} />
      <Stack.Screen name="LegalDocument" component={LegalDocumentScreen} />
      <Stack.Screen name="AssistantDataInfo" component={AssistantDataInfoScreen} />
      <Stack.Screen name="AccountDeletionRequest" component={AccountDeletionRequestScreen} />
      <Stack.Screen name="DeleteAccountFinalConfirmation" component={DeleteAccountFinalConfirmationScreen} />
      <Stack.Screen name="PrivacyRequestDetails" component={PrivacyRequestDetailsScreen} />
      <Stack.Screen name="DataExportRequest" component={DataExportRequestScreen} />
      <Stack.Screen name="DataCorrectionRequest" component={DataCorrectionRequestScreen} />
      <Stack.Screen name="BookingSupportEntry" component={BookingSupportEntryScreen} />
      <Stack.Screen name="SupportRequests" component={SupportRequestsScreen} />
      <Stack.Screen name="SupportRequestDetails" component={SupportRequestDetailsScreen} />
      <Stack.Screen name="CreateSupportRequest" component={SupportRequestWizardNavigator} />
      <Stack.Screen name="SafetyReport" component={SafetyReportScreen} />
    </Stack.Navigator>
  );
}
