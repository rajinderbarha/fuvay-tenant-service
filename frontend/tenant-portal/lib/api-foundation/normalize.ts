/**
 * FRONTEND-CONNECT-01 — Consolidated response-normalization helpers.
 *
 * Re-exports the existing safe* helpers from lib/status-format.ts (already
 * proven on the /provider/status page — do not fork behavior) and adds the
 * remaining ones the spec asks for that did not exist yet: safeTime,
 * safeBoolean, safeRequestId, safePrice, safeArray-with-generic already
 * existed. Every UI surface should import safe* from here going forward.
 */
export {
  safeNum as safeNumber,
  safeText,
  safeCurrency,
  safeDate,
  safeArray,
  safeStatus,
  safePercent,
} from "../status-format";

import { safeNum as _safeNum } from "../status-format";

export function safeTime(v: unknown, fallback = "—"): string {
  if (!v || typeof v !== "string") return fallback;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export function safeBoolean(v: unknown, fallback = false): boolean {
  if (typeof v === "boolean") return v;
  if (v === "true") return true;
  if (v === "false") return false;
  return fallback;
}

export function safeRequestId(v: unknown): string | null {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  return null;
}

/** Formats a rupee amount; unlike safeCurrency this never fabricates a value
 *  when the field is genuinely absent (returns "—" instead of "₹0"). */
export function safePrice(v: unknown, currency = "INR"): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = _safeNum(v, NaN);
  if (!Number.isFinite(n)) return "—";
  const symbol = currency === "INR" ? "₹" : currency + " ";
  return `${symbol}${n.toLocaleString("en-IN")}`;
}
