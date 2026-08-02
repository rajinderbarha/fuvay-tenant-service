import * as Crypto from "expo-crypto";
import { QueueItem, QueueItemState, OperationType } from "./types";
import { classify, isTransientFailure, isPermanentFailure } from "./operationRegistry";
import { loadQueue, saveQueue } from "./queueStorage";
import { getSessionGeneration } from "../auth/tokenCoordinator";
import { isOffline } from "../api/networkState";

/**
 * Queue orchestration (Phase Z spec sections 6, 13, 14). This module owns
 * dependency ordering/cycle detection, bounded backoff classification, and
 * "sync all now" eligibility -- it does NOT itself perform HTTP calls; the
 * actual per-operation execute function is supplied by the caller (a
 * typed dispatch map built from each feature's real API client, per spec
 * section 22's "no generic replay of arbitrary requests" requirement).
 */

const MAX_ATTEMPTS = 6;
const BASE_DELAY_MS = 2_000;
const MAX_DELAY_MS = 30 * 60_000; // 30 minutes

export function computeBackoff(attempt: number, retryAfterSeconds?: number): number {
  if (typeof retryAfterSeconds === "number") return retryAfterSeconds * 1000;
  const exponential = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** (attempt - 1));
  const jitter = Math.random() * exponential * 0.25;
  return Math.round(exponential + jitter);
}

export interface EnqueueInput {
  operation_type: OperationType;
  tenant_id: string;
  vertical_code: string;
  job_id?: string;
  entity_id?: string;
  local_entity_version?: number;
  dependencies?: string[];
  title: string;
  job_reference?: string;
  payload: Record<string, unknown>;
}

export function buildQueueItem(input: EnqueueInput): QueueItem {
  const now = new Date().toISOString();
  const def = classify(input.operation_type);
  return {
    local_id: Crypto.randomUUID(),
    operation_type: input.operation_type,
    operation_class: def.operation_class,
    session_generation: getSessionGeneration(),
    tenant_id: input.tenant_id,
    vertical_code: input.vertical_code,
    job_id: input.job_id,
    entity_id: input.entity_id,
    local_entity_version: input.local_entity_version,
    idempotency_key: Crypto.randomUUID(),
    dependencies: input.dependencies ?? [],
    state: def.operation_class === "LOCAL_DRAFT" ? "draft" : "waiting",
    attempt_count: 0,
    next_attempt_at: null,
    created_at: now,
    updated_at: now,
    title: input.title,
    job_reference: input.job_reference,
    payload: input.payload,
  };
}

/** Detects a dependency cycle via DFS. Returns true if `items` (as a
 * whole) contains any cycle -- used before ever accepting a new item. */
export function hasDependencyCycle(items: QueueItem[]): boolean {
  const byId = new Map(items.map(i => [i.local_id, i]));
  const WHITE = 0, GRAY = 1, BLACK = 2;
  const color = new Map<string, number>(items.map(i => [i.local_id, WHITE]));

  function visit(id: string): boolean {
    color.set(id, GRAY);
    const item = byId.get(id);
    for (const depId of item?.dependencies ?? []) {
      const depColor = color.get(depId);
      if (depColor === GRAY) return true;
      if (depColor === WHITE && visit(depId)) return true;
    }
    color.set(id, BLACK);
    return false;
  }

  for (const item of items) {
    if (color.get(item.local_id) === WHITE && visit(item.local_id)) return true;
  }
  return false;
}

/** True only once every dependency has reached server_confirmed. A
 * missing dependency (already removed/cancelled) also blocks -- it never
 * silently proceeds as if satisfied. */
export function dependenciesSatisfied(item: QueueItem, allItems: QueueItem[]): boolean {
  if (item.dependencies.length === 0) return true;
  const byId = new Map(allItems.map(i => [i.local_id, i]));
  return item.dependencies.every(depId => byId.get(depId)?.state === "server_confirmed");
}

/** True if any dependency has permanently failed/been cancelled -- the
 * child must show `blocked`, never silently retry forever (spec section 6). */
export function isBlockedByDependency(item: QueueItem, allItems: QueueItem[]): boolean {
  const byId = new Map(allItems.map(i => [i.local_id, i]));
  return item.dependencies.some(depId => {
    const dep = byId.get(depId);
    return !dep || dep.state === "failed" || dep.state === "cancelled" || dep.state === "conflict";
  });
}

/** Items eligible to attempt right now: not offline, session generation
 * matches the CURRENT session (never resumes a stale technician's item),
 * not already in a terminal/conflict/blocked state, dependencies met,
 * and (for retries) past next_attempt_at. */
