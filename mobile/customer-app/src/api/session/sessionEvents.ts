import { SessionState } from "./sessionStateMachine";
import { CustomerSessionContext } from "../../domain/auth";

export interface SessionSnapshot {
  state: SessionState;
  context: CustomerSessionContext | null;
  epoch: number;
}

type Listener = (snapshot: SessionSnapshot) => void;

const listeners = new Set<Listener>();
let current: SessionSnapshot = { state: "uninitialized", context: null, epoch: 0 };

export function getSessionSnapshot(): SessionSnapshot {
  return current;
}

export function publishSessionSnapshot(next: SessionSnapshot): void {
  current = next;
  listeners.forEach(l => l(current));
}

export function subscribeSessionSnapshot(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Test-only reset. */
export function __resetSessionEventsForTests(): void {
  current = { state: "uninitialized", context: null, epoch: 0 };
  listeners.clear();
}
