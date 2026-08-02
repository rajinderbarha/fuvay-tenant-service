"use client";
import React, { useState } from "react";
import {
  Plus, Pencil, Trash2, Eye, X, CheckCircle2, AlertTriangle,
  XCircle, Info, TrendingUp, TrendingDown, Minus, ChevronRight,
  MoreHorizontal,
} from "lucide-react";

// ── Button ──────────────────────────────────────────────────────────────────
type BV = "primary" | "secondary" | "ghost" | "danger" | "success" | "warning";
type BS = "xs" | "sm" | "md" | "lg";
export function Btn({
  children, variant = "primary", size = "md", loading, icon, iconRight,
  fullWidth, onClick, type = "button", disabled, style = {},
}: {
  children?: React.ReactNode; variant?: BV; size?: BS; loading?: boolean;
  icon?: React.ReactNode; iconRight?: React.ReactNode; fullWidth?: boolean;
  onClick?: () => void; type?: "button" | "submit"; disabled?: boolean;
  style?: React.CSSProperties;
}) {
  const [hov, setHov] = useState(false);
  const V: Record<BV, React.CSSProperties> = {
    primary:  { background: "var(--primary-gradient)", color: "var(--text-on-brand)", border: "none", boxShadow: hov ? "var(--shadow-md)" : "var(--shadow-sm)" },
    secondary:{ background: hov ? "var(--surface-sunken)" : "var(--surface)", color: "var(--text-primary)", border: "1px solid var(--border)" },
    ghost:    { background: hov ? "var(--accent-muted)"  : "transparent",     color: "var(--text-secondary)", border: "none" },
    danger:   { background: hov ? "var(--danger-border)" : "var(--danger-bg)",  color: "var(--danger-text)",  border: "1px solid var(--danger-border)"  },
    success:  { background: hov ? "var(--success-border)": "var(--success-bg)", color: "var(--success-text)", border: "1px solid var(--success-border)" },
    warning:  { background: hov ? "var(--warning-border)": "var(--warning-bg)", color: "var(--warning-text)", border: "1px solid var(--warning-border)" },
  };
  const S: Record<BS, React.CSSProperties> = {
    xs: { padding: "4px 10px",  fontSize: 11, borderRadius: 7,  height: 26, gap: 4 },
    sm: { padding: "6px 14px",  fontSize: 12, borderRadius: 9,  height: 32, gap: 5 },
    md: { padding: "8px 18px",  fontSize: 13, borderRadius: 10, height: 38, gap: 6 },
    lg: { padding: "10px 22px", fontSize: 14, borderRadius: 12, height: 44, gap: 7 },
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled || loading}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        fontWeight: 500, cursor: disabled || loading ? "not-allowed" : "pointer",
        transition: "all 0.15s", whiteSpace: "nowrap", fontFamily: "inherit",
        opacity: disabled || loading ? 0.55 : 1,
        width: fullWidth ? "100%" : undefined,
        ...V[variant], ...S[size], ...style,
      }}>
      {loading ? <Spinner size={13}/> : icon}
      {children}
      {!loading && iconRight}
    </button>
  );
}

// ── IconBtn — square icon-only button (for table actions, toolbars) ──────────
type IconBtnV = "default" | "danger" | "success" | "warning" | "ghost";
export function IconBtn({
  icon, onClick, tooltip, variant = "default", size = "md", disabled,
}: {
  icon: React.ReactNode; onClick?: () => void; tooltip?: string;
  variant?: IconBtnV; size?: "sm" | "md" | "lg"; disabled?: boolean;
}) {
  const [hov, setHov] = useState(false);
  const dim = { sm: 28, md: 32, lg: 36 }[size];
  const rad = { sm: 7,  md: 8,  lg: 9  }[size];
  const ico = { sm: 13, md: 14, lg: 16 }[size];
  const V: Record<IconBtnV, React.CSSProperties> = {
    default: { background: hov ? "var(--surface-sunken)" : "transparent", color: "var(--text-secondary)", border: "1px solid transparent" },
    ghost:   { background: hov ? "var(--accent-muted)"  : "transparent", color: "var(--accent)",          border: "1px solid transparent" },
    danger:  { background: hov ? "var(--danger-bg)"     : "transparent", color: "var(--danger-text)",     border: "1px solid transparent" },
    success: { background: hov ? "var(--success-bg)"    : "transparent", color: hov ? "var(--success-text)" : "var(--text-tertiary)", border: "1px solid transparent" },
    warning: { background: hov ? "var(--warning-bg)"    : "transparent", color: hov ? "var(--warning-text)" : "var(--text-tertiary)", border: "1px solid transparent" },
  };
  return (
    <button
      onClick={onClick} disabled={disabled} title={tooltip}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        width: dim, height: dim, borderRadius: rad,
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "inherit", flexShrink: 0,
        transition: "all 0.12s", opacity: disabled ? 0.4 : 1,
        fontSize: ico,
        ...V[variant],
      }}>
      {React.isValidElement(icon)
        ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: ico })
        : icon}
    </button>
  );
}

