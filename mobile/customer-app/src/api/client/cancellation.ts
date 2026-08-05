/**
 * Cancellation helpers (spec section 26). A request must be cancellable
 * on: screen/feature unmount, query replacement, session termination,
 * logout, account suspension, bootstrap reset. This wraps the platform
 * `AbortController` so call sites compose cancellation reasons instead of
 * juggling raw signals.
 */
export class RequestCancelledError extends Error {
  constructor(public readonly reason: string) {
    super(`Request cancelled: ${reason}`);
    this.name = "RequestCancelledError";
  }
}

export interface TimeoutSignalHandle {
  signal: AbortSignal;
  /** Must be called once the request settles (success or failure) --
   * otherwise the underlying timer keeps the process alive until
   * `timeoutMs` elapses, which is both a real resource leak and what was
   * causing test workers to hang past test completion. */
  clear: () => void;
}

export function createTimeoutSignal(timeoutMs: number, external?: AbortSignal): TimeoutSignalHandle {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onExternalAbort = () => controller.abort();
  external?.addEventListener("abort", onExternalAbort);

  const clear = () => {
    clearTimeout(timer);
    external?.removeEventListener("abort", onExternalAbort);
  };

  return { signal: controller.signal, clear };
}
