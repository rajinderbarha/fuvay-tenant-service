import React from "react";
import { TextField, TextFieldProps } from "./TextField";
import { AppText } from "../typography/AppText";
import { useTheme } from "../../themes";

export type CurrencyFieldProps = Omit<TextFieldProps, "keyboardType" | "leadingIcon"> & {
  currencySymbol?: string;
};

/** Numeric-keyboard field for money entry. Formatting/parsing of the
 * currency value is a feature-layer concern -- this component only
 * constrains the keyboard and shows the currency symbol. */
export function CurrencyField({ currencySymbol = "₹", ...rest }: CurrencyFieldProps) {
  const { theme } = useTheme();
  return (
    <TextField
      keyboardType="decimal-pad"
      leadingIcon={<AppText variant="body" color="tertiary">{currencySymbol}</AppText>}
      {...rest}
    />
  );
}