// ── Action icon buttons (convenience wrappers) ────────────────────────────────
export function AddBtn(p: { onClick?: () => void; tooltip?: string; size?: "sm"|"md"|"lg"; label?: string }) {
  if (p.label) return (
    <Btn variant="primary" size={p.size === "sm" ? "sm" : "md"} icon={<Plus size={14}/>} onClick={p.onClick}>{p.label}</Btn>
  );
  return <IconBtn icon={<Plus/>} onClick={p.onClick} tooltip={p.tooltip ?? "Add"} variant="ghost" size={p.size ?? "md"}/>;
}
export function EditBtn(p: { onClick?: () => void; tooltip?: string; size?: "sm"|"md"|"lg" }) {
  return <IconBtn icon={<Pencil/>} onClick={p.onClick} tooltip={p.tooltip ?? "Edit"} variant="default" size={p.size ?? "sm"}/>;
}
export function DeleteBtn(p: { onClick?: () => void; tooltip?: string; size?: "sm"|"md"|"lg" }) {
  return <IconBtn icon={<Trash2/>} onClick={p.onClick} tooltip={p.tooltip ?? "Delete"} variant="danger" size={p.size ?? "sm"}/>;
}
export function ViewBtn(p: { onClick?: () => void; tooltip?: string; size?: "sm"|"md"|"lg" }) {
  return <IconBtn icon={<Eye/>} onClick={p.onClick} tooltip={p.tooltip ?? "View"} variant="default" size={p.size ?? "sm"}/>;
}
export function MoreBtn(p: { onClick?: () => void; tooltip?: string }) {
  return <IconBtn icon={<MoreHorizontal/>} onClick={p.onClick} tooltip={p.tooltip ?? "More"} variant="default" size="sm"/>;
}

// ── RowActions — pre-built action cell for DataTable ─────────────────────────
export function RowActions({
  onView, onEdit, onDelete, extra,
}: {
  onView?: () => void; onEdit?: () => void; onDelete?: () => void;
  extra?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
      {onView   && <ViewBtn   onClick={onView}/>}
      {onEdit   && <EditBtn   onClick={onEdit}/>}
      {onDelete && <DeleteBtn onClick={onDelete}/>}
      {extra}
    </div>
  );
}