export function eligibleForSync(items: QueueItem[]): QueueItem[] {
  if (isOffline()) return [];
  const currentGeneration = getSessionGeneration();
  const now = Date.now();
  return items.filter(item => {
    if (item.session_generation !== currentGeneration) return false;
    if (["server_confirmed", "cancelled", "conflict", "authentication_required"].includes(item.state)) return false;
    if (item.operation_class === "LOCAL_DRAFT" && item.state === "draft") return false;
    if (isBlockedByDependency(item, items)) return false;
    if (!dependenciesSatisfied(item, items)) return false;
    if (item.next_attempt_at && new Date(item.next_attempt_at).getTime() > now) return false;
    return true;
  });
}

/** Topologically orders eligible items so a parent always executes
 * before any child that depends on it. Throws if a cycle is present --
 * callers must run hasDependencyCycle() before this. */
export function orderByDependency(items: QueueItem[]): QueueItem[] {
  const byId = new Map(items.map(i => [i.local_id, i]));
  const visited = new Set<string>();
  const ordered: QueueItem[] = [];

  function visit(item: QueueItem) {
    if (visited.has(item.local_id)) return;
    visited.add(item.local_id);
    for (const depId of item.dependencies) {
      const dep = byId.get(depId);
      if (dep) visit(dep);
    }
    ordered.push(item);
  }

  items.forEach(visit);
  return ordered;
}

export type ExecuteResult = { ok: true } | { ok: false; errorCode: string; retryAfterSeconds?: number };
export type Executor = (item: QueueItem) => Promise<ExecuteResult>;

export interface SyncSummary {
  attempted: number;
  confirmed: number;
  failed: number;
  conflicted: number;
  skipped: number;
}

/**
 * "Sync all now" (spec section 14). Re-derives eligibility fresh each
 * call (never blindly replays the whole queue), executes in dependency
 * order, and stops advancing a branch once a parent fails/conflicts so a
 * child can never run before its parent is confirmed.
 */
export async function runSyncPass(userId: string, tenantId: string, execute: Executor): Promise<SyncSummary> {
  const summary: SyncSummary = { attempted: 0, confirmed: 0, failed: 0, conflicted: 0, skipped: 0 };
  if (isOffline()) return summary;

  let items = await loadQueue(userId, tenantId);
  if (hasDependencyCycle(items)) {
    // A cycle means the graph itself is invalid -- block everything
    // involved rather than guess an order.
    items = items.map(i => (i.dependencies.length > 0 ? { ...i, state: "blocked" as QueueItemState } : i));
    await saveQueue(userId, tenantId, items);
    return summary;
  }

  // Eligibility is re-derived after every item completes (not precomputed
  // once) so a child whose parent is confirmed mid-pass becomes eligible
  // within the SAME sync pass, rather than waiting for the next one.
  const attemptedIds = new Set<string>();
  for (;;) {
    const eligible = eligibleForSync(items).filter(i => !attemptedIds.has(i.local_id));
    if (eligible.length === 0) break;
    const item = orderByDependency(eligible)[0];
    const fresh = items.find(i => i.local_id === item.local_id)!;
    attemptedIds.add(item.local_id);
    summary.attempted += 1;
    items = items.map(i =>
      i.local_id === item.local_id ? { ...i, state: "uploading" as QueueItemState, updated_at: new Date().toISOString() } : i,
    );
    const result = await execute(fresh);
    const now = new Date().toISOString();
    if (result.ok) {
      summary.confirmed += 1;
      items = items.map(i => (i.local_id === item.local_id ? { ...i, state: "server_confirmed" as QueueItemState, updated_at: now } : i));
    } else if (result.errorCode === "STALE_ENTITY_VERSION" || result.errorCode === "CONFLICT" || result.errorCode === "STALE_WORKFLOW_VERSION" || result.errorCode === "QUOTE_NOT_CURRENT") {
      summary.conflicted += 1;
      items = items.map(i => (i.local_id === item.local_id ? { ...i, state: "conflict" as QueueItemState, last_error_code: result.errorCode, updated_at: now } : i));
    } else if (result.errorCode === "AUTH_REQUIRED" || result.errorCode === "ACCESS_TOKEN_EXPIRED" || result.errorCode === "REFRESH_TOKEN_EXPIRED") {
      items = items.map(i => (i.local_id === item.local_id ? { ...i, state: "authentication_required" as QueueItemState, last_error_code: result.errorCode, updated_at: now } : i));
    } else {
      const attempt = fresh.attempt_count + 1;
      const permanent = isPermanentFailure(result.errorCode) || attempt >= MAX_ATTEMPTS;
      summary.failed += 1;
      items = items.map(i =>
        i.local_id === item.local_id
          ? {
              ...i,
              state: (permanent ? "failed" : "waiting") as QueueItemState,
              attempt_count: attempt,
              last_error_code: result.errorCode,
              next_attempt_at: permanent || !isTransientFailure(result.errorCode)
                ? null
                : new Date(Date.now() + computeBackoff(attempt, result.retryAfterSeconds)).toISOString(),
              updated_at: now,
            }
          : i,
      );
    }
    await saveQueue(userId, tenantId, items);
  }

  return summary;
}
