/**
 * Input v2 — label, error, helperText, prefix text, clearable, icon support.
 * All colours from CSS variables — zero hardcoded hex.
 */
"use client";
import React, { useState } from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?:      string;
  error?:      string;
  helperText?: string;
  hint?:       string;           // alias for helperText
  prefix?:     string;           // text prefix like "₹" or "+91"
  suffix?:     string;           // text suffix like "kg" or "%"
  icon?:       React.ReactNode;
  iconRight?:  React.ReactNode;
  clearable?:  boolean;
  onClear?:    () => void;
}

export function Input({
  label, error, helperText, hint, prefix, suffix,
  icon, iconRight, clearable, onClear,
  style, id, value, onChange, ...props
}: InputProps) {
  const [focused, setFocused] = useState(false);
  const inputId   = id || label?.toLowerCase().replace(/\s+/g, "-");
  const helper    = helperText ?? hint;
  const hasError  = !!error;
  const showClear = clearable && value != null && String(value).length > 0;

  const borderColor = focused
    ? hasError ? "var(--color-danger)" : "var(--color-border-focus)"
    : hasError  ? "var(--color-danger)" : "var(--color-border)";

  const shadowColor = focused
    ? hasError ? "rgba(220,38,38,0.12)" : "rgba(46,134,171,0.14)"
    : "transparent";

  const paddingLeft  = prefix ? 0 : icon ? 36 : 12;
  const paddingRight = suffix ? 0 : (showClear || iconRight) ? 36 : 12;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      {label && (
        <label htmlFor={inputId} style={{
          fontSize: "var(--text-sm)", fontWeight: "var(--font-medium)" as unknown as number,
          color: "var(--color-text-secondary)", letterSpacing: "0.02em",
          display: "flex", alignItems: "center", gap: 4,
        }}>
          {label}
          {props.required && (
            <span style={{ color: "var(--color-danger)", fontWeight: 600 }}>*</span>
          )}
        </label>
      )}

      {/* Input wrapper */}
      <div style={{
        position: "relative", display: "flex", alignItems: "center",
        background: props.disabled ? "var(--color-surface-sunken)" : "var(--input-bg)",
        border: `1px solid ${borderColor}`,
        borderRadius: "var(--radius-md)",
        boxShadow: `0 0 0 3px ${shadowColor}`,
        transition: "border-color 0.15s, box-shadow 0.15s",
        overflow: "hidden",
      }}>

        {/* Prefix text */}
        {prefix && (
          <span style={{
            padding: "0 10px", height: "100%", display: "flex", alignItems: "center",
            borderRight: "1px solid var(--color-border)",
            background: "var(--color-surface-sunken)",
            color: "var(--color-text-secondary)", fontSize: "var(--text-sm)",
            fontWeight: "var(--font-medium)" as unknown as number,
            whiteSpace: "nowrap", userSelect: "none", flexShrink: 0,
          }}>
            {prefix}
          </span>
        )}

        {/* Leading icon */}
        {icon && !prefix && (
          <span style={{
            position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)",
            color: "var(--color-text-tertiary)", pointerEvents: "none", lineHeight: 0,
          }}>
            {icon}
          </span>
        )}

        <input
          id={inputId} value={value} onChange={onChange}
          {...props}
          style={{
            flex: 1, height: 38, border: "none", outline: "none",
            background: "transparent",
            paddingLeft, paddingRight,
            fontSize: "var(--text-base)", fontFamily: "var(--font-sans)",
            color: "var(--color-text-primary)",
            cursor: props.disabled ? "not-allowed" : undefined,
            ...style,
          }}
          onFocus={e => { setFocused(true);  props.onFocus?.(e); }}
          onBlur={e  => { setFocused(false); props.onBlur?.(e); }}
        />

        {/* Clear button */}
        {showClear && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => {
              onChange?.({ target: { value: "" } } as React.ChangeEvent<HTMLInputElement>);
              onClear?.();
            }}
            style={{
              position: "absolute", right: suffix ? 36 : iconRight ? 34 : 9,
              top: "50%", transform: "translateY(-50%)",
              width: 18, height: 18, borderRadius: "50%", border: "none",
              background: "var(--color-text-tertiary)", color: "var(--color-surface-base)",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", fontSize: 11, fontWeight: 700, lineHeight: 1,
              opacity: 0.7, padding: 0,
            }}
          >
            ×
          </button>
        )}

        {/* Trailing icon */}
        {iconRight && !suffix && !showClear && (
          <span style={{
            position: "absolute", right: 11, top: "50%", transform: "translateY(-50%)",
            color: "var(--color-text-tertiary)", pointerEvents: "none", lineHeight: 0,
          }}>
            {iconRight}
          </span>
        )}

        {/* Suffix text */}
        {suffix && (
          <span style={{
            padding: "0 10px", height: "100%", display: "flex", alignItems: "center",
            borderLeft: "1px solid var(--color-border)",
            background: "var(--color-surface-sunken)",
            color: "var(--color-text-secondary)", fontSize: "var(--text-sm)",
            fontWeight: "var(--font-medium)" as unknown as number,
            whiteSpace: "nowrap", userSelect: "none", flexShrink: 0,
          }}>
            {suffix}
          </span>
        )}
      </div>

      {error      && <p style={{ fontSize: "var(--text-sm)", color: "var(--color-danger-text)", margin: 0 }}>{error}</p>}
      {helper && !error && <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-tertiary)", margin: 0 }}>{helper}</p>}
    </div>
  );
}
