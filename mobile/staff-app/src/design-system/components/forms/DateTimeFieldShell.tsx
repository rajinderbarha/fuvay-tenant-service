import React from "react";
import { SelectField, SelectFieldProps } from "./SelectField";

type ShellProps = Omit<SelectFieldProps, "placeholder"> & { placeholder?: string };

/**
 * Display/control shell for date and time entry -- Phase D provides the
 * pressable field chrome and accessible labeling only. The actual native
 * date/time picker (platform-specific) is wired in the feature layer that
 * owns the real value format; this keeps the design system free of a
 * business date-parsing decision.
 */
export function DateField({ placeholder = "Select date…", ...rest }: ShellProps) {
  return <SelectField placeholder={placeholder} {...rest} />;
}

export function TimeField({ placeholder = "Select time…", ...rest }: ShellProps) {
  return <SelectField placeholder={placeholder} {...rest} />;
}