// ── Badge ───────────────────────────────────────────────────────────────────
type BadgeV = "default" | "success" | "warning" | "danger" | "info" | "muted" | "golden" | "terra";
export function Badge({ children, variant = "default", size = "md", dot }: {
  children: React.ReactNode; variant?: BadgeV; size?: "sm" | "md" | "lg"; dot?: boolean;
}) {
  const V: Record<BadgeV, React.CSSProperties> = {
    default:{ background: "var(--accent-muted)",     color: "var(--accent)",        border: "1px solid transparent"              },
    success:{ background: "var(--success-bg)",        color: "var(--success-text)",  border: "1px solid var(--success-border)"    },
    warning:{ background: "var(--warning-bg)",        color: "var(--warning-text)",  border: "1px solid var(--warning-border)"    },
    danger: { background: "var(--danger-bg)",         color: "var(--danger-text)",   border: "1px solid var(--danger-border)"     },
    info:   { background: "var(--info-bg)",           color: "var(--info-text)",     border: "1px solid var(--info-border)"       },
    muted:  { background: "var(--surface-sunken)",    color: "var(--text-tertiary)", border: "1px solid var(--border)"            },
    golden: { background: "var(--golden-bg)",         color: "var(--golden-text)",   border: "1px solid var(--golden-border)"     },
    terra:  { background: "var(--terra-bg)",          color: "var(--terra-text)",    border: "1px solid var(--terra-border)"      },
  };
  const S: Record<string, React.CSSProperties> = {
    sm: { fontSize: 10, padding: "2px 7px" },
    md: { fontSize: 11, padding: "3px 9px" },
    lg: { fontSize: 12, padding: "4px 12px" },
  };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      borderRadius: 999, fontWeight: 700, letterSpacing: "0.03em",
      whiteSpace: "nowrap", ...V[variant], ...S[size],
    }}>
      {dot && <span style={{ width: 5, height: 5, borderRadius: "50%", background: "currentColor", flexShrink: 0 }}/>}
      {children}
    </span>
  );
}

// ── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, style = {}, padding = 20, hover = false, onClick }: {
  children: React.ReactNode; style?: React.CSSProperties; padding?: number;
  hover?: boolean; onClick?: () => void;
}) {
  const [hov, setHov] = useState(false);
  return (
    <div onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{
      background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-xl, 1rem)",
      padding, boxShadow: hov && hover ? "var(--shadow-md)" : "var(--shadow-sm)",
      transform: hov && hover ? "translateY(-1px)" : "none",
      borderColor: hov && hover ? "var(--border-strong)" : "var(--border)",
      transition: "all 0.15s ease", cursor: onClick ? "pointer" : undefined, ...style,
    }}>{children}</div>
  );
}

// ── CardHeader — icon + title + subtitle + actions in one line ───────────────
export function CardHeader({ icon, title, subtitle, actions, accent }: {
  icon?: React.ReactNode; title: string; subtitle?: string;
  actions?: React.ReactNode; accent?: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {icon && (
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: accent ? `${accent}18` : "var(--accent-muted)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: accent ?? "var(--accent)", flexShrink: 0,
            border: `1px solid ${accent ? `${accent}30` : "var(--border)"}`,
          }}>
            {React.isValidElement(icon)
              ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: 16 })
              : icon}
          </div>
        )}
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: 0, lineHeight: 1.3 }}>{title}</h3>
          {subtitle && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{subtitle}</p>}
        </div>
      </div>
      {actions && <div style={{ display: "flex", alignItems: "center", gap: 6 }}>{actions}</div>}
    </div>
  );
}

// ── Input ────────────────────────────────────────────────────────────────────
export function Input({ label, placeholder, value, onChange, error, hint, icon, type = "text", disabled, required }: {
  label?: string; placeholder?: string; value?: string; onChange?: (v: string) => void;
  error?: string; hint?: string; icon?: React.ReactNode; type?: string;
  disabled?: boolean; required?: boolean;
}) {
  const id = label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      {label && (
        <label htmlFor={id} style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", letterSpacing: "0.02em" }}>
          {label}{required && <span style={{ color: "var(--danger)", marginLeft: 3 }}>*</span>}
        </label>
      )}
      <div style={{ position: "relative" }}>
        {icon && (
          <span style={{
            position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)",
            color: "var(--text-tertiary)", pointerEvents: "none",
            display: "flex", alignItems: "center",
          }}>{React.isValidElement(icon) ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: 14 }) : icon}</span>
        )}
        <input id={id} type={type} value={value} disabled={disabled} placeholder={placeholder}
          onChange={e => onChange?.(e.target.value)}
          style={{
            width: "100%", height: 38, padding: icon ? "0 12px 0 36px" : "0 12px",
            fontSize: 14, fontFamily: "inherit",
            background: disabled ? "var(--surface-sunken)" : "var(--surface)",
            border: `1px solid ${error ? "var(--danger)" : "var(--border)"}`,
            borderRadius: 10, color: "var(--text-primary)", outline: "none",
            boxShadow: "var(--shadow-sm)", transition: "border-color 0.15s", boxSizing: "border-box",
          }}
          onFocus={e => { e.currentTarget.style.borderColor = error ? "var(--danger)" : "var(--border-focus)"; e.currentTarget.style.boxShadow = `0 0 0 3px ${error ? "rgba(192,57,43,0.10)" : "rgba(63,117,108,0.12)"}`; }}
          onBlur={e  => { e.currentTarget.style.borderColor = error ? "var(--danger)" : "var(--border)"; e.currentTarget.style.boxShadow = "var(--shadow-sm)"; }}
        />
      </div>
      {error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{error}</p>}
      {hint && !error && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{hint}</p>}
    </div>
  );
}

