import {
  buildQueueItem, hasDependencyCycle, dependenciesSatisfied, isBlockedByDependency,
  eligibleForSync, orderByDependency, computeBackoff, runSyncPass,
} from "../syncEngine";
import { loadQueue, saveQueue, clearQueue } from "../queueStorage";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { __resetTokenCoordinatorForTests, establishTokens } from "../../auth/tokenCoordinator";
import { __resetNetworkStateForTests } from "../../api/networkState";
import { QueueItem } from "../types";

jest.mock("../../api/networkState", () => {
  const actual = jest.requireActual("../../api/networkState");
  return { ...actual, isOffline: jest.fn(() => false) };
});
import { isOffline } from "../../api/networkState";

const USER = "user-1";
const TENANT = "tenant-1";

beforeEach(async () => {
  __resetTokenCoordinatorForTests();
  __resetNetworkStateForTests();
  (isOffline as jest.Mock).mockReturnValue(false);
  await clearQueue(USER, TENANT);
});

describe("buildQueueItem", () => {
  it("stamps the current session generation and derives class/state from the registry", () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" });
    const item = buildQueueItem({
      operation_type: "WORK_FINISH", tenant_id: TENANT, vertical_code: "home_services",
      title: "Work completed", payload: {},
    });
    expect(item.operation_class).toBe("IDEMPOTENT_MUTATION");
    expect(item.state).toBe("waiting");
    expect(item.session_generation).toBe(1);
    expect(item.idempotency_key).toBeTruthy();
  });

  it("gives LOCAL_DRAFT operations an initial draft state, not waiting", () => {
    const item = buildQueueItem({
      operation_type: "SUPPORT_REQUEST_CREATE", tenant_id: TENANT, vertical_code: "home_services",
      title: "Support draft", payload: {},
    });
    expect(item.state).toBe("draft");
  });
});

describe("dependency graph", () => {
  function item(overrides: Partial<QueueItem>): QueueItem {
    return {
      local_id: "1", operation_type: "WORK_START", operation_class: "IDEMPOTENT_MUTATION",
      session_generation: 0, tenant_id: TENANT, vertical_code: "home_services",
      idempotency_key: "k", dependencies: [], state: "waiting", attempt_count: 0,
      next_attempt_at: null, created_at: "", updated_at: "", title: "t", payload: {},
      ...overrides,
    };
  }

  it("detects a direct cycle", () => {
    const a = item({ local_id: "a", dependencies: ["b"] });
    const b = item({ local_id: "b", dependencies: ["a"] });
    expect(hasDependencyCycle([a, b])).toBe(true);
  });

  it("finds no cycle in a valid chain", () => {
    const a = item({ local_id: "a", dependencies: [] });
    const b = item({ local_id: "b", dependencies: ["a"] });
    const c = item({ local_id: "c", dependencies: ["b"] });
    expect(hasDependencyCycle([a, b, c])).toBe(false);
    expect(orderByDependency([c, b, a]).map(i => i.local_id)).toEqual(["a", "b", "c"]);
  });

  it("a child cannot execute before its parent is server_confirmed", () => {
    const parent = item({ local_id: "p", state: "waiting" });
    const child = item({ local_id: "c", dependencies: ["p"], state: "waiting" });
    expect(dependenciesSatisfied(child, [parent, child])).toBe(false);
    const confirmedParent = { ...parent, state: "server_confirmed" as const };
    expect(dependenciesSatisfied(child, [confirmedParent, child])).toBe(true);
  });

  it("blocks a child when its parent has failed", () => {
    const parent = item({ local_id: "p", state: "failed" });
    const child = item({ local_id: "c", dependencies: ["p"] });
    expect(isBlockedByDependency(child, [parent, child])).toBe(true);
  });

  it("blocks a child when its parent is missing entirely", () => {
    const child = item({ local_id: "c", dependencies: ["ghost"] });
    expect(isBlockedByDependency(child, [child])).toBe(true);
  });
});

