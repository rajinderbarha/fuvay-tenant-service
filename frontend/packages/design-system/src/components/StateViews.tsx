import React from "react";
import { Inbox, AlertOctagon, ShieldAlert } from "lucide-react";

interface StateViewProps {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ size?: number }>;
  primaryAction?: React.ReactNode;
  secondaryAction?: React.ReactNode;
}

function StateView({ title, description, icon: Icon = Inbox, primaryAction, secondaryAction }: StateViewProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "3rem 1.5rem", gap: "0.75rem", color: "var(--text-secondary)" }}>
      <Icon size={40} />
      <h3 className="ds-text-section-title" style={{ margin: 0, color: "var(--text-primary)" }}>
        {title}
      </h3>
      {description && (
        <p className="ds-text-body" style={{ margin: 0, maxWidth: "28rem" }}>
          {description}
        </p>
      )}
      {(primaryAction || secondaryAction) && (
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
          {primaryAction}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}

export function EmptyState(props: Omit<StateViewProps, "icon">) {
  return <StateView {...props} icon={Inbox} />;
}

export function ErrorState(props: Omit<StateViewProps, "icon">) {
  return <StateView {...props} icon={AlertOctagon} />;
}

export function PermissionDeniedState(props: Omit<StateViewProps, "icon">) {
  return <StateView {...props} icon={ShieldAlert} />;
}