// ── Select ───────────────────────────────────────────────────────────────────
export function Select({ label, value, onChange, options, placeholder, disabled }: {
  label?: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder?: string; disabled?: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      {label && <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", letterSpacing: "0.02em" }}>{label}</label>}
      <select value={value} onChange={e => onChange(e.target.value)} disabled={disabled} style={{
        height: 38, padding: "0 12px", fontSize: 14, fontFamily: "inherit",
        background: disabled ? "var(--bg-secondary)" : "var(--surface)",
        border: "1px solid var(--border)", borderRadius: 10,
        color: disabled ? "var(--text-tertiary)" : "var(--text-primary)",
        outline: "none", cursor: disabled ? "not-allowed" : "pointer", boxShadow: "var(--shadow-sm)",
        opacity: disabled ? 0.7 : 1,
      }}>
        {placeholder && <option value="">{placeholder}</option>}
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ── Spinner ──────────────────────────────────────────────────────────────────
export function Spinner({ size = 20, color = "var(--accent)" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      style={{ animation: "spin 0.7s linear infinite", display: "block", flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" opacity="0.2"/>
      <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round"/>
    </svg>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────
export function Skeleton({ width, height = 20, radius = 6, style = {} }: {
  width?: number | string; height?: number; radius?: number; style?: React.CSSProperties;
}) {
  return <div className="skeleton" style={{ width: width ?? "100%", height, borderRadius: radius, ...style }}/>;
}

// ── Avatar ───────────────────────────────────────────────────────────────────
const PAL = [
  { bg: "var(--info-bg)",        text: "var(--info-text)"    },
  { bg: "var(--success-bg)",     text: "var(--success-text)" },
  { bg: "var(--warning-bg)",     text: "var(--warning-text)" },
  { bg: "var(--danger-bg)",      text: "var(--danger-text)"  },
  { bg: "var(--accent-muted)",   text: "var(--accent)"       },
  { bg: "var(--surface-sunken)", text: "var(--text-secondary)"},
];
function hashIdx(s: string) { return [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % PAL.length, 0); }
export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  const p = PAL[hashIdx(name)];
  const ini = name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: 999,
      background: p.bg, color: p.text,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.35, fontWeight: 700, flexShrink: 0,
      border: "2px solid var(--border)",
    }}>{ini}</div>
  );
}

// ── Modal ────────────────────────────────────────────────────────────────────
// FINAL-L5-05AC: canonical shared dialog -- every Admin dialog in the app
// renders through this one component, so focus trap / restoration / ARIA
// semantics fixed here apply everywhere at once rather than per-page.
let modalTitleSeq = 0;
export function Modal({ open, onClose, title, children, size = "md" }: {
  open: boolean; onClose: () => void; title?: string;
  children: React.ReactNode; size?: "sm" | "md" | "lg" | "xl";
}) {
  const dialogRef = React.useRef<HTMLDivElement>(null);
  const previouslyFocused = React.useRef<HTMLElement | null>(null);
  const titleId = React.useRef(`modal-title-${++modalTitleSeq}`).current;

  // Escape closes; Tab/Shift+Tab is trapped within the dialog's focusable
  // elements (rule 7/8: dialogs must trap focus and restore it on close).
  React.useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open, onClose]);

  // On open: remember the trigger, move focus into the dialog. On close:
  // restore focus to the trigger so keyboard users never lose their place.
  React.useEffect(() => {
    if (open) {
      previouslyFocused.current = document.activeElement as HTMLElement | null;
      const t = setTimeout(() => {
        const focusable = dialogRef.current?.querySelector<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        (focusable ?? dialogRef.current)?.focus();
      }, 0);
      return () => clearTimeout(t);
    }
    previouslyFocused.current?.focus?.();
    previouslyFocused.current = null;
  }, [open]);

  if (!open) return null;
  const W = { sm: 400, md: 560, lg: 720, xl: 900 };
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 300,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
      animation: "fadeIn 0.15s ease",
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        style={{
          width: "100%", maxWidth: W[size], maxHeight: "90vh", overflow: "auto",
          background: "var(--surface-elevated)", borderRadius: "var(--radius-xl, 1rem)",
          boxShadow: "var(--shadow-lg)", border: "1px solid var(--border)",
          animation: "slideUp 0.2s cubic-bezier(0.34,1.56,0.64,1)",
        }}>
        {title && (
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "18px 24px", borderBottom: "1px solid var(--border)",
          }}>
            <h2 id={titleId} style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{title}</h2>
            <button onClick={onClose} aria-label="Close dialog" style={{
              background: "none", border: "none", cursor: "pointer", padding: 6,
              color: "var(--text-tertiary)", borderRadius: 8,
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "background 0.12s, color 0.12s",
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = "var(--surface-sunken)"; (e.currentTarget as HTMLButtonElement).style.color = "var(--text-primary)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "none"; (e.currentTarget as HTMLButtonElement).style.color = "var(--text-tertiary)"; }}>
              <X size={16}/>
            </button>
          </div>
        )}
        <div style={{ padding: 24 }}>{children}</div>
      </div>
    </div>
  );
}