describe("eligibleForSync", () => {
  function item(overrides: Partial<QueueItem>): QueueItem {
    return {
      local_id: "1", operation_type: "WORK_START", operation_class: "IDEMPOTENT_MUTATION",
      session_generation: 0, tenant_id: TENANT, vertical_code: "home_services",
      idempotency_key: "k", dependencies: [], state: "waiting", attempt_count: 0,
      next_attempt_at: null, created_at: "", updated_at: "", title: "t", payload: {},
      ...overrides,
    };
  }

  it("excludes everything when offline", () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    const a = item({ local_id: "a" });
    expect(eligibleForSync([a])).toEqual([]);
  });

  it("excludes items from a previous session generation", () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" }); // generation 1
    const stale = item({ local_id: "a", session_generation: 0 });
    expect(eligibleForSync([stale])).toEqual([]);
  });

  it("excludes conflict/cancelled/authentication_required/local-draft states", () => {
    const conflict = item({ local_id: "a", state: "conflict" });
    const cancelled = item({ local_id: "b", state: "cancelled" });
    const authRequired = item({ local_id: "c", state: "authentication_required" });
    const draft = item({ local_id: "d", state: "draft", operation_class: "LOCAL_DRAFT" });
    expect(eligibleForSync([conflict, cancelled, authRequired, draft])).toEqual([]);
  });

  it("excludes items whose next_attempt_at is in the future", () => {
    const future = item({ local_id: "a", next_attempt_at: new Date(Date.now() + 60_000).toISOString() });
    expect(eligibleForSync([future])).toEqual([]);
  });
});

describe("computeBackoff", () => {
  it("respects an explicit Retry-After over the exponential curve", () => {
    expect(computeBackoff(1, 30)).toBe(30_000);
  });

  it("grows with attempt number and stays within the bound", () => {
    const d1 = computeBackoff(1);
    const d5 = computeBackoff(5);
    expect(d5).toBeGreaterThan(d1);
    expect(d5).toBeLessThanOrEqual(30 * 60_000 * 1.25);
  });
});

