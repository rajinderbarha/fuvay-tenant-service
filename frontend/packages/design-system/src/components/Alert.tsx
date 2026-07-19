"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";
import type { Tone } from "../tokens/motion";

const toneStyle: Record<Tone, { bg: string; border: string; text: string; icon: React.ComponentType<{ size?: number }> }> = {
  success: { bg: "var(--success-bg)", border: "var(--success-border)", text: "var(--success-text)", icon: CheckCircle2 },
  warning: { bg: "var(--warning-bg)", border: "var(--warning-border)", text: "var(--warning-text)", icon: AlertTriangle },
  danger: { bg: "var(--danger-bg)", border: "var(--danger-border)", text: "var(--danger-text)", icon: XCircle },
  info: { bg: "var(--info-bg)", border: "var(--info-border)", text: "var(--info-text)", icon: Info },
  neutral: { bg: "var(--neutral-bg)", border: "var(--neutral-border)", text: "var(--neutral-text)", icon: Info },
  brand: { bg: "var(--accent-muted)", border: "var(--brand)", text: "var(--brand)", icon: Info },
};

export interface AlertProps {
  tone?: Tone;
  title?: string;
  children?: React.ReactNode;
  onDismiss?: () => void;
}

export function Alert({ tone = "info", title, children, onDismiss }: AlertProps) {
  const s = toneStyle[tone];
  const Icon = s.icon;
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      style={{ display: "flex", gap: "0.625rem", padding: "0.75rem 1rem", background: s.bg, border: `1px solid ${s.border}`, borderRadius: "var(--radius-md)", color: s.text }}
    >
      <Icon size={18} />
      <div style={{ flex: 1 }}>
        {title && <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{title}</div>}
        {children && <div style={{ fontSize: "0.8125rem", marginTop: title ? "0.125rem" : 0 }}>{children}</div>}
      </div>
      {onDismiss && (
        <button aria-label="Dismiss" onClick={onDismiss} className="ds-focus-visible" style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}>
          <X size={16} />
        </button>
      )}
    </div>
  );
}

export interface Toast {
  id: string;
  tone?: Tone;
  title: string;
  description?: string;
}

let toastSeq = 0;
const listeners = new Set<(toasts: Toast[]) => void>();
let toasts: Toast[] = [];

function emit() {
  listeners.forEach((l) => l(toasts));
}

export function pushToast(toast: Omit<Toast, "id">, autoDismissMs = 4000) {
  const id = `toast-${++toastSeq}`;
  toasts = [...toasts, { ...toast, id }];
  emit();
  if (autoDismissMs > 0) {
    setTimeout(() => dismissToast(id), autoDismissMs);
  }
  return id;
}

export function dismissToast(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

/** Renders the live toast stack. Mount once near the root (e.g. alongside
 * ThemeProvider). Uses aria-live so screen readers announce new toasts. */
export function ToastViewport() {
  const [items, setItems] = useState<Toast[]>(toasts);
  useEffect(() => {
    listeners.add(setItems);
    return () => {
      listeners.delete(setItems);
    };
  }, []);

  return (
    <div
      aria-live="polite"
      style={{ position: "fixed", bottom: "1rem", right: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem", zIndex: 1400, maxWidth: "22rem" }}
    >
      {items.map((t) => (
        <div key={t.id} style={{ boxShadow: "var(--shadow-lg)", borderRadius: "var(--radius-md)" }}>
          <Alert tone={t.tone} title={t.title} onDismiss={() => dismissToast(t.id)}>
            {t.description}
          </Alert>
        </div>
      ))}
    </div>
  );
}
