import React from "react";
import { NumericText, NumericTextProps } from "../typography/NumericText";

export interface MoneyProps extends Omit<NumericTextProps, "children"> {
  /** Already-formatted amount as a number -- formatting/currency-symbol
   * placement is a presentation concern here; real currency conversion or
   * business rounding stays server-side. */
  amount: number;
  currencySymbol?: string;
}

export function Money({ amount, currencySymbol = "₹", ...rest }: MoneyProps) {
  const formatted = amount.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  return <NumericText {...rest}>{currencySymbol}{formatted}</NumericText>;
}