// ── Toast ────────────────────────────────────────────────────────────────────
export interface ToastItem { id: string; title: string; description?: string; variant: "success" | "warning" | "danger" | "info"; }
const TOAST_CONFIG = {
  success: { icon: <CheckCircle2 size={16}/>, border: "var(--success)",  bg: "var(--success-bg)",  color: "var(--success-text)"  },
  warning: { icon: <AlertTriangle size={16}/>, border: "var(--warning)", bg: "var(--warning-bg)",  color: "var(--warning-text)"  },
  danger:  { icon: <XCircle size={16}/>,       border: "var(--danger)",  bg: "var(--danger-bg)",   color: "var(--danger-text)"   },
  info:    { icon: <Info size={16}/>,           border: "var(--info)",    bg: "var(--info-bg)",     color: "var(--info-text)"     },
};
export function Toaster({ toasts, onRemove }: { toasts: ToastItem[]; onRemove: (id: string) => void }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="false"
      style={{ position: "fixed", bottom: 24, right: 24, zIndex: 400, display: "flex", flexDirection: "column", gap: 10, maxWidth: 360 }}
    >
      {toasts.map(t => {
        const c = TOAST_CONFIG[t.variant];
        return (
          <div key={t.id} style={{
            display: "flex", alignItems: "flex-start", gap: 12, padding: "14px 18px",
            borderRadius: 12, boxShadow: "var(--shadow-lg)", border: "1px solid var(--border)",
            borderLeft: `3px solid ${c.border}`, background: c.bg,
            animation: "slideUp 0.2s ease",
          }}>
            <span style={{ color: c.color, display: "flex", alignItems: "center", flexShrink: 0, marginTop: 1 }}>{c.icon}</span>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{t.title}</p>
              {t.description && <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "3px 0 0" }}>{t.description}</p>}
            </div>
            <button onClick={() => onRemove(t.id)} aria-label="Dismiss notification" style={{
              background: "none", border: "none", cursor: "pointer",
              color: "var(--text-tertiary)", padding: 0, display: "flex", alignItems: "center",
            }}><X size={14}/></button>
          </div>
        );
      })}
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
export function StatCard({ label, value, change, trend, icon, onClick, alert, accent }: {
  label: string; value: string | number; change?: string; trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode; onClick?: () => void; alert?: boolean; accent?: string;
}) {
  const [hov, setHov] = useState(false);
  const tC = trend === "up" ? "var(--success-text)" : trend === "down" ? "var(--danger-text)" : "var(--text-tertiary)";
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const iconBg = alert ? "var(--danger-border)" : accent ? `${accent}18` : "var(--accent-muted)";
  const iconColor = alert ? "var(--danger-text)" : accent ?? "var(--accent)";
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} onClick={onClick} style={{
      background: alert ? "var(--danger-bg)" : "var(--surface)",
      border: `1px solid ${alert ? "var(--danger-border)" : hov && onClick ? "var(--border-strong)" : "var(--border)"}`,
      borderRadius: "var(--radius-xl, 1rem)", padding: "18px 20px",
      boxShadow: hov && onClick ? "var(--shadow-md)" : "var(--shadow-sm)",
      display: "flex", flexDirection: "column", gap: 12,
      cursor: onClick ? "pointer" : undefined,
      transform: hov && onClick ? "translateY(-1px)" : "none",
      transition: "all 0.15s ease",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <p style={{
          fontSize: 11, fontWeight: 600,
          color: alert ? "var(--danger-text)" : "var(--text-tertiary)",
          margin: 0, textTransform: "uppercase", letterSpacing: "0.06em",
        }}>{label}</p>
        {icon && (
          <div style={{
            width: 36, height: 36, borderRadius: "var(--radius-lg)",
            background: iconBg,
            display: "flex", alignItems: "center", justifyContent: "center",
            color: iconColor, flexShrink: 0,
            border: `1px solid ${alert ? "var(--danger-border)" : accent ? `${accent}25` : "var(--border)"}`,
          }}>
            {React.isValidElement(icon)
              ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: 16 })
              : icon}
          </div>
        )}
      </div>
      <p style={{ fontSize: 28, fontWeight: 700, color: alert ? "var(--danger-text)" : "var(--text-primary)", margin: 0, lineHeight: 1, letterSpacing: "-0.02em" }}>{value}</p>
      {change && (
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <TrendIcon size={12} color={tC}/>
          <p style={{ fontSize: 12, color: tC, margin: 0 }}>{change}</p>
        </div>
      )}
    </div>
  );
}

