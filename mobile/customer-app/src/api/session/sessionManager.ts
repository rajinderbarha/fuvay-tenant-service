import * as authApi from "../auth/authApi";
import {
  parseLoginOutcome, isMfaChallenge, adaptMfaChallenge, adaptSessionResult,
  parseAccessContext, adaptCustomerSessionContext, isValidCustomerSession,
} from "../auth/authAdapters";
import { saveSession, loadSession, clearSession as clearVault, getInMemoryAccessToken } from "./tokenVault";
import { getRefreshedAccessToken, bumpSessionEpoch, getSessionEpoch } from "./refreshCoordinator";
import { clearProtectedState } from "./queryCacheSecurity";
import { SessionState, assertValidTransition } from "./sessionStateMachine";
import { getSessionSnapshot, publishSessionSnapshot } from "./sessionEvents";
import { CustomerSessionContext, MfaChallengeState } from "../../domain/auth";
import { CustomerId } from "../../domain/ids";
import { DomainError } from "../../domain/errors";
import { logger } from "../../utils/logger";
import { redact } from "../../utils/redact";

/**
 * The one session orchestrator (spec section 8/19/20). Every auth flow
 * (password, OTP, MFA-completion, refresh, logout, restore) goes through
 * here so Phase E's navigation resolver, the HTTP client's 401 recovery
 * path, and any future screen all observe the exact same state machine
 * instead of three independent copies of "am I logged in."
 */
let pendingMfaChallengeToken: string | null = null;
let currentCustomerId: CustomerId | null = null;

function setState(state: SessionState, context: CustomerSessionContext | null = getSessionSnapshot().context) {
  const prev = getSessionSnapshot();
  assertValidTransition(prev.state, state);
  publishSessionSnapshot({ state, context, epoch: getSessionEpoch() });
}

async function validateAndAdoptSession(accessToken: string, refreshToken: string | null): Promise<CustomerSessionContext> {
  const rawContext = await authApi.getAccessContext(accessToken);
  const dto = parseAccessContext(rawContext.data);
  const context = adaptCustomerSessionContext(dto);

  if (!isValidCustomerSession(context)) {
    logger.warn("session.invalid_audience", redact({ audience: context.audience }));
    setState("invalid_audience", context);
    await clearVault();
    return context;
  }

  currentCustomerId = context.customerId;
  await saveSession(accessToken, refreshToken, context.customerId as CustomerId);
  setState("authenticated", context);
  return context;
}

export async function restoreSession(): Promise<void> {
  // Idempotent guard: AuthProvider and useNavigationSnapshot may both
  // trigger this on mount depending on effect ordering -- only the first
  // call should actually run it.
  if (getSessionSnapshot().state !== "uninitialized") return;
  setState("restoring", null);
  const stored = await loadSession();
  if (!stored) {
    setState("unauthenticated", null);
    return;
  }
  currentCustomerId = stored.customerId as CustomerId;
  try {
    await validateAndAdoptSession(stored.accessToken, stored.refreshToken);
  } catch (err) {
    if (err instanceof DomainError && err.category === "AUTH_REQUIRED") {
      // Access token itself was rejected outright (not merely expired) --
      // attempt one refresh before giving up, mirroring the authenticated-
      // client's 401 recovery path.
      try {
        const refreshed = await getRefreshedAccessToken(stored.customerId as CustomerId);
        await validateAndAdoptSession(refreshed, null);
        return;
      } catch {
        setState("session_expired", null);
        await clearVault();
        return;
      }
    }
    setState("session_expired", null);
    await clearVault();
  }
}

export interface LoginWithPasswordInput {
  email: string;
  password: string;
  deviceId?: string;
  deviceName?: string;
  rememberDevice?: boolean;
}

async function handleLoginOutcome(rawOutcome: unknown): Promise<CustomerSessionContext | MfaChallengeState> {
  const outcome = parseLoginOutcome(rawOutcome);
  if (isMfaChallenge(outcome)) {
    const challenge = adaptMfaChallenge(outcome);
    pendingMfaChallengeToken = challenge.challengeToken;
    setState("mfa_required", null);
    return challenge;
  }
  const session = adaptSessionResult(outcome);
  return validateAndAdoptSession(session.accessToken, session.refreshToken);
}

