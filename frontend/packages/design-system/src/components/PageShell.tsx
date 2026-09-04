import React from "react";

export function PageShell({ children }: { children: React.ReactNode }) {
  // Authenticated application layouts already own the viewport padding and
  // content width. PageShell only owns vertical rhythm; adding another inset
  // here created the inconsistent, double-padded headers seen on newer pages.
  return <div className="ds-page-shell" style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)", width: "100%" }}>{children}</div>;
}

export function PageHeader({
  title,
  description,
  subtitle,
  actions,
  icon,
  eyebrow,
  context,
}: {
  title: string;
  description?: string;
  /** Backward-compatible alias used by older portal pages. */
  subtitle?: string;
  actions?: React.ReactNode;
  icon?: React.ReactNode;
  eyebrow?: string;
  context?: string;
}) {
  const supportingText = description ?? subtitle;
  const commandEyebrow = eyebrow ?? "Platform control plane";
  const hasCommandContext = Boolean(commandEyebrow || context);
  const renderedIcon = icon && React.isValidElement(icon)
    ? React.cloneElement(icon as React.ReactElement<{ size?: number }>, { size: hasCommandContext ? 13 : 18 })
    : icon;
  return (
    <header className="ds-section-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--layout-section-gap)", flexWrap: "wrap" }}>
      <div style={{ minWidth: 0, flex: "1 1 32rem" }}>
        {hasCommandContext && (
          <div style={{ display: "flex", alignItems: "center", gap: "var(--layout-control-gap)", minHeight: 14, marginBottom: "var(--space-2)" }}>
            {icon && <span style={{ display: "inline-flex", alignItems: "center", color: "var(--text-link)", flexShrink: 0 }}>{renderedIcon}</span>}
            <span style={{ color: "var(--text-link)", fontSize: 10, lineHeight: 1, fontWeight: 750, letterSpacing: "0.08em", textTransform: "uppercase" }}>{commandEyebrow}</span>
            {context && <span style={{ paddingLeft: "var(--space-2)", borderLeft: "1px solid var(--border)", color: "var(--text-tertiary)", fontSize: 10, lineHeight: 1, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>{context}</span>}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-3)", minWidth: 0 }}>
          {icon && !hasCommandContext && (
            <span style={{ width: 40, height: 40, display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0, borderRadius: "var(--radius-lg)", background: "var(--accent-muted)", color: "var(--accent)", border: "1px solid var(--border)" }}>{renderedIcon}</span>
          )}
          <div style={{ minWidth: 0 }}>
            <h1 className="ds-text-page-title" style={{ margin: 0, color: "var(--text-primary)", fontSize: "clamp(22px, 2.4vw, 28px)", lineHeight: 1.1, fontWeight: 700, letterSpacing: "-0.02em" }}>
              {title}
            </h1>
            {supportingText && (
              <p className="ds-text-body" style={{ margin: "6px 0 0", color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.45, maxWidth: 560 }}>
                {supportingText}
              </p>
            )}
          </div>
        </div>
      </div>
      {actions && <div className="ds-section-header-actions" style={{ display: "flex", gap: "var(--layout-control-gap)", alignItems: "center", flexWrap: "wrap", paddingTop: "var(--space-1)" }}>{actions}</div>}
    </header>
  );
}

export function Section({ title, children, actions }: { title?: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {(title || actions) && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {title && (
            <h2 className="ds-text-section-title" style={{ margin: 0, color: "var(--text-primary)" }}>
              {title}
            </h2>
          )}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
