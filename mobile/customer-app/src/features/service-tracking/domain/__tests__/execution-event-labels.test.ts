import { resolveExecutionEventLabelKey } from "../execution-event-labels";
import { logger } from "../../../../observability/logger";

jest.mock("../../../../observability/logger", () => ({ logger: { warn: jest.fn() } }));

describe("resolveExecutionEventLabelKey", () => {
  beforeEach(() => jest.clearAllMocks());

  it("maps every real, confirmed-emitted execution event type to a translation key", () => {
    expect(resolveExecutionEventLabelKey("technician_on_the_way")).toBe("serviceTracking.event.onTheWay");
    expect(resolveExecutionEventLabelKey("technician_reached_site")).toBe("serviceTracking.event.reachedSite");
    expect(resolveExecutionEventLabelKey("inspection_started")).toBe("serviceTracking.event.inspectionStarted");
    expect(resolveExecutionEventLabelKey("inspection_completed")).toBe("serviceTracking.event.inspectionCompleted");
    expect(resolveExecutionEventLabelKey("service_started")).toBe("serviceTracking.event.serviceStarted");
    expect(resolveExecutionEventLabelKey("work_done")).toBe("serviceTracking.event.workDone");
    expect(logger.warn).not.toHaveBeenCalled();
  });

  it("fails safe on an unmapped-but-real event type (e.g. diagnosis/photo/work-note events, deliberately out of this sprint's milestone-only scope)", () => {
    expect(resolveExecutionEventLabelKey("diagnosis_added")).toBeNull();
    expect(logger.warn).toHaveBeenCalledWith("execution_event_unmapped", { eventType: "diagnosis_added" });
  });

  it("fails safe on a wholly unrecognized event type without throwing", () => {
    expect(() => resolveExecutionEventLabelKey("some_future_event")).not.toThrow();
    expect(resolveExecutionEventLabelKey("some_future_event")).toBeNull();
  });
});
