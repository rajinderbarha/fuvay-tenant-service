const MONEY_KEYS = new Set([
  "addon_total",
  "base_price",
  "customer_max_price",
  "customer_min_price",
  "customer_total",
  "emergency_addon",
  "inspection_charge",
  "max_price",
  "min_price",
  "platform_fee",
  "selected_price_amount",
  "service_base_price",
  "standard_price",
  "visit_fee",
]);

const HUMANIZED_VALUE_KEYS = new Set([
  "city_tier",
  "payment_mode",
  "platform_fee_model",
  "pricing_mode",
  "pricing_model",
  "source",
]);

function numericValue(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value: number): string {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function humanize(value: string): string {
  const text = value.replace(/_/g, " ").trim().toLowerCase();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : value;
}

export function formatPriceSnapshotLabel(key: string): string {
  if (key.endsWith("_pct")) {
    return `${humanize(key.slice(0, -4))} (%)`;
  }
  return humanize(key).replace(/\bId\b/g, "ID");
}

export function formatPriceSnapshotValue(key: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";

  if (typeof value === "boolean") return value ? "Yes" : "No";

  const numeric = numericValue(value);
  if (key.endsWith("_pct") || key.endsWith("_percentage")) {
    return numeric === null ? String(value) : `${formatNumber(numeric)}%`;
  }

  if (MONEY_KEYS.has(key)) {
    return numeric === null ? String(value) : `₹${formatNumber(numeric)}`;
  }

  if (typeof value === "number") return formatNumber(value);

  if (typeof value === "string" && HUMANIZED_VALUE_KEYS.has(key)) {
    return humanize(value);
  }

  return String(value);
}