describe("runSyncPass", () => {
  it("confirms a simple item and persists server_confirmed", async () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" });
    const item = buildQueueItem({ operation_type: "WORK_START", tenant_id: TENANT, vertical_code: "home_services", title: "Work started", payload: {} });
    await saveQueue(USER, TENANT, [item]);
    const summary = await runSyncPass(USER, TENANT, async () => ({ ok: true }));
    expect(summary.confirmed).toBe(1);
    const after = await loadQueue(USER, TENANT);
    expect(after[0].state).toBe("server_confirmed");
  });

  it("marks a conflict without retrying it, and never overwrites the item's own local data", async () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" });
    const item = buildQueueItem({ operation_type: "ESTIMATE_REVISE", tenant_id: TENANT, vertical_code: "home_services", title: "Estimate revision", payload: {} });
    await saveQueue(USER, TENANT, [item]);
    const summary = await runSyncPass(USER, TENANT, async () => ({ ok: false, errorCode: "STALE_ENTITY_VERSION" }));
    expect(summary.conflicted).toBe(1);
    const after = await loadQueue(USER, TENANT);
    expect(after[0].state).toBe("conflict");
  });

  it("schedules a bounded retry for a transient failure but marks permanent failure as failed", async () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" });
    const transientItem = buildQueueItem({ operation_type: "WORK_START", tenant_id: TENANT, vertical_code: "home_services", title: "t", payload: {} });
    await saveQueue(USER, TENANT, [transientItem]);
    await runSyncPass(USER, TENANT, async () => ({ ok: false, errorCode: "SERVER_UNAVAILABLE" }));
    let after = await loadQueue(USER, TENANT);
    expect(after[0].state).toBe("waiting");
    expect(after[0].next_attempt_at).toBeTruthy();

    const permanentItem = buildQueueItem({ operation_type: "WORK_START", tenant_id: TENANT, vertical_code: "home_services", title: "t", payload: {} });
    await saveQueue(USER, TENANT, [permanentItem]);
    await runSyncPass(USER, TENANT, async () => ({ ok: false, errorCode: "VALIDATION_ERROR" }));
    after = await loadQueue(USER, TENANT);
    expect(after[0].state).toBe("failed");
  });

  it("marks authentication_required on an auth failure instead of endlessly retrying", async () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" });
    const item = buildQueueItem({ operation_type: "NOTIFICATION_MARK_READ", tenant_id: TENANT, vertical_code: "home_services", title: "t", payload: {} });
    await saveQueue(USER, TENANT, [item]);
    const summary = await runSyncPass(USER, TENANT, async () => ({ ok: false, errorCode: "ACCESS_TOKEN_EXPIRED" }));
    expect(summary.confirmed).toBe(0);
    const after = await loadQueue(USER, TENANT);
    expect(after[0].state).toBe("authentication_required");
  });

  it("never executes a child before its parent is confirmed, within a single pass", async () => {
    establishTokens({ accessToken: "a", refreshToken: "r", sessionId: "s" });
    const parent = buildQueueItem({ operation_type: "INSPECTION_PHOTO_UPLOAD", tenant_id: TENANT, vertical_code: "home_services", title: "Photo", payload: {} });
    const child = buildQueueItem({ operation_type: "INSPECTION_SUBMIT", tenant_id: TENANT, vertical_code: "home_services", title: "Submit", payload: {}, dependencies: [parent.local_id] });
    await saveQueue(USER, TENANT, [parent, child]);
    const order: string[] = [];
    await runSyncPass(USER, TENANT, async item => {
      order.push(item.operation_type);
      return { ok: true };
    });
    expect(order).toEqual(["INSPECTION_PHOTO_UPLOAD", "INSPECTION_SUBMIT"]);
    const after = await loadQueue(USER, TENANT);
    expect(after.every(i => i.state === "server_confirmed")).toBe(true);
  });

  it("does nothing while offline", async () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    const item = buildQueueItem({ operation_type: "WORK_START", tenant_id: TENANT, vertical_code: "home_services", title: "t", payload: {} });
    await saveQueue(USER, TENANT, [item]);
    const summary = await runSyncPass(USER, TENANT, async () => ({ ok: true }));
    expect(summary.attempted).toBe(0);
  });
});

describe("queueStorage isolation and serialization", () => {
  it("scopes queues per user+tenant so one user's queue never leaks into another's", async () => {
    const itemA = buildQueueItem({ operation_type: "WORK_START", tenant_id: "tenant-a", vertical_code: "home_services", title: "t", payload: {} });
    const itemB = buildQueueItem({ operation_type: "WORK_START", tenant_id: "tenant-b", vertical_code: "home_services", title: "t", payload: {} });
    await saveQueue("user-a", "tenant-a", [itemA]);
    await saveQueue("user-b", "tenant-b", [itemB]);
    expect((await loadQueue("user-a", "tenant-a")).map(i => i.local_id)).toEqual([itemA.local_id]);
    expect((await loadQueue("user-b", "tenant-b")).map(i => i.local_id)).toEqual([itemB.local_id]);
  });

  it("round-trips a saved queue exactly through JSON serialization", async () => {
    const item = buildQueueItem({ operation_type: "DOCUMENT_UPLOAD", tenant_id: TENANT, vertical_code: "home_services", title: "Doc", payload: { note: "n" } });
    await saveQueue(USER, TENANT, [item]);
    const loaded = await loadQueue(USER, TENANT);
    expect(loaded).toEqual([item]);
  });

  it("quarantines a corrupted record instead of throwing", async () => {
    await AsyncStorage.setItem("serviceos.staffapp.syncqueue.v1.user-1.tenant-1", "{not valid json");
    const loaded = await loadQueue(USER, TENANT);
    expect(loaded).toEqual([]);
  });
});
