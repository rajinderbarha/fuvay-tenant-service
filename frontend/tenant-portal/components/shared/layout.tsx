/**
 * Sprint 34A — UI Simplification Foundation
 * Shared layout primitives for the super-admin portal.
 *
 * Import from this file for structural components.
 * Import from shared/ui for atomic UI elements (Btn, Badge, Modal, etc.)
 */
"use client";
import React, { useState, useEffect, useRef } from "react";

// ── Design-token shorthand ────────────────────────────────────────────────────
const T = {
  surface:   "var(--surface)",
  sunken:    "var(--surface-sunken)",
  elevated:  "var(--surface-elevated)",
  border:    "var(--border)",
  borderStr: "var(--border-strong)",
  textPri:   "var(--text-primary)",
  textSec:   "var(--text-secondary)",
  textTer:   "var(--text-tertiary)",
  textLink:  "var(--text-link)",
  brand:     "var(--brand)",
  accent:    "var(--accent)",
  danger:    "var(--danger)",
  dangerBg:  "var(--danger-bg)",
  dangerBdr: "var(--danger-border)",
  dangerTxt: "var(--danger-text)",
  successBg: "var(--success-bg)",
  successBdr:"var(--success-border)",
  successTxt:"var(--success-text)",
  warningBg: "var(--warning-bg)",
  warningBdr:"var(--warning-border)",
  warningTxt:"var(--warning-text)",
  infoBg:    "var(--info-bg)",
  infoBdr:   "var(--info-border)",
  infoTxt:   "var(--info-text)",
  shadow:    "var(--shadow)",
  shadowSm:  "var(--shadow-sm)",
  shadowMd:  "var(--shadow-md)",
};

// ── Types ─────────────────────────────────────────────────────────────────────
export interface ActionMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: "default" | "danger";
  disabled?: boolean;
  divider?: boolean;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterDef {
  key: string;
  label: string;
  type: "select" | "text" | "date";
  options?: FilterOption[];
  placeholder?: string;
}

// ── PageShell ─────────────────────────────────────────────────────────────────
/**
 * Top-level page container. Provides consistent max-width, padding, and
 * vertical gap between sections. Wrap entire page content in this.
 */
