import { JobExecutionParams, AuthRouteName, RestrictedRouteName, ReasonCode } from "./guards/types";

/**
 * Typed navigation parameter lists (spec section 2). Job-related routes
 * carry only stable IDs/keys -- never a whole job/customer/estimate/
 * workflow object. React Navigation's typed generics below are what give
 * every `navigation.navigate(...)` call in the app compile-time safety.
 */

export interface ResetIdentifier { email?: string; phone?: string }

export type AuthStackParamList = {
  Login: { pendingDeepLink?: string; reasonCode?: ReasonCode } | undefined;
  OtpVerify: { phone: string };
  Mfa: { mfaChallengeToken: string; rememberDevice: boolean };
  ForgotPassword: undefined;
  /** One combined screen for code + new password -- the real backend
   * (`POST /v1/auth/password/reset/confirm`) verifies the code and sets
   * the new password in a single atomic call; there is no separate
   * "verify code" endpoint to build a distinct step around. */
  ResetPassword: { identifier: ResetIdentifier };
  ResetSuccess: undefined;
};

export type AppTabsParamList = {
  Home: undefined;
  Jobs: undefined;
  Schedule: undefined;
  Notifications: { notificationId?: string } | undefined;
  Profile: undefined;
};

export type ScheduleStackParamList = {
  ScheduleHome: undefined;
  ManageAvailability: undefined;
  RequestTimeOff: undefined;
};

export type ProfileStackParamList = {
  ProfileHome: undefined;
  EditPersonalProfile: undefined;
  EmploymentDetails: undefined;
  Documents: undefined;
  DocumentDetail: { docCode: string };
  DocumentUpload: { docCode?: string };
  DocumentHistory: { docCode: string };
  AvailabilityPreferences: undefined;
  NotificationPreferences: undefined;
  Appearance: undefined;
  Security: undefined;
  ChangePassword: undefined;
  MFASetup: undefined;
  MFAManagement: undefined;
  TrustedDevice: undefined;
  SecurityActivity: undefined;
  ActiveSessions: undefined;
  PrivacyAndData: undefined;
  DataSummary: undefined;
  ConsentHistory: undefined;
  PrivacyRequestForm: { requestType?: import("../services/privacy/types").PrivacyRequestType; isAccountClosure?: boolean } | undefined;
  PrivacyRequestList: undefined;
  PrivacyRequestDetail: { requestId: string };
  VoluntaryDataExport: undefined;
  AccountClosureRequest: undefined;
  /** Terms / Privacy and any other published policy, read from
   *  /v1/public/legal. `title` is only a placeholder shown while the real
   *  title loads. */
  LegalDocuments: undefined;
  LegalDocumentDetail: { docType: string; title?: string };
  HelpAndSupport: undefined;
  HelpSearch: undefined;
  HelpCategory: { areaKey: string; areaLabel: string };
  HelpArticle: { slug: string };
  SupportRequestList: undefined;
  SupportRequestDetail: { requestId: string };
  CreateSupportRequest: { intent?: "manager" | "platform" | "technical" } | undefined;
  TechnicalDiagnosticsPreview: { subject: string; description: string; category: string; impact: string } | undefined;
  OfflineSyncCenter: undefined;
  SyncItemDetail: { localId: string };
  SyncConflictReview: { localId: string };
  OfflineStorage: undefined;
};

export type JobExecutionStackParamList = {
  JobDetail: JobExecutionParams;
  JobTimeline: JobExecutionParams;
  Inspection: JobExecutionParams;
  Estimate: JobExecutionParams;
  EstimateRevision: JobExecutionParams;
  PartsRequest: JobExecutionParams;
  Checklist: JobExecutionParams;
  CompletionProof: JobExecutionParams;
  DirectPaymentConfirmation: JobExecutionParams;
};

export type RestrictedStateStackParamList = {
  AccountPending: { reasonCode: ReasonCode };
  AccountSuspended: { reasonCode: ReasonCode };
  TenantSuspended: { reasonCode: ReasonCode };
  TechnicianInactive: { reasonCode: ReasonCode };
  AccessDenied: { reasonCode: ReasonCode };
  AppUpdateRequired: { reasonCode: ReasonCode };
  ServiceUnavailable: { reasonCode: ReasonCode };
};

export type RootStackParamList = {
  Bootstrap: undefined;
  AuthStack: { screen: AuthRouteName; params?: AuthStackParamList[AuthRouteName] } | undefined;
  AppTabs: undefined;
  JobExecutionStack: { screen: keyof JobExecutionStackParamList; params: JobExecutionParams };
  RestrictedStateStack: { screen: RestrictedRouteName; params: RestrictedStateStackParamList[RestrictedRouteName] };
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