// ── Section Header ────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, actions, icon }: {
  title: string; subtitle?: string; actions?: React.ReactNode; icon?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {icon && (
          <div style={{
            width: 40, height: 40, borderRadius: 12,
            background: "var(--accent-muted)", color: "var(--accent)",
            display: "flex", alignItems: "center", justifyContent: "center",
            border: "1px solid var(--border)", flexShrink: 0,
          }}>
            {React.isValidElement(icon)
              ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: 18 })
              : icon}
          </div>
        )}
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0, letterSpacing: "-0.02em" }}>{title}</h1>
          {subtitle && <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "4px 0 0" }}>{subtitle}</p>}
        </div>
      </div>
      {actions && <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>{actions}</div>}
    </div>
  );
}

// ── Data Table ────────────────────────────────────────────────────────────────
function DtRow<T extends Record<string, unknown>>({ row, columns, index, rowCount, onRowClick }: {
  row: T;
  columns: { key: string; label: string; width?: number; render?: (v: unknown, row: T) => React.ReactNode }[];
  index: number; rowCount: number; onRowClick?: (row: T) => void;
}) {
  const [hov, setHov] = React.useState(false);
  return (
    <tr
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={() => onRowClick?.(row)} style={{
        borderBottom: index < rowCount - 1 ? "1px solid var(--border)" : "none",
        background: hov && onRowClick ? "var(--surface-sunken)" : "transparent",
        cursor: onRowClick ? "pointer" : "default",
        transition: "background 0.1s",
      }}>
      {columns.map(c => (
        <td key={c.key} style={{ padding: "12px 16px", fontSize: 13, color: "var(--text-primary)" }}>
          {c.render ? c.render(row[c.key] as unknown, row) : (row[c.key] != null && typeof row[c.key] === "object" ? row[c.key] as React.ReactNode : String(row[c.key] ?? ""))}
        </td>
      ))}
    </tr>
  );
}