export function PageShell({
  children,
  maxWidth = 1200,
  gap = 24,
  style,
}: {
  children: React.ReactNode;
  maxWidth?: number;
  gap?: number;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap,
      maxWidth,
      width: "100%",
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── PageHeader ────────────────────────────────────────────────────────────────
/**
 * Standard page header: breadcrumb (optional) + title + description +
 * primary action + secondary actions in ActionMenu.
 *
 * Replaces ad-hoc header divs and SectionHeader usage.
 */
export function PageHeader({
  title,
  description,
  breadcrumbs,
  primaryAction,
  secondaryActions,
  statusBadge,
  style,
}: {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  primaryAction?: React.ReactNode;
  secondaryActions?: ActionMenuItem[];
  statusBadge?: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, ...style }}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {breadcrumbs.map((b, i) => (
            <React.Fragment key={i}>
              {i > 0 && (
                <span style={{ fontSize: 12, color: T.textTer }}>›</span>
              )}
              {b.href ? (
                <a href={b.href} style={{
                  fontSize: 12, color: T.textLink, textDecoration: "none",
                  fontWeight: 500,
                }}>{b.label}</a>
              ) : (
                <span style={{ fontSize: 12, color: T.textTer }}>{b.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}
      <div style={{
        display: "flex", alignItems: "flex-start", justifyContent: "space-between",
        gap: 16, flexWrap: "wrap",
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1 style={{
              fontSize: 22, fontWeight: 700, color: T.textPri, margin: 0,
              lineHeight: 1.2,
            }}>{title}</h1>
            {statusBadge}
          </div>
          {description && (
            <p style={{
              fontSize: 13, color: T.textSec, margin: "4px 0 0",
              lineHeight: 1.5, maxWidth: 640,
            }}>{description}</p>
          )}
        </div>
        {(primaryAction || (secondaryActions && secondaryActions.length > 0)) && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            {secondaryActions && secondaryActions.length > 0 && (
              <ActionMenu items={secondaryActions} />
            )}
            {primaryAction}
          </div>
        )}
      </div>
    </div>
  );
}

// ── PageIntro ─────────────────────────────────────────────────────────────────
/** Descriptive paragraph below PageHeader when description alone isn't enough. */
export function PageIntro({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <p style={{
      fontSize: 13, color: T.textSec, margin: 0, lineHeight: 1.6,
      maxWidth: 680, ...style,
    }}>{children}</p>
  );
}

// ── ActionMenu ────────────────────────────────────────────────────────────────
/**
 * Kebab/overflow dropdown menu for secondary and advanced actions.
 * Keeps the primary action clean and reduces button clutter.
 */
export function ActionMenu({
  items,
  label = "Actions",
  icon,
  align = "right",
  size = "sm",
}: {
  items: ActionMenuItem[];
  label?: string;
  icon?: React.ReactNode;
  align?: "left" | "right";
  size?: "xs" | "sm" | "md";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const pad = size === "xs" ? "5px 10px" : size === "sm" ? "7px 14px" : "9px 18px";
  const fontSize = size === "xs" ? 11 : size === "sm" ? 13 : 14;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(p => !p)}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: pad, fontSize, fontWeight: 500,
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, cursor: "pointer", color: T.textSec,
          fontFamily: "inherit", transition: "all 0.15s",
          boxShadow: T.shadowSm,
        }}
        onMouseEnter={e => { (e.target as HTMLButtonElement).style.borderColor = T.borderStr; (e.target as HTMLButtonElement).style.color = T.textPri; }}
        onMouseLeave={e => { (e.target as HTMLButtonElement).style.borderColor = T.border; (e.target as HTMLButtonElement).style.color = T.textSec; }}
        aria-label={label}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {icon ?? <span style={{ fontSize: 16, lineHeight: 1 }}>⋯</span>}
        {label !== "Actions" || !icon ? label : null}
        {!icon && (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </button>

      {open && (
        <div role="menu" style={{
          position: "absolute",
          [align === "right" ? "right" : "left"]: 0,
          top: "calc(100% + 6px)",
          minWidth: 200, maxWidth: 280,
          background: T.elevated,
          border: `1px solid ${T.border}`,
          borderRadius: 10,
          boxShadow: T.shadowMd,
          zIndex: 100,
          overflow: "hidden",
          padding: "4px 0",
        }}>
          {items.map((item, i) => (
            <React.Fragment key={i}>
              {item.divider && i > 0 && (
                <div style={{ height: 1, background: T.border, margin: "4px 0" }} />
              )}
              <button
                role="menuitem"
                disabled={item.disabled}
                onClick={() => {
                  if (item.disabled) return;
                  setOpen(false);
                  if (item.href) window.location.href = item.href;
                  else item.onClick?.();
                }}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  width: "100%", padding: "9px 14px",
                  fontSize: 13, fontWeight: 500, textAlign: "left",
                  background: "transparent",
                  border: "none", cursor: item.disabled ? "not-allowed" : "pointer",
                  color: item.variant === "danger" ? T.dangerTxt : T.textPri,
                  opacity: item.disabled ? 0.5 : 1,
                  fontFamily: "inherit", transition: "background 0.1s",
                }}
                onMouseEnter={e => {
                  if (!item.disabled)
                    (e.currentTarget as HTMLButtonElement).style.background = T.sunken;
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                }}
              >
                {item.icon && (
                  <span style={{ opacity: 0.75, display: "flex", alignItems: "center" }}>
                    {item.icon}
                  </span>
                )}
                {item.label}
              </button>
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}

// ── AdvancedFiltersDrawer ─────────────────────────────────────────────────────
/**
 * Right-side sliding drawer for advanced filters.
 * Essential filters stay on the page; advanced filters go here.
 */
export function AdvancedFiltersDrawer({
  open,
  onClose,
  filters,
  values,
  onChange,
  onApply,
  onReset,
}: {
  open: boolean;
  onClose: () => void;
  filters: FilterDef[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onApply: () => void;
  onReset: () => void;
}) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape" && open) onClose();
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          onClick={onClose}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)",
            zIndex: 200, animation: "fadeIn 0.15s ease",
          }}
          aria-hidden="true"
        />
      )}
      {/* Drawer */}
      <div
        role="dialog"
        aria-label="Advanced Filters"
        aria-modal="true"
        style={{
          position: "fixed", top: 0, right: 0, bottom: 0,
          width: 340, maxWidth: "90vw",
          background: T.surface,
          borderLeft: `1px solid ${T.border}`,
          boxShadow: T.shadowMd,
          zIndex: 201,
          transform: open ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.22s cubic-bezier(0.4,0,0.2,1)",
          display: "flex", flexDirection: "column",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "18px 20px", borderBottom: `1px solid ${T.border}`,
        }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: T.textPri }}>
            Advanced Filters
          </h2>
          <button
            onClick={onClose}
            aria-label="Close filters"
            style={{
              width: 30, height: 30, borderRadius: 8,
              border: `1px solid ${T.border}`, background: T.surface,
              cursor: "pointer", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 16, color: T.textSec,
              fontFamily: "inherit",
            }}
          >×</button>
        </div>

        {/* Filter fields */}
        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          {filters.map(f => (
            <div key={f.key} style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              <label htmlFor={`filter-${f.key}`} style={{
                fontSize: 12, fontWeight: 600, color: T.textSec,
                textTransform: "uppercase", letterSpacing: "0.05em",
              }}>{f.label}</label>
              {f.type === "select" ? (
                <select
                  id={`filter-${f.key}`}
                  value={values[f.key] ?? ""}
                  onChange={e => onChange(f.key, e.target.value)}
                  style={{
                    height: 36, padding: "0 10px", fontSize: 13,
                    border: `1px solid ${T.border}`, borderRadius: 8,
                    background: T.surface, color: T.textPri,
                    fontFamily: "inherit", cursor: "pointer", outline: "none",
                  }}
                >
                  <option value="">{f.placeholder ?? `All ${f.label}`}</option>
                  {f.options?.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              ) : f.type === "date" ? (
                <input
                  id={`filter-${f.key}`}
                  type="date"
                  value={values[f.key] ?? ""}
                  onChange={e => onChange(f.key, e.target.value)}
                  style={{
                    height: 36, padding: "0 10px", fontSize: 13,
                    border: `1px solid ${T.border}`, borderRadius: 8,
                    background: T.surface, color: T.textPri,
                    fontFamily: "inherit", outline: "none",
                  }}
                />
              ) : (
                <input
                  id={`filter-${f.key}`}
                  type="text"
                  value={values[f.key] ?? ""}
                  onChange={e => onChange(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  style={{
                    height: 36, padding: "0 10px", fontSize: 13,
                    border: `1px solid ${T.border}`, borderRadius: 8,
                    background: T.surface, color: T.textPri,
                    fontFamily: "inherit", outline: "none",
                  }}
                />
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: "14px 20px", borderTop: `1px solid ${T.border}`,
          display: "flex", gap: 10,
        }}>
          <button
            onClick={onReset}
            style={{
              flex: 1, padding: "9px 0", fontSize: 13, fontWeight: 500,
              border: `1px solid ${T.border}`, borderRadius: 8,
              background: T.surface, color: T.textSec,
              cursor: "pointer", fontFamily: "inherit",
            }}
          >Reset</button>
          <button
            onClick={() => { onApply(); onClose(); }}
            style={{
              flex: 2, padding: "9px 0", fontSize: 13, fontWeight: 600,
              border: "none", borderRadius: 8,
              background: T.brand, color: "#fff",
              cursor: "pointer", fontFamily: "inherit",
            }}
          >Apply Filters</button>
        </div>
      </div>
    </>
  );
}

// ── ListPageShell ─────────────────────────────────────────────────────────────
/**
 * Standard wrapper for list/table pages.
 * Composes: PageHeader + search bar + essential filters + content area.
 *
 * Advanced filters go into AdvancedFiltersDrawer; pass a toggle trigger as
 * part of essentialFilters or secondaryActions.
 */
export function ListPageShell({
  title,
  description,
  breadcrumbs,
  primaryAction,
  secondaryActions,
  search,
  essentialFilters,
  summary,
  children,
  style,
}: {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  primaryAction?: React.ReactNode;
  secondaryActions?: ActionMenuItem[];
  search?: React.ReactNode;
  essentialFilters?: React.ReactNode;
  summary?: React.ReactNode;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <PageShell style={style}>
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={breadcrumbs}
        primaryAction={primaryAction}
        secondaryActions={secondaryActions}
      />
      {summary && <div>{summary}</div>}
      {(search || essentialFilters) && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
        }}>
          {search}
          {essentialFilters}
        </div>
      )}
      <div>{children}</div>
    </PageShell>
  );
}

// ── SearchBar ─────────────────────────────────────────────────────────────────
/** Standardized search input with magnifier icon. */
export function SearchBar({
  value,
  onChange,
  placeholder = "Search…",
  style,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{
      position: "relative", display: "flex", alignItems: "center",
      minWidth: 220, ...style,
    }}>
      <span style={{
        position: "absolute", left: 10, color: T.textTer,
        display: "flex", alignItems: "center", pointerEvents: "none",
      }}>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M10.5 10.5l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </span>
      <input
        type="search"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        style={{
          width: "100%", height: 36, paddingLeft: 32, paddingRight: 10,
          fontSize: 13, border: `1px solid ${T.border}`, borderRadius: 8,
          background: T.surface, color: T.textPri,
          fontFamily: "inherit", outline: "none",
        }}
        onFocus={e => (e.target.style.borderColor = "var(--border-focus)")}
        onBlur={e => (e.target.style.borderColor = T.border)}
      />
    </div>
  );
}

// ── EssentialFilter ───────────────────────────────────────────────────────────
/** A single visible filter select (show 2–4 max; put extras in AdvancedFiltersDrawer). */
export function EssentialFilter({
  label,
  value,
  options,
  onChange,
  style,
}: {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (v: string) => void;
  style?: React.CSSProperties;
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      aria-label={label}
      style={{
        height: 36, padding: "0 28px 0 10px", fontSize: 13,
        border: `1px solid ${T.border}`, borderRadius: 8,
        background: T.surface, color: value ? T.textPri : T.textTer,
        cursor: "pointer", fontFamily: "inherit", outline: "none",
        appearance: "none",
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
        backgroundRepeat: "no-repeat", backgroundPosition: "right 10px center",
        ...style,
      }}
    >
      <option value="">{label}: All</option>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ── SummaryStrip ──────────────────────────────────────────────────────────────
/** Horizontal row of small stat chips (shown below PageHeader). */
export function SummaryStrip({ items }: {
  items: Array<{ label: string; value: string | number; variant?: "default" | "success" | "warning" | "danger" }>;
}) {
  const bg: Record<string, string> = {
    default: T.sunken, success: T.successBg, warning: T.warningBg, danger: T.dangerBg,
  };
  const tc: Record<string, string> = {
    default: T.textPri, success: T.successTxt, warning: T.warningTxt, danger: T.dangerTxt,
  };

  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      {items.map((it, i) => {
        const v = it.variant ?? "default";
        return (
          <div key={i} style={{
            display: "flex", alignItems: "baseline", gap: 6,
            padding: "8px 14px", borderRadius: 10,
            background: bg[v], border: `1px solid ${T.border}`,
          }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: tc[v], fontVariantNumeric: "tabular-nums" }}>
              {it.value}
            </span>
            <span style={{ fontSize: 11, color: T.textTer, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
              {it.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── FormSection ───────────────────────────────────────────────────────────────
/** Sections a form with a title, optional description, and grouped fields. */
export function FormSection({
  title,
  description,
  children,
  collapsed,
  onToggle,
  style,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  collapsed?: boolean;
  onToggle?: () => void;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{
      border: `1px solid ${T.border}`, borderRadius: 12,
      background: T.surface, overflow: "hidden", ...style,
    }}>
      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 20px",
          cursor: onToggle ? "pointer" : "default",
          borderBottom: collapsed ? "none" : `1px solid ${T.border}`,
        }}
        onClick={onToggle}
      >
        <div>
          <p style={{ fontSize: 14, fontWeight: 700, color: T.textPri, margin: 0 }}>{title}</p>
          {description && (
            <p style={{ fontSize: 12, color: T.textTer, margin: "2px 0 0" }}>{description}</p>
          )}
        </div>
        {onToggle && (
          <svg
            width="16" height="16" viewBox="0 0 16 16" fill="none"
            style={{ transform: collapsed ? "rotate(0deg)" : "rotate(180deg)", transition: "transform 0.2s", color: T.textTer }}
          >
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </div>
      {!collapsed && (
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ── DangerZone ────────────────────────────────────────────────────────────────
/** Visually separated section for destructive/dangerous actions. */
export function DangerZone({
  title = "Danger Zone",
  description,
  children,
}: {
  title?: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      border: `1px solid ${T.dangerBdr}`, borderRadius: 12,
      background: T.dangerBg, overflow: "hidden",
    }}>
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.dangerBdr}` }}>
        <p style={{ fontSize: 14, fontWeight: 700, color: T.dangerTxt, margin: 0 }}>{title}</p>
        {description && (
          <p style={{ fontSize: 12, color: T.dangerTxt, margin: "2px 0 0", opacity: 0.8 }}>{description}</p>
        )}
      </div>
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
        {children}
      </div>
    </div>
  );
}

// ── SaveChangesBar ────────────────────────────────────────────────────────────
/** Sticky bottom bar shown when a form has unsaved changes. */
export function SaveChangesBar({
  visible,
  onSave,
  onDiscard,
  loading,
  message = "You have unsaved changes.",
}: {
  visible: boolean;
  onSave: () => void;
  onDiscard: () => void;
  loading?: boolean;
  message?: string;
}) {
  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0,
      background: T.elevated, borderTop: `1px solid ${T.border}`,
      boxShadow: T.shadowMd, zIndex: 150,
      padding: "12px 24px",
      display: "flex", alignItems: "center", justifyContent: "space-between",
      gap: 12,
      transform: visible ? "translateY(0)" : "translateY(100%)",
      transition: "transform 0.2s cubic-bezier(0.4,0,0.2,1)",
    }}>
      <span style={{ fontSize: 13, color: T.textSec }}>{message}</span>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onDiscard}
          disabled={loading}
          style={{
            padding: "7px 16px", fontSize: 13, fontWeight: 500,
            border: `1px solid ${T.border}`, borderRadius: 8,
            background: T.surface, color: T.textSec,
            cursor: "pointer", fontFamily: "inherit",
          }}
        >Discard</button>
        <button
          onClick={onSave}
          disabled={loading}
          style={{
            padding: "7px 18px", fontSize: 13, fontWeight: 600,
            border: "none", borderRadius: 8,
            background: T.brand, color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
            fontFamily: "inherit",
          }}
        >{loading ? "Saving…" : "Save Changes"}</button>
      </div>
    </div>
  );
}

// ── PermissionDeniedState ─────────────────────────────────────────────────────
export function PermissionDeniedState({ resource }: { resource?: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "60px 24px", gap: 12, textAlign: "center",
    }}>
      <div style={{ fontSize: 40 }}>🔒</div>
      <p style={{ fontSize: 16, fontWeight: 700, color: T.textPri, margin: 0 }}>
        Access Restricted
      </p>
      <p style={{ fontSize: 13, color: T.textSec, margin: 0, maxWidth: 360 }}>
        You don't have permission to view{resource ? ` ${resource}` : " this page"}.
        Contact your administrator if you think this is a mistake.
      </p>
    </div>
  );
}

// ── NotFoundState ─────────────────────────────────────────────────────────────
export function NotFoundState({ resource, action }: { resource?: string; action?: React.ReactNode }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "60px 24px", gap: 12, textAlign: "center",
    }}>
      <div style={{ fontSize: 40 }}>🔍</div>
      <p style={{ fontSize: 16, fontWeight: 700, color: T.textPri, margin: 0 }}>
        {resource ?? "Item"} Not Found
      </p>
      <p style={{ fontSize: 13, color: T.textSec, margin: 0, maxWidth: 360 }}>
        This {(resource ?? "item").toLowerCase()} doesn't exist or may have been removed.
      </p>
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}

// ── ComingSoonState ───────────────────────────────────────────────────────────
export function ComingSoonState({ feature }: { feature?: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "60px 24px", gap: 12, textAlign: "center",
    }}>
      <div style={{ fontSize: 40 }}>🚧</div>
      <p style={{ fontSize: 16, fontWeight: 700, color: T.textPri, margin: 0 }}>
        {feature ?? "This feature"} is coming soon
      </p>
      <p style={{ fontSize: 13, color: T.textSec, margin: 0, maxWidth: 360 }}>
        We're building this now. Check back soon.
      </p>
    </div>
  );
}

// ── ErrorState ────────────────────────────────────────────────────────────────
/**
 * Error state that shows a safe message and optional retry.
 * request_id is displayed for admin-level debugging but never stack traces.
 */
export function ErrorState({
  title = "Something went wrong",
  message,
  requestId,
  onRetry,
}: {
  title?: string;
  message?: string;
  requestId?: string;
  onRetry?: () => void;
}) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "60px 24px", gap: 12, textAlign: "center",
    }}>
      <div style={{ fontSize: 40 }}>⚠️</div>
      <p style={{ fontSize: 16, fontWeight: 700, color: T.textPri, margin: 0 }}>{title}</p>
      {message && (
        <p style={{ fontSize: 13, color: T.textSec, margin: 0, maxWidth: 400 }}>{message}</p>
      )}
      {requestId && (
        <p style={{ fontSize: 11, color: T.textTer, margin: 0, fontFamily: "monospace" }}>
          Request ID: {requestId}
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            marginTop: 8, padding: "8px 20px", fontSize: 13, fontWeight: 600,
            border: `1px solid ${T.border}`, borderRadius: 8,
            background: T.surface, color: T.textPri,
            cursor: "pointer", fontFamily: "inherit",
          }}
        >Try Again</button>
      )}
    </div>
  );
}

// ── DetailTabs ────────────────────────────────────────────────────────────────
/**
 * Standard tab bar for detail pages (Tenant detail, User detail, etc.).
 * Keeps the active tab indicator consistent across all detail pages.
 */
export function DetailTabs({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ key: string; label: string; badge?: number }>;
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div style={{
      display: "flex", gap: 2,
      borderBottom: `1px solid ${T.border}`,
      overflowX: "auto",
    }}>
      {tabs.map(tab => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          role="tab"
          aria-selected={active === tab.key}
          style={{
            padding: "10px 16px",
            fontSize: 13, fontWeight: active === tab.key ? 700 : 500,
            color: active === tab.key ? T.brand : T.textSec,
            background: "transparent", border: "none", cursor: "pointer",
            borderBottom: `2px solid ${active === tab.key ? T.brand : "transparent"}`,
            fontFamily: "inherit", whiteSpace: "nowrap", display: "flex",
            alignItems: "center", gap: 6, transition: "color 0.15s",
            marginBottom: -1,
          }}
          onMouseEnter={e => {
            if (active !== tab.key)
              (e.currentTarget as HTMLButtonElement).style.color = T.textPri;
          }}
          onMouseLeave={e => {
            if (active !== tab.key)
              (e.currentTarget as HTMLButtonElement).style.color = T.textSec;
          }}
        >
          {tab.label}
          {tab.badge !== undefined && tab.badge > 0 && (
            <span style={{
              fontSize: 10, fontWeight: 700, padding: "1px 5px", borderRadius: 99,
              background: T.accent, color: "#fff",
            }}>{tab.badge}</span>
          )}
        </button>
      ))}
    </div>
  );
}

// ── EntityHeader ──────────────────────────────────────────────────────────────
/**
 * Header for detail pages showing avatar/icon, name, metadata, and status badge.
 * Used at the top of Tenant, User, Job, and Booking detail pages.
 */
export function EntityHeader({
  initials,
  avatarUrl,
  name,
  meta,
  statusBadge,
  actions,
  accentColor = T.brand,
}: {
  initials: string;
  avatarUrl?: string | null;
  name: string;
  meta?: React.ReactNode;
  statusBadge?: React.ReactNode;
  actions?: React.ReactNode;
  accentColor?: string;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap",
      padding: 20,
      background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14,
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: 12, flexShrink: 0,
        background: avatarUrl ? "transparent" : accentColor,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#fff", fontSize: 20, fontWeight: 700, overflow: "hidden",
      }}>
        {avatarUrl
          ? <img src={avatarUrl} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          : initials.slice(0, 2).toUpperCase()
        }
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: T.textPri, margin: 0 }}>{name}</h2>
          {statusBadge}
        </div>
        {meta && (
          <div style={{ marginTop: 4, display: "flex", gap: 12, flexWrap: "wrap" }}>
            {meta}
          </div>
        )}
      </div>
      {actions && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
          {actions}
        </div>
      )}
    </div>
  );
}

// ── MetaItem ──────────────────────────────────────────────────────────────────
/** A single key-value metadata row (used inside EntityHeader or detail panels). */
export function MetaItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <span style={{ fontSize: 12, color: T.textTer }}>
      <span style={{ fontWeight: 600 }}>{label}:</span>{" "}
      <span style={{ color: T.textSec }}>{value ?? "—"}</span>
    </span>
  );
}

// ── InfoRow ───────────────────────────────────────────────────────────────────
/** Key-value row for detail/settings panels. */
export function InfoRow({ label, value, style }: {
  label: string;
  value: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
      padding: "10px 0", borderBottom: `1px solid ${T.border}`, gap: 16, ...style,
    }}>
      <span style={{
        fontSize: 12, color: T.textTer, fontWeight: 600,
        textTransform: "uppercase", letterSpacing: "0.05em", flexShrink: 0,
      }}>{label}</span>
      <span style={{ fontSize: 13, color: T.textPri, textAlign: "right" }}>
        {value ?? "—"}
      </span>
    </div>
  );
}