export async function loginWithPassword(input: LoginWithPasswordInput): Promise<CustomerSessionContext | MfaChallengeState> {
  setState("authenticating", null);
  try {
    const res = await authApi.loginWithPassword(input);
    return await handleLoginOutcome(res.data);
  } catch (err) {
    setState("unauthenticated", null);
    throw err;
  }
}

export async function requestLoginOtp(phone: string) {
  // Requesting an OTP does not change session state -- it is a
  // pre-authentication side effect, not a transition.
  const res = await authApi.requestLoginOtp({ phone });
  return res.data;
}

/** Emails a sign-in code. Like the phone equivalent, requesting one is a
 * pre-authentication side effect and changes no session state. */
export async function requestEmailLoginOtp(email: string) {
  const res = await authApi.requestEmailOtp({ email });
  return res.data;
}

export async function verifyEmailLoginOtp(email: string, otp: string, deviceId?: string, deviceName?: string) {
  setState("authenticating", null);
  try {
    const res = await authApi.verifyEmailOtp({ email, otp, deviceId, deviceName });
    return await handleLoginOutcome(res.data);
  } catch (err) {
    setState("unauthenticated", null);
    throw err;
  }
}

export async function verifyLoginOtp(phone: string, otp: string, deviceId?: string, deviceName?: string) {
  setState("authenticating", null);
  try {
    const res = await authApi.verifyLoginOtp({ phone, otp, deviceId, deviceName });
    return await handleLoginOutcome(res.data);
  } catch (err) {
    setState("unauthenticated", null);
    throw err;
  }
}

export async function completeMfaChallenge(code: string, deviceId?: string, deviceName?: string, rememberDevice?: boolean) {
  if (!pendingMfaChallengeToken) {
    throw new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "No MFA challenge in progress" });
  }
  setState("authenticating", null);
  try {
    const res = await authApi.completeMfaChallenge({
      mfaChallengeToken: pendingMfaChallengeToken, code, deviceId, deviceName, rememberDevice,
    });
    const result = await handleLoginOutcome(res.data);
    pendingMfaChallengeToken = null;
    return result;
  } catch (err) {
    setState("mfa_required", null);
    throw err;
  }
}

/** Cancels an in-progress MFA challenge (e.g. the customer navigates
 * away) -- clears the challenge token from memory immediately, per spec
 * section 12 ("clear challenge state on ... cancellation"). */
export function cancelMfaChallenge(): void {
  pendingMfaChallengeToken = null;
  if (getSessionSnapshot().state === "mfa_required") {
    setState("unauthenticated", null);
  }
}

/**
 * Logout order matches spec section 19 exactly: mark logging-out state,
 * bump epoch (so any in-flight refresh is discarded), best-effort backend
 * revocation, clear vault regardless of network outcome, clear protected
 * caches, then land on `unauthenticated`.
 */
export async function logout(): Promise<void> {
  const accessToken = getInMemoryAccessToken();
  const previousCustomerId = currentCustomerId ?? undefined;
  bumpSessionEpoch();

  if (accessToken) {
    try {
      await authApi.logout(accessToken);
    } catch (err) {
      logger.warn("session.logout_backend_unreachable", redact({ message: (err as Error)?.message }));
      // Never trap the customer in the app because backend logout is
      // temporarily unreachable (spec section 19) -- local state is
      // cleared unconditionally below regardless of this failure.
    }
  }

  await clearVault();
  await clearProtectedState(previousCustomerId);
  currentCustomerId = null;
  pendingMfaChallengeToken = null;
  setState("unauthenticated", null);
}

export function getCurrentCustomerId(): CustomerId | null {
  return currentCustomerId;
}

/** Test-only reset. */
export function __resetSessionManagerForTests(): void {
  pendingMfaChallengeToken = null;
  currentCustomerId = null;
}