export function DataTable<T extends Record<string, unknown>>({ columns, rows, loading, emptyText = "No data found.", onRowClick }: {
  columns: { key: string; label: string; width?: number; render?: (v: unknown, row: T) => React.ReactNode }[];
  rows: T[]; loading?: boolean; emptyText?: string; onRowClick?: (row: T) => void;
}) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-xl, 1rem)", overflow: "hidden", boxShadow: "var(--shadow-sm)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
            {columns.map(c => (
              <th key={c.key} style={{
                padding: "11px 16px", textAlign: "left", fontSize: 11, fontWeight: 700,
                color: "var(--text-tertiary)", letterSpacing: "0.07em", textTransform: "uppercase",
                width: c.width ? `${c.width}px` : undefined,
              }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading
            ? [...Array(5)].map((_, i) => (
                <tr key={i}><td colSpan={columns.length} style={{ padding: "12px 16px" }}><Skeleton height={18}/></td></tr>
              ))
            : rows.length === 0
            ? (
                <tr><td colSpan={columns.length} style={{ padding: "52px 16px", textAlign: "center" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-tertiary)" }}>
                      <Info size={18}/>
                    </div>
                    <p style={{ color: "var(--text-tertiary)", fontSize: 14, margin: 0 }}>{emptyText}</p>
                  </div>
                </td></tr>
              )
            : rows.map((row, i) => (
                <DtRow key={i} row={row} columns={columns} index={i} rowCount={rows.length} onRowClick={onRowClick}/>
              ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: {
  icon?: React.ReactNode; title: string; description?: string; action?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "64px 32px", textAlign: "center", gap: 12 }}>
      {icon && (
        <div style={{
          width: 56, height: 56, borderRadius: 16,
          background: "var(--surface-sunken)", border: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "var(--text-tertiary)", marginBottom: 4,
        }}>
          {React.isValidElement(icon)
            ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: 24 })
            : icon}
        </div>
      )}
      <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{title}</h3>
      {description && <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0, maxWidth: 400 }}>{description}</p>}
      {action && <div style={{ marginTop: 12 }}>{action}</div>}
    </div>
  );
}

// ── Health Score Badge ────────────────────────────────────────────────────────
const HEALTH_COLORS: { [k: string]: { bg: string; text: string; border: string; icon: string; label: string } } = {
  platinum: { bg: "#FDF6E3", text: "#8B6914", border: "#F0D060", icon: "#C0A060", label: "Platinum" },
  gold:     { bg: "#FEF9EE", text: "#92400E", border: "#FCD34D", icon: "#F4A830", label: "Gold"     },
  silver:   { bg: "#F8FAFC", text: "#475569", border: "#CBD5E1", icon: "#94A3B8", label: "Silver"   },
  bronze:   { bg: "#FDF0E8", text: "#7C2D12", border: "#FDBA74", icon: "#CD7F32", label: "Bronze"   },
  at_risk:  { bg: "#FFFBEB", text: "#92400E", border: "#FDE68A", icon: "var(--warning)", label: "At Risk"  },
  critical: { bg: "#FEF2F2", text: "#991B1B", border: "#FECACA", icon: "#EF4444", label: "Critical" },
};
function getHealthBand(score: number): string {
  return score >= 90 ? "platinum" : score >= 75 ? "gold" : score >= 55 ? "silver" : score >= 35 ? "bronze" : score >= 15 ? "at_risk" : "critical";
}
export function HealthMeter({ score }: { score: number }) {
  const c = HEALTH_COLORS[getHealthBand(score)];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", color: c.text, textTransform: "uppercase" }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: c.icon }}/>
          {c.label}
        </span>
        <span style={{ fontSize: 14, fontWeight: 700, color: c.text }}>{score}</span>
      </div>
      <div style={{ height: 7, background: "var(--border)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.min(100, Math.max(0, score))}%`, background: c.icon, borderRadius: 999, transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)" }}/>
      </div>
    </div>
  );
}

