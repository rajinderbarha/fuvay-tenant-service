/**
 * Logging abstraction. Screens/services call `logger`, never `console`
 * directly, so a real crash-reporting sink can be wired in later without
 * touching call sites. Dev-only console output; production is a silent
 * no-op until that sink exists.
 */
export interface Logger {
  debug(message: string, context?: Record<string, unknown>): void;
  info(message: string, context?: Record<string, unknown>): void;
  warn(message: string, context?: Record<string, unknown>): void;
  error(message: string, error?: unknown, context?: Record<string, unknown>): void;
}

export const logger: Logger = {
  debug(message, context) {
    if (__DEV__) console.debug(`[customer-app] ${message}`, context ?? "");
  },
  info(message, context) {
    if (__DEV__) console.info(`[customer-app] ${message}`, context ?? "");
  },
  warn(message, context) {
    if (__DEV__) console.warn(`[customer-app] ${message}`, context ?? "");
  },
  error(message, error, context) {
    if (__DEV__) console.error(`[customer-app] ${message}`, error, context ?? "");
  },
};
