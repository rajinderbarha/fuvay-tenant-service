export interface ApiEnvelope<T> {
  data: T;
}

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RetryPolicy {
  maxAttempts: number;
  /** Only mutation-unsafe by default: GET is retryable, POST/PUT/PATCH/DELETE are not unless idempotencyKey is set. */
  retryableMethods: HttpMethod[];
  baseDelayMs: number;
}

export const defaultRetryPolicy: RetryPolicy = {
  maxAttempts: 2,
  retryableMethods: ["GET"],
  baseDelayMs: 300,
};

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
  skipAuth?: boolean;
  /** Required for any non-GET mutation the caller wants safely retried. */
  idempotencyKey?: string;
  signal?: AbortSignal;
}
