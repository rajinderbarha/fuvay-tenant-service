import { ExceptionalRouteName, PublicRouteName } from "./guards/types";
import { AssistantEntryContext } from "../domain/assistantEntry";

/**
 * Typed navigation parameter lists (spec section 5). No unrestricted
 * string route names, no `any` params -- every screen this phase can
 * reach carries only stable identifiers/reason codes, never a whole
 * domain object.
 */
/**
 * CONFLICT HISTORY NOTE: an earlier Home-redesign task temporarily
 * changed this to Home/Bookings/Chat/Offers/Profile with no elevated
 * action. THIS task explicitly restores the Phase E tab set --
 * Home/Bookings/Assistant (central elevated)/Support/Profile -- and
 * explicitly forbids Chat/Offers/Wallet/Payments/Providers tabs. This is
 * the current, authoritative tab set; the prior change is superseded.
 */
export type CustomerTabName = "Home" | "Bookings" | "Assistant" | "Support" | "Profile";

export type CustomerTabsParamList = {
  Home: undefined;
  Bookings: undefined;
  /** Optional backend context carried from a Home service tap or the
   * "Not sure what to book?" entry card -- see domain/assistantEntry.ts.
   * `undefined` means the customer opened the tab directly (no category
   * pre-selected). The Booking Assistant conversation itself is a later
   * phase; this tab remains a placeholder that only displays/forwards
   * this context today. */
  Assistant: AssistantEntryContext | undefined;
  Support: undefined;
  Profile: undefined;
};

/**
 * Phase G: replaces the Phase E AuthEntryPlaceholder with the real typed
 * customer-auth route set (spec section 6). No password/OTP/token value
 * is ever carried as a route param -- `phone` here is the (non-secret)
 * masked-destination display value only, and the MFA challenge token
 * lives in sessionManager's module state, never in navigation params.
 */
export type PublicStackParamList = {
  LoginMethod: undefined;
  Signup: undefined;
  // `devOtpHint` is populated only from the backend's own dev/staging-only
  // `otp_hint` field (never sent in production -- see AuthService.
  // send_phone_otp) and only when EXPO_PUBLIC_ENV is non-production. It
  // exists purely to pre-fill/auto-submit the code during local testing.
  VerifyLoginOtp: { phone: string; devOtpHint?: string };
  PasswordLogin: undefined;
  MfaChallenge: undefined;
  RecoveryCodeChallenge: undefined;
  ForgotPasswordRequest: undefined;
  ResetPasswordConfirm: { email?: string; phone?: string };
};

export type ExceptionalStateStackParamList = {
  PreparingExperience: undefined;
  SessionExpired: { reason: string };
  AccountSuspended: { reason: string };
  UpdateRequired: { reason: string };
  Maintenance: { reason: string };
  ApiUnavailable: { reason: string };
  StorageUnavailable: { reason: string };
  VerticalUnavailable: { reason: string };
  InvalidAccess: { reason: string };
};

/**
 * Service Match/Review/Confirmation phase. Only real backend identifiers
 * cross this boundary -- no pricing, provider, serviceability, customer
 * identity or question-answer data (spec section 2). The Review screen
 * reloads all of that itself from `draftId`/`aiSessionId`.
 */
export type ReviewServiceRequestParams = {
  draftId: string;
  aiSessionId: string;
};

export type BookingConfirmationParams = {
  bookingId: string;
};

/** Booking Details (pending-assignment phase) -- same rule as Review/
 * Confirmation: only the real booking identifier crosses this boundary,
 * never status/pricing/provider/address (spec section 2). */
export type BookingDetailsParams = {
  bookingId: string;
};

export type CustomerAppStackParamList = {
  CustomerTabs: undefined;
  BookingReview: ReviewServiceRequestParams;
  BookingConfirmation: BookingConfirmationParams;
  BookingDetails: BookingDetailsParams;
  Notifications: undefined;
  EditProfile: undefined;
  Security: undefined;
  SavedAddresses: undefined;
  /** Edit loads the owned address by id from the canonical cache/API --
   * never receives the whole address object as a route param (spec
   * section 5). */
  AddAddress: undefined;
  EditAddress: { addressId: string };
  MfaManage: undefined;
  ManageSessions: undefined;
  LoginActivity: undefined;
  PrivacyData: undefined;
  PrivacyRequests: undefined;
  PrivacyRequestSubmitted: { requestId: string };
  PrivacyConsent: undefined;
  AssistantDataInfo: undefined;
  AccountDeletionRequest: undefined;
  /** Route params carry only the request ID -- the detail screen resolves
   * every displayed field from the authenticated backend itself, never
   * trusting a full request object passed as a param (spec section 2). */
  PrivacyRequestDetails: { requestId: string };
  DataExportRequest: undefined;
  DataCorrectionRequest: undefined;
  DeleteAccountFinalConfirmation: { reason: string };
  /** `mode` decides only where the picker sends the customer next --
   * "help" opens the real Booking Details for their own booking, "safety"
   * creates a real safety-report complaint scoped to it (spec section 5:
   * only `bookingId` ever crosses into the next screen). The general
   * Create Support Request flow now has its own internal booking picker
   * (Step 1 of the wizard) rather than routing through here first. */
  BookingSupportEntry: { mode: "help" | "safety" };
  SupportRequests: undefined;
  /** Entry point into the nested 3-step Create Support Request wizard
   * (`SupportRequestWizardNavigator`) -- params are forwarded to the
   * wizard's own `Topic` screen. The in-progress draft itself lives in
   * `SupportRequestWizardContext`, scoped to the wizard's lifetime, not
   * in navigation params (spec section 2). */
  CreateSupportRequest: { source?: "help_hub" | "support_requests" | "booking"; bookingId?: string } | undefined;
  SupportRequestDetails: { requestId: string };
  SafetyReport: { bookingId: string };
};

export type RootStackParamList = {
  Bootstrap: undefined;
  PublicStack: { screen: PublicRouteName } | undefined;
  CustomerAppStack: undefined;
  ExceptionalStateStack: { screen: ExceptionalRouteName; params: { reason: string } };
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
