/**
 * TEMPORARY diagnostic — safe to delete along with app/debug_client_errors.py.
 *
 * Server-side capture proves what the API returned, but says nothing about a
 * crash that happens AFTER a successful response. This forwards uncaught
 * JS errors to the backend so the stack trace lands in the same capture log
 * as the requests around it.
 *
 * Deliberately fire-and-forget and fully swallowed: a diagnostic must never
 * turn a recoverable error into a second, louder one. It also never replaces
 * the existing handler -- the previous one is always called, so normal
 * red-screen/reporting behaviour is unchanged.
 */
import { ENV } from "../config/environment";

let installed = false;

function post(payload: Record<string, unknown>): void {
  try {
    void fetch(`${ENV.apiBaseUrl.replace(/\/$/, "")}/v1/_debug/client-error`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, at: new Date().toISOString() }),
    }).catch(() => {});
  } catch {
    /* diagnostics must never throw */
  }
}

export function installDebugClientErrorReporter(): void {
  if (installed) return;
  installed = true;

  // React Native / Hermes global handler.
  const errorUtils = (globalThis as { ErrorUtils?: {
    getGlobalHandler?: () => (e: unknown, isFatal?: boolean) => void;
    setGlobalHandler?: (h: (e: unknown, isFatal?: boolean) => void) => void;
  } }).ErrorUtils;

  if (errorUtils?.setGlobalHandler) {
    const previous = errorUtils.getGlobalHandler?.();
    errorUtils.setGlobalHandler((error: unknown, isFatal?: boolean) => {
      const e = error as { message?: string; stack?: string };
      post({ source: "ErrorUtils", fatal: !!isFatal, message: e?.message ?? String(error), stack: e?.stack });
      previous?.(error, isFatal);
    });
  }

  // Expo web runs in a browser, where uncaught errors surface here instead.
  const w = globalThis as unknown as {
    addEventListener?: (t: string, l: (ev: unknown) => void) => void;
  };
  if (typeof w.addEventListener === "function") {
    w.addEventListener("error", (ev: unknown) => {
      const e = ev as { message?: string; filename?: string; lineno?: number; error?: { stack?: string } };
      post({ source: "window.error", message: e?.message, file: e?.filename, line: e?.lineno, stack: e?.error?.stack });
    });
    w.addEventListener("unhandledrejection", (ev: unknown) => {
      const e = ev as { reason?: { message?: string; stack?: string } };
      post({ source: "unhandledrejection", message: e?.reason?.message ?? String(e?.reason), stack: e?.reason?.stack });
    });
  }
}
