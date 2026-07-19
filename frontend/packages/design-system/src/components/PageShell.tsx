import React from "react";

export function PageShell({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", padding: "1.5rem", maxWidth: "1400px", margin: "0 auto" }}>{children}</div>;
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
      <div>
        <h1 className="ds-text-page-title" style={{ margin: 0, color: "var(--text-primary)" }}>
          {title}
        </h1>
        {description && (
          <p className="ds-text-body" style={{ margin: "0.25rem 0 0", color: "var(--text-secondary)" }}>
            {description}
          </p>
        )}
      </div>
      {actions && <div style={{ display: "flex", gap: "0.5rem" }}>{actions}</div>}
    </div>
  );
}

export function Section({ title, children, actions }: { title?: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
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
