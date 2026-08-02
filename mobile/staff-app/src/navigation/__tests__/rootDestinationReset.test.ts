import { destinationSignature, resetStateFor } from "../rootDestinationReset";
import { RootDestination } from "../guards/types";

describe("destinationSignature — used to decide whether a security-driven reset is needed", () => {
  it("differs across job routes for the same jobId (still resets on execution-child navigation)", () => {
    const detail: RootDestination = { tree: "JobExecutionStack", screen: "JobDetail", params: { jobId: "j1" } };
    const inspection: RootDestination = { tree: "JobExecutionStack", screen: "Inspection", params: { jobId: "j1" } };
    expect(destinationSignature(detail)).not.toBe(destinationSignature(inspection));
  });

  it("is identical for the same destination shape (no redundant resets)", () => {
    const a: RootDestination = { tree: "RestrictedStateStack", screen: "TenantSuspended", reasonCode: "TENANT_INACTIVE" };
    const b: RootDestination = { tree: "RestrictedStateStack", screen: "TenantSuspended", reasonCode: "TENANT_INACTIVE" };
    expect(destinationSignature(a)).toBe(destinationSignature(b));
  });

  it("differs between two different restricted-state screens", () => {
    const a: RootDestination = { tree: "RestrictedStateStack", screen: "AccountSuspended", reasonCode: "TECHNICIAN_INACTIVE" };
    const b: RootDestination = { tree: "RestrictedStateStack", screen: "TenantSuspended", reasonCode: "TENANT_INACTIVE" };
    expect(destinationSignature(a)).not.toBe(destinationSignature(b));
  });
});

describe("resetStateFor — navigation resets on security-context change (spec section 10)", () => {
  it("resets to a single AuthStack route on logout/session expiry (full reset, no back stack survives)", () => {
    const state = resetStateFor({ tree: "AuthStack", screen: "Login" });
    expect(state).toEqual({ index: 0, routes: [{ name: "AuthStack" }] });
  });

  it("forwards a SESSION_EXPIRED reasonCode into Login's own params, so it can show real session-expired context", () => {
    const state = resetStateFor({ tree: "AuthStack", screen: "Login", reasonCode: "SESSION_EXPIRED" });
    expect(state).toEqual({ index: 0, routes: [{ name: "AuthStack", params: { screen: "Login", params: { reasonCode: "SESSION_EXPIRED" } } }] });
  });

  it("resets to a single RestrictedStateStack route when tenant/technician suspension is detected", () => {
    const state = resetStateFor({ tree: "RestrictedStateStack", screen: "TenantSuspended", reasonCode: "TENANT_INACTIVE" });
    expect(state).toEqual({ index: 0, routes: [{ name: "RestrictedStateStack", params: { screen: "TenantSuspended", params: { reasonCode: "TENANT_INACTIVE" } } }] });
  });

  it("resets to AppTabs with no leftover job-execution route beneath it", () => {
    const state = resetStateFor({ tree: "AppTabs" });
    expect(state).toEqual({ index: 0, routes: [{ name: "AppTabs" }] });
  });

  it("resets into JobExecutionStack carrying only the jobId, never a whole job object", () => {
    const state = resetStateFor({ tree: "JobExecutionStack", screen: "JobDetail", params: { jobId: "j1" } });
    expect(state).toEqual({ index: 0, routes: [{ name: "JobExecutionStack", params: { screen: "JobDetail", params: { jobId: "j1" } } }] });
  });
});
