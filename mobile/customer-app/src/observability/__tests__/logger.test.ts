describe("logger", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    jest.restoreAllMocks();
  });

  it("logs debug messages when log level is debug (development)", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "development";
    process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";
    process.env.EXPO_PUBLIC_LOG_LEVEL = "debug";
    const debugSpy = jest.spyOn(console, "debug").mockImplementation(() => {});
    const { logger } = require("../logger");
    logger.debug("test.debug");
    expect(debugSpy).toHaveBeenCalled();
  });

  it("excludes debug-level details when log level is warn (production-like)", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    process.env.EXPO_PUBLIC_LOG_LEVEL = "warn";
    const debugSpy = jest.spyOn(console, "debug").mockImplementation(() => {});
    const { logger } = require("../logger");
    logger.debug("test.debug");
    expect(debugSpy).not.toHaveBeenCalled();
  });

  it("redacts sensitive context before it reaches console output", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "development";
    process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";
    process.env.EXPO_PUBLIC_LOG_LEVEL = "debug";
    const infoSpy = jest.spyOn(console, "info").mockImplementation(() => {});
    const { logger } = require("../logger");
    logger.info("test.info", { token: "super-secret" });
    const [, context] = infoSpy.mock.calls[0];
    expect(JSON.stringify(context)).not.toContain("super-secret");
  });

  it("retains safe correlation metadata (requestId) alongside redaction", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "development";
    process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";
    process.env.EXPO_PUBLIC_LOG_LEVEL = "debug";
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    const { logger } = require("../logger");
    logger.error("test.error", new Error("boom"), { requestId: "req_abc" });
    const [, context] = errorSpy.mock.calls[0];
    expect((context as { requestId?: string }).requestId).toBe("req_abc");
  });

  it("routes caught errors to the registered crash-reporting adapter", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "development";
    process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";
    const { logger, setCrashReportingAdapter } = require("../logger");
    const recordError = jest.fn();
    setCrashReportingAdapter({ recordError });
    const error = new Error("boom");
    jest.spyOn(console, "error").mockImplementation(() => {});
    logger.error("test.error", error);
    expect(recordError).toHaveBeenCalledWith(error, undefined);
    setCrashReportingAdapter(null);
  });
});
