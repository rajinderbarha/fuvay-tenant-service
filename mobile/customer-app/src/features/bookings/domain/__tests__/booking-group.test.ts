import { groupForStatus } from "../booking-group";

describe("groupForStatus", () => {
  it("groups every real, reachable pre-terminal status as active", () => {
    expect(groupForStatus("pending_assignment")).toBe("active");
    expect(groupForStatus("assigned")).toBe("active");
    expect(groupForStatus("accepted")).toBe("active");
    expect(groupForStatus("scheduled")).toBe("active");
  });

  it("groups terminal statuses as past", () => {
    expect(groupForStatus("completed")).toBe("past");
    expect(groupForStatus("cancelled")).toBe("past");
  });

  it("groups an unrecognized status as active rather than silently hiding it in Past", () => {
    expect(groupForStatus("some_future_status")).toBe("active");
  });
});
