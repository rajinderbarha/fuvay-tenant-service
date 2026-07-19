"use client";

import React, { useId } from "react";

type Status = "default" | "error" | "warning" | "success";

const statusColor: Record<Status, string> = {
  default: "var(--border)",
  error: "var(--danger)",
  warning: "var(--warning)",
  success: "var(--success)",
};

interface FieldWrapperProps {
  label?: string;
  required?: boolean;
  description?: string;
  message?: string;
  status?: Status;
  htmlFor: string;
  children: React.ReactNode;
}

function FieldWrapper({ label, required, description, message, status = "default", htmlFor, children }: FieldWrapperProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
      {label && (
        <label htmlFor={htmlFor} className="ds-text-label" style={{ color: "var(--text-primary)" }}>
          {label}
          {required && (
            <span style={{ color: "var(--danger)", marginLeft: "0.25rem" }} aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      {description && (
        <span className="ds-text-helper" style={{ color: "var(--text-secondary)" }}>
          {description}
        </span>
      )}
      {children}
      {message && (
        <span className="ds-text-helper" style={{ color: statusColor[status] }} role={status === "error" ? "alert" : undefined}>
          {message}
        </span>
      )}
    </div>
  );
}

const controlBase: React.CSSProperties = {
  fontFamily: "var(--font-family-base)",
  fontSize: "0.875rem",
  padding: "0.5rem 0.75rem",
  borderRadius: "var(--radius-md)",
  background: "var(--card-bg, var(--surface))",
  color: "var(--text-primary)",
  transition: "border-color var(--motion-fast), box-shadow var(--motion-fast)",
  width: "100%",
};

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  required?: boolean;
  description?: string;
  message?: string;
  status?: Status;
}

export function Input({ label, required, description, message, status = "default", id, disabled, readOnly, style, ...rest }: InputProps) {
  const autoId = useId();
  const fieldId = id || autoId;
  return (
    <FieldWrapper label={label} required={required} description={description} message={message} status={status} htmlFor={fieldId}>
      <input
        id={fieldId}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={status === "error"}
        className="ds-focus-visible"
        style={{
          ...controlBase,
          border: `1px solid ${statusColor[status]}`,
          opacity: disabled ? 0.6 : 1,
          background: readOnly ? "var(--bg-muted)" : controlBase.background,
          ...style,
        }}
        {...rest}
      />
    </FieldWrapper>
  );
}

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  required?: boolean;
  description?: string;
  message?: string;
  status?: Status;
}

export function Textarea({ label, required, description, message, status = "default", id, disabled, style, ...rest }: TextareaProps) {
  const autoId = useId();
  const fieldId = id || autoId;
  return (
    <FieldWrapper label={label} required={required} description={description} message={message} status={status} htmlFor={fieldId}>
      <textarea
        id={fieldId}
        disabled={disabled}
        aria-invalid={status === "error"}
        className="ds-focus-visible"
        style={{ ...controlBase, border: `1px solid ${statusColor[status]}`, opacity: disabled ? 0.6 : 1, minHeight: "5rem", resize: "vertical", ...style }}
        {...rest}
      />
    </FieldWrapper>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  label?: string;
  required?: boolean;
  description?: string;
  message?: string;
  status?: Status;
  options: SelectOption[];
  placeholder?: string;
}

export function Select({ label, required, description, message, status = "default", id, disabled, options, placeholder, style, ...rest }: SelectProps) {
  const autoId = useId();
  const fieldId = id || autoId;
  return (
    <FieldWrapper label={label} required={required} description={description} message={message} status={status} htmlFor={fieldId}>
      <select
        id={fieldId}
        disabled={disabled}
        aria-invalid={status === "error"}
        className="ds-focus-visible"
        style={{ ...controlBase, border: `1px solid ${statusColor[status]}`, opacity: disabled ? 0.6 : 1, ...style }}
        {...rest}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FieldWrapper>
  );
}
