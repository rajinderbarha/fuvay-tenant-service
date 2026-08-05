/**
 * Money handling. Backend truth (app/engines/pricing/models.py): amounts
 * are `Numeric(10,2)` Decimal columns, currency is a `String(5)` defaulting
 * to "INR" (app/engines/home_service_booking prices flow through
 * `price_snapshot` JSONB built from those same Decimal values). Over JSON
 * transport a Decimal may arrive as either a numeric literal or a decimal
 * string depending on the serializer path -- this module accepts both and
 * never performs float arithmetic: every amount is normalized to integer
 * minor units (paise) immediately on parse.
 */
import { DomainError } from "./errors";

export interface Money {
  /** Integer minor units (paise for INR) -- never a float. */
  minorUnits: number;
  currency: string;
}

const DEFAULT_CURRENCY = "INR";
const MINOR_UNIT_SCALE = 100;

/** Parses a backend decimal amount (number or numeric string) into Money.
 * Throws a DomainError rather than silently coercing a malformed value --
 * the caller (an adapter) is expected to translate that into a
 * ContractValidationError with full context. */
export function parseMoney(raw: unknown, currency: string = DEFAULT_CURRENCY): Money {
  let numeric: number;
  if (typeof raw === "number") {
    numeric = raw;
  } else if (typeof raw === "string" && raw.trim() !== "" && !Number.isNaN(Number(raw))) {
    numeric = Number(raw);
  } else {
    throw new DomainError({
      category: "CONTRACT_MISMATCH",
      diagnostic: `parseMoney received a non-numeric value: ${JSON.stringify(raw)}`,
    });
  }
  // Round at the paise boundary explicitly (never rely on float display
  // rounding) -- this is the one and only arithmetic operation performed
  // on the raw value before it becomes an integer.
  const minorUnits = Math.round(numeric * MINOR_UNIT_SCALE);
  return { minorUnits, currency };
}

export function addMoney(a: Money, b: Money): Money {
  if (a.currency !== b.currency) {
    throw new DomainError({
      category: "CONTRACT_MISMATCH",
      diagnostic: `Cannot add Money of different currencies: ${a.currency} + ${b.currency}`,
    });
  }
  return { minorUnits: a.minorUnits + b.minorUnits, currency: a.currency };
}

/** Display-only formatting. Never use this output as an input to further
 * arithmetic. */
export function formatMoney(money: Money, locale: string = "en-IN"): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency: money.currency }).format(
    money.minorUnits / MINOR_UNIT_SCALE,
  );
}
