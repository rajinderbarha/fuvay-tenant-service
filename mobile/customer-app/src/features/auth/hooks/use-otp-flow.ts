import { useCallback, useState } from "react";
import { Platform } from "react-native";
import { authApi } from "../api/auth-api";
import { isValidPhone, isValidOtp, normalizePhone } from "../domain/phone-validation";
import { toCustomerSession } from "../domain/session";
import { persistSession } from "../state/session-store";
import { ApiError } from "../../../api/api-errors";
import { reevaluateStartup } from "../../../app/startup/startup-service";

export type OtpFlowStep = "enter-phone" | "enter-otp" | "verifying" | "sending";

export interface UseOtpFlowResult {
  step: OtpFlowStep;
  phone: string;
  setPhone: (phone: string) => void;
  otp: string;
  setOtp: (otp: string) => void;
  error: string | null;
  /** Dev-only OTP hint from the backend's non-Twilio fallback path — never set in a production build. */
  devOtpHint: string | null;
  sendOtp: () => Promise<void>;
  verifyOtp: () => Promise<boolean>;
  reset: () => void;
}

function safeErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.category === "rate_limited") return "Too many attempts. Please wait a moment and try again.";
    if (err.category === "unauthorized") return "Incorrect or expired code. Please try again.";
    if (err.category === "not_found") return "No account found for this number.";
    if (err.category === "validation_error") return "Please check the details you entered.";
    return "Something went wrong. Please try again.";
  }
  return "Something went wrong. Please try again.";
}

export function useOtpFlow(): UseOtpFlowResult {
  const [step, setStep] = useState<OtpFlowStep>("enter-phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);

  const sendOtp = useCallback(async () => {
    setError(null);
    const normalized = normalizePhone(phone);
    if (!isValidPhone(normalized)) {
      setError("Enter a valid phone number.");
      return;
    }
    setStep("sending");
    try {
      const result = await authApi.sendOtp(normalized, "phone_login");
      setDevOtpHint(__DEV__ ? (result.otp_hint ?? null) : null);
      setStep("enter-otp");
    } catch (err) {
      setError(safeErrorMessage(err));
      setStep("enter-phone");
    }
  }, [phone]);

  const verifyOtp = useCallback(async (): Promise<boolean> => {
    setError(null);
    if (!isValidOtp(otp)) {
      setError("Enter the 6-digit code.");
      return false;
    }
    setStep("verifying");
    try {
      const normalized = normalizePhone(phone);
      const result = await authApi.verifyOtp(normalized, otp, "mobile", Platform.OS);
      const profile = await authApi.me().catch(() => result.user);
      await persistSession(toCustomerSession({ accessToken: result.access_token, refreshToken: result.refresh_token }, profile));
      void reevaluateStartup();
      return true;
    } catch (err) {
      setError(safeErrorMessage(err));
      setStep("enter-otp");
      return false;
    }
  }, [phone, otp]);

  const reset = useCallback(() => {
    setStep("enter-phone");
    setPhone("");
    setOtp("");
    setError(null);
    setDevOtpHint(null);
  }, []);

  return { step, phone, setPhone, otp, setOtp, error, devOtpHint, sendOtp, verifyOtp, reset };
}
