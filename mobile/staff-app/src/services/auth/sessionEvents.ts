import { AccessContext } from "../../navigation/guards/types";

/**
 * Typed event channel between session/API and navigation (Phase F spec
 * section 20). This module has ZERO imports from ../../navigation/session
 * or ../../navigation/RootNavigator -- navigation subscribes to this, this
 * never reaches back into navigation, keeping the dependency direction
 * one-way and acyclic (it does import navigation/guards/types for the
 * AccessContext shape, which is a pure type module with no React/nav code).
 */
export type SessionEvent =
  | { type: "SESSION_ESTABLISHED"; accessContext: AccessContext }
  | { type: "SESSION_REFRESHED" }
  | { type: "SESSION_EXPIRED"; reasonCode?: string }
  | { type: "SESSION_REVOKED"; reasonCode?: string }
  | { type: "SESSION_CLEARED"; reason: string }
  | { type: "ACCESS_CONTEXT_CHANGED"; accessContext: AccessContext }
  | { type: "ACCOUNT_RESTRICTED"; accessContext: AccessContext }
  | { type: "TENANT_RESTRICTED"; accessContext: AccessContext }
  | { type: "TECHNICIAN_RESTRICTED"; accessContext: AccessContext }
  | { type: "APP_UPDATE_REQUIRED" };

type Listener = (event: SessionEvent) => void;

const listeners = new Set<Listener>();

export function emitSessionEvent(event: SessionEvent): void {
  listeners.forEach(l => l(event));
}

export function subscribeSessionEvents(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Test-only reset. */
export function __resetSessionEventsForTests(): void {
  listeners.clear();
}