// ── Job Status Badge — uses CSS design tokens, no hardcoded hex ───────────────
const JOB_STATUS_MAP: Record<string, { variant: string; label: string }> = {
  created:            { variant: "info",    label: "Created"            },
  pending_assignment: { variant: "warning", label: "Pending Assignment" },
  assigned:           { variant: "info",    label: "Assigned"           },
  accepted:           { variant: "success", label: "Accepted"           },
  staff_accepted:     { variant: "success", label: "Staff Accepted"     },
  en_route:           { variant: "info",    label: "En Route"           },
  staff_en_route:     { variant: "info",    label: "En Route"           },
  arrived:            { variant: "info",    label: "Arrived"            },
  staff_arrived:      { variant: "info",    label: "Arrived"            },
  in_progress:        { variant: "warning", label: "In Progress"        },
  parts_required:     { variant: "warning", label: "Parts Required"     },
  parts_sourcing:     { variant: "warning", label: "Parts Sourcing"     },
  parts_sourced:      { variant: "info",    label: "Parts Sourced"      },
  quality_check:      { variant: "info",    label: "Quality Check"      },
  checklist_pending:  { variant: "warning", label: "Checklist Pending"  },
  checklist_done:     { variant: "success", label: "Checklist Done"     },
  diagnosis_done:     { variant: "info",    label: "Diagnosis Done"     },
  awaiting_quote:     { variant: "warning", label: "Awaiting Quote"     },
  quote_sent:         { variant: "warning", label: "Quote Sent"         },
  quote_approved:     { variant: "success", label: "Quote Approved"     },
  quote_rejected:     { variant: "danger",  label: "Quote Rejected"     },
  completion_review:  { variant: "warning", label: "Completion Review"  },
  completed:          { variant: "success", label: "Completed"          },
  invoiced:           { variant: "info",    label: "Invoiced"           },
  payment_pending:    { variant: "warning", label: "Payment Pending"    },
  awaiting_payment:   { variant: "warning", label: "Awaiting Payment"   },
  paid:               { variant: "success", label: "Paid"               },
  closed:             { variant: "muted",   label: "Closed"             },
  cancelled:          { variant: "danger",  label: "Cancelled"          },
  disputed:           { variant: "danger",  label: "Disputed"           },
  refunded:           { variant: "info",    label: "Refunded"           },
  no_show:            { variant: "danger",  label: "No Show"            },
  rescheduled:        { variant: "info",    label: "Rescheduled"        },
  warranty_claim:     { variant: "warning", label: "Warranty Claim"     },
  rework_required:    { variant: "danger",  label: "Rework Required"    },
  resumed:            { variant: "info",    label: "Resumed"            },
  archived:           { variant: "muted",   label: "Archived"           },
};
const JOB_BADGE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  success: { bg: "var(--success-bg)", text: "var(--success-text)", border: "var(--success-border)" },
  warning: { bg: "var(--warning-bg)", text: "var(--warning-text)", border: "var(--warning-border)" },
  danger:  { bg: "var(--danger-bg)",  text: "var(--danger-text)",  border: "var(--danger-border)"  },
  info:    { bg: "var(--info-bg)",    text: "var(--info-text)",    border: "var(--info-border)"    },
  muted:   { bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)"   },
};
export function JobStatusBadge({ status }: { status: string }) {
  const s = JOB_STATUS_MAP[status] ?? { variant: "muted", label: status.replace(/_/g, " ") };
  const c = JOB_BADGE_COLORS[s.variant] ?? JOB_BADGE_COLORS.muted;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, borderRadius: 999,
      fontWeight: 700, fontSize: 11, padding: "3px 10px", letterSpacing: "0.03em", whiteSpace: "nowrap",
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: c.text, flexShrink: 0 }}/>
      {s.label}
    </span>
  );
}

// ── Pagination ────────────────────────────────────────────────────────────────
export function Pagination({ page, total, pageSize = 20, onPage }: {
  page: number; total: number; pageSize?: number; onPage: (p: number) => void;
}) {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
        {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </p>
      <div style={{ display: "flex", gap: 4 }}>
        <IconBtn icon={<ChevronRight style={{ transform: "scaleX(-1)" }}/>} onClick={() => onPage(page - 1)} disabled={page <= 1} size="sm" variant="default" tooltip="Previous"/>
        <span style={{ display: "flex", alignItems: "center", padding: "0 10px", fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>{page} / {pages}</span>
        <IconBtn icon={<ChevronRight/>} onClick={() => onPage(page + 1)} disabled={page >= pages} size="sm" variant="default" tooltip="Next"/>
      </div>
    </div>
  );
}
