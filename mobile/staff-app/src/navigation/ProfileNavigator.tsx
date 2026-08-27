import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ProfileStackParamList } from "./routeTypes";
import { ProfileScreen } from "../screens/profile/ProfileScreen";
import { EditPersonalProfileScreen } from "../screens/profile/EditPersonalProfileScreen";
import { EmploymentDetailsScreen } from "../screens/employment/EmploymentDetailsScreen";
import { DocumentsScreen } from "../screens/documents/DocumentsScreen";
import { DocumentDetailScreen } from "../screens/documents/DocumentDetailScreen";
import { DocumentUploadScreen } from "../screens/documents/DocumentUploadScreen";
import { DocumentHistoryScreen } from "../screens/documents/DocumentHistoryScreen";
import { AvailabilityPreferencesScreen } from "../screens/profile/AvailabilityPreferencesScreen";
import { NotificationPreferencesScreen } from "../screens/notificationPreferences/NotificationPreferencesScreen";
import { AppearanceScreen } from "../screens/profile/AppearanceScreen";
import { SecurityScreen } from "../screens/security/SecurityScreen";
import { ChangePasswordScreen } from "../screens/security/ChangePasswordScreen";
import { MFASetupScreen } from "../screens/security/MFASetupScreen";
import { MFAManagementScreen } from "../screens/security/MFAManagementScreen";
import { TrustedDeviceScreen } from "../screens/security/TrustedDeviceScreen";
import { SecurityActivityScreen } from "../screens/security/SecurityActivityScreen";
import { ActiveSessionsScreen } from "../screens/security/ActiveSessionsScreen";
import { PrivacyAndDataScreen } from "../screens/privacy/PrivacyAndDataScreen";
import { DataSummaryScreen } from "../screens/privacy/DataSummaryScreen";
import { ConsentHistoryScreen } from "../screens/privacy/ConsentHistoryScreen";
import { PrivacyRequestFormScreen } from "../screens/privacy/PrivacyRequestFormScreen";
import { PrivacyRequestListScreen } from "../screens/privacy/PrivacyRequestListScreen";
import { PrivacyRequestDetailScreen } from "../screens/privacy/PrivacyRequestDetailScreen";
import { VoluntaryDataExportScreen } from "../screens/privacy/VoluntaryDataExportScreen";
import { AccountClosureRequestScreen } from "../screens/privacy/AccountClosureRequestScreen";
import { LegalDocumentsScreen } from "../screens/legal/LegalDocumentsScreen";
import { LegalDocumentDetailScreen } from "../screens/legal/LegalDocumentDetailScreen";
import { HelpAndSupportScreen } from "../screens/support/HelpAndSupportScreen";
import { HelpSearchScreen } from "../screens/support/HelpSearchScreen";
import { HelpCategoryScreen } from "../screens/support/HelpCategoryScreen";
import { HelpArticleScreen } from "../screens/support/HelpArticleScreen";
import { SupportRequestListScreen } from "../screens/support/SupportRequestListScreen";
import { SupportRequestDetailScreen } from "../screens/support/SupportRequestDetailScreen";
import { CreateSupportRequestScreen } from "../screens/support/CreateSupportRequestScreen";
import { TechnicalDiagnosticsPreviewScreen } from "../screens/support/TechnicalDiagnosticsPreviewScreen";
import { OfflineSyncCenterScreen } from "../screens/sync/OfflineSyncCenterScreen";
import { SyncItemDetailScreen } from "../screens/sync/SyncItemDetailScreen";
import { SyncConflictReviewScreen } from "../screens/sync/SyncConflictReviewScreen";
import { OfflineStorageScreen } from "../screens/sync/OfflineStorageScreen";

const Stack = createNativeStackNavigator<ProfileStackParamList>();

/** Nested stack hosted by the Profile tab (Phase R), mirroring
 * ScheduleNavigator.tsx's pattern (Phase P). */
export function ProfileNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="ProfileHome" component={ProfileScreen} />
      <Stack.Screen name="EditPersonalProfile" component={EditPersonalProfileScreen} />
      <Stack.Screen name="EmploymentDetails" component={EmploymentDetailsScreen} />
      <Stack.Screen name="Documents" component={DocumentsScreen} />
      <Stack.Screen name="DocumentDetail" component={DocumentDetailScreen} />
      <Stack.Screen name="DocumentUpload" component={DocumentUploadScreen} />
      <Stack.Screen name="DocumentHistory" component={DocumentHistoryScreen} />
      <Stack.Screen name="AvailabilityPreferences" component={AvailabilityPreferencesScreen} />
      <Stack.Screen name="NotificationPreferences" component={NotificationPreferencesScreen} />
      <Stack.Screen name="Appearance" component={AppearanceScreen} />
      <Stack.Screen name="Security" component={SecurityScreen} />
      <Stack.Screen name="ChangePassword" component={ChangePasswordScreen} />
      <Stack.Screen name="MFASetup" component={MFASetupScreen} />
      <Stack.Screen name="MFAManagement" component={MFAManagementScreen} />
      <Stack.Screen name="TrustedDevice" component={TrustedDeviceScreen} />
      <Stack.Screen name="SecurityActivity" component={SecurityActivityScreen} />
      <Stack.Screen name="ActiveSessions" component={ActiveSessionsScreen} />
      <Stack.Screen name="PrivacyAndData" component={PrivacyAndDataScreen} />
      <Stack.Screen name="DataSummary" component={DataSummaryScreen} />
      <Stack.Screen name="ConsentHistory" component={ConsentHistoryScreen} />
      <Stack.Screen name="PrivacyRequestForm" component={PrivacyRequestFormScreen} />
      <Stack.Screen name="PrivacyRequestList" component={PrivacyRequestListScreen} />
      <Stack.Screen name="PrivacyRequestDetail" component={PrivacyRequestDetailScreen} />
      <Stack.Screen name="VoluntaryDataExport" component={VoluntaryDataExportScreen} />
      <Stack.Screen name="AccountClosureRequest" component={AccountClosureRequestScreen} />
      <Stack.Screen name="LegalDocuments" component={LegalDocumentsScreen} />
      <Stack.Screen name="LegalDocumentDetail" component={LegalDocumentDetailScreen} />
      <Stack.Screen name="HelpAndSupport" component={HelpAndSupportScreen} />
      <Stack.Screen name="HelpSearch" component={HelpSearchScreen} />
      <Stack.Screen name="HelpCategory" component={HelpCategoryScreen} />
      <Stack.Screen name="HelpArticle" component={HelpArticleScreen} />
      <Stack.Screen name="SupportRequestList" component={SupportRequestListScreen} />
      <Stack.Screen name="SupportRequestDetail" component={SupportRequestDetailScreen} />
      <Stack.Screen name="CreateSupportRequest" component={CreateSupportRequestScreen} />
      <Stack.Screen name="TechnicalDiagnosticsPreview" component={TechnicalDiagnosticsPreviewScreen} />
      <Stack.Screen name="OfflineSyncCenter" component={OfflineSyncCenterScreen} />
      <Stack.Screen name="SyncItemDetail" component={SyncItemDetailScreen} />
      <Stack.Screen name="SyncConflictReview" component={SyncConflictReviewScreen} />
      <Stack.Screen name="OfflineStorage" component={OfflineStorageScreen} />
    </Stack.Navigator>
  );
}
