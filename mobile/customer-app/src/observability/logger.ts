import { environment } from "../config/environment";
import { redact } from "./redaction";

export type LogLevel = "debug" | "info" | "warn" | "error" | "fatal";

const LEVEL_ORDER: LogLevel[] = ["debug", "info", "warn", "error", "fatal"];

export interface LogContext {
  feature?: string;
  screen?: string;
  requestId?: string;
  correlationId?: string;
  [key: string]: unknown;
}

export interface CrashReportingAdapter {
  recordError(error: Error, context?: LogContext): void;
}

export interface AnalyticsAdapter {
  track(event: string, properties?: Record<string, unknown>): void;
}

let crashReportingAdapter: CrashReportingAdapter | null = null;
let analyticsAdapter: AnalyticsAdapter | null = null;

export function setCrashReportingAdapter(adapter: CrashReportingAdapter | null): void {
  crashReportingAdapter = adapter;
}

export function setAnalyticsAdapter(adapter: AnalyticsAdapter | null): void {
  analyticsAdapter = adapter;
}

function shouldLog(level: LogLevel): boolean {
  return LEVEL_ORDER.indexOf(level) >= LEVEL_ORDER.indexOf(environment.logLevel);
}

function emit(level: LogLevel, message: string, context?: LogContext): void {
  if (!shouldLog(level)) return;
  const safeContext = context ? redact(context) : undefined;

  // The only sanctioned console usage in the app — every other call site
  // must go through this logger instead of calling console.* directly.
  const payload = safeContext ? [message, safeContext] : [message];
  if (level === "debug") console.debug(...payload);
  else if (level === "info") console.info(...payload);
  else if (level === "warn") console.warn(...payload);
  else console.error(...payload);
}

export const logger = {
  debug: (message: string, context?: LogContext) => emit("debug", message, context),
  info: (message: string, context?: LogContext) => emit("info", message, context),
  warn: (message: string, context?: LogContext) => emit("warn", message, context),
  error: (message: string, error?: unknown, context?: LogContext) => {
    emit("error", message, context);
    if (crashReportingAdapter && error instanceof Error) {
      crashReportingAdapter.recordError(error, context);
    }
  },
  fatal: (message: string, error?: unknown, context?: LogContext) => {
    emit("fatal", message, context);
    if (crashReportingAdapter && error instanceof Error) {
      crashReportingAdapter.recordError(error, context);
    }
  },
  track: (event: string, properties?: Record<string, unknown>) => {
    if (!environment.analyticsEnabled) return;
    analyticsAdapter?.track(event, redact(properties) as Record<string, unknown>);
  },
};
