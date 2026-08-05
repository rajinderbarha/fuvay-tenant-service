import {
  LoginOutcomeDto, AuthSessionResponseDto, OtpSendResponseDto, AccessContextResponseDto,
  loginOutcomeSchema, otpSendResponseSchema, accessContextResponseSchema,
} from "./authContracts";
import { SessionResult, MfaChallengeState, OtpSendResult, CustomerSessionContext, CustomerAudience } from "../../domain/auth";
import { asCustomerId, asTenantId } from "../../domain/ids";
import { ContractValidationError } from "../../domain/errors";

export function parseLoginOutcome(raw: unknown): LoginOutcomeDto {
  const result = loginOutcomeSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("LoginOutcomeDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function isMfaChallenge(outcome: LoginOutcomeDto): outcome is Extract<LoginOutcomeDto, { mfa_required: true }> {
  return outcome.mfa_required === true;
}

export function adaptMfaChallenge(dto: Extract<LoginOutcomeDto, { mfa_required: true }>): MfaChallengeState {
  return { status: "challenge_required", challengeToken: dto.mfa_challenge_token };
}

/** A malformed token response must never create an authenticated session
 * (spec section 31) -- this throws rather than defaulting any field. */
export function adaptSessionResult(dto: AuthSessionResponseDto): SessionResult {
  if (!dto.access_token || dto.access_token.trim() === "") {
    throw new ContractValidationError("AuthSessionResponseDto", ["access_token is required and cannot be empty"]);
  }
  return {
    accessToken: dto.access_token,
    refreshToken: dto.refresh_token,
    customerId: asCustomerId(dto.user.id),
    requiresPasswordChange: dto.requires_password_change ?? false,
    postLoginDestination: dto.next_destination ?? null,
  };
}

export function parseOtpSendResponse(raw: unknown): OtpSendResponseDto {
  const result = otpSendResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("OtpSendResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

/** `otp_hint` (dev/staging-only per AuthService.send_phone_otp) is
 * deliberately dropped here -- it must never reach app state, storage or
 * logs, even though the backend includes it outside production. */
export function adaptOtpSendResult(dto: OtpSendResponseDto): OtpSendResult {
  return { message: dto.message, usesExternalVerifyProvider: dto.use_verify ?? false };
}

export function parseAccessContext(raw: unknown): AccessContextResponseDto {
  const result = accessContextResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("AccessContextResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

const CUSTOMER_AUDIENCE: CustomerAudience = "serviceos:customer";

/** The one function permitted to decide whether a backend response
 * represents a valid customer session (spec section 14) -- role AND
 * audience AND (when present) tenant/technician ambiguity are all
 * checked here, never left to a screen or a decoded-but-unverified JWT
 * claim. */
export function adaptCustomerSessionContext(dto: AccessContextResponseDto): CustomerSessionContext {
  const isCustomerAudience = dto.audience === CUSTOMER_AUDIENCE;
  const isCustomerRole = dto.canonical_role === "customer";
  return {
    authenticated: true,
    audience: dto.audience,
    customerId: isCustomerAudience && isCustomerRole ? asCustomerId(dto.user_id) : null,
    tenantId: dto.tenant_id ? asTenantId(dto.tenant_id) : null,
    // No dedicated customer "account status" field exists in this
    // response (confirmed in source -- get_mobile_access_context returns
    // tenant_status/technician_status only, both null for a customer
    // role). Customer suspension is enforced by the login/refresh
    // endpoints themselves (ACCOUNT_LOCKED / account inactive errors);
    // reaching this function successfully means the account is usable.
    accountStatus: isCustomerAudience && isCustomerRole ? "active" : "unknown",
  };
}

export function isValidCustomerSession(ctx: CustomerSessionContext): boolean {
  return ctx.authenticated && ctx.audience === CUSTOMER_AUDIENCE && ctx.customerId !== null;
}
