import { resolveNotificationCapability } from "../notificationCapability";

describe("resolveNotificationCapability", () => {
  it("never claims 'enabled' -- no push transport dependency exists in this app (confirmed via package.json audit)", () => {
    expect(resolveNotificationCapability()).toEqual({ kind: "unavailable" });
  });
});
