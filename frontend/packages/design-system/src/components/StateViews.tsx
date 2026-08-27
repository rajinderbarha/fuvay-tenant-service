import React from "react";
import { Inbox, AlertOctagon, ShieldAlert } from "lucide-react";

interface StateViewProps {
  title: string;
  description?: string;
  icon?: React.ReactNode | React.ComponentType<{ size?: number }>;
  action?: React.ReactNode;
  primaryAction?: React.ReactNode;
  secondaryAction?: React.ReactNode;
}

function StateView({ title, description, icon = Inbox, action, primaryAction, secondaryAction }: StateViewProps) {
  const Icon = icon;
  const renderedIcon = React.isValidElement(Icon)
    ? React.cloneElement(Icon as React.ReactElement<{ size?: number }>, { size: 24 })
    : (typeof Icon === "function" || (typeof Icon === "object" && Icon !== null && "$$typeof" in Icon))
      ? React.createElement(Icon as React.ElementType<{ size?: number }>, { size: 24 })
      : Icon;
  const resolvedPrimaryAction = action ?? primaryAction;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "4rem 2rem", gap: "0.75rem", color: "var(--text-secondary)" }}>
      <div style={{ width: 56, height: 56, borderRadius: 16, background: "var(--surface-sunken)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-tertiary)", marginBottom: 4 }}>
        {renderedIcon}
      </div>
      <h3 className="ds-text-section-title" style={{ margin: 0, color: "var(--text-primary)", fontSize: 16, fontWeight: 600 }}>
        {title}
      </h3>
      {description && (
        <p className="ds-text-body" style={{ margin: 0, maxWidth: "28rem" }}>
          {description}
        </p>
      )}
      {(resolvedPrimaryAction || secondaryAction) && (
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
          {resolvedPrimaryAction}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}

export function EmptyState(props: StateViewProps) {
  return <StateView {...props} icon={props.icon ?? Inbox} />;
}

export function ErrorState(props: Omit<StateViewProps, "icon">) {
  return <StateView {...props} icon={AlertOctagon} />;
}

export function PermissionDeniedState(props: Omit<StateViewProps, "icon">) {
  return <StateView {...props} icon={ShieldAlert} />;
}
