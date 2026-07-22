import React from "react";

export interface AvatarProps {
  src?: string | null;
  name: string;
  size?: number;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

export function Avatar({ src, name, size = 40 }: AvatarProps) {
  const style: React.CSSProperties = {
    width: size,
    height: size,
    borderRadius: "var(--radius-full)",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: size * 0.38,
    color: "var(--brand)",
    background: "var(--accent-muted)",
    overflow: "hidden",
  };
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt={name} style={{ ...style, objectFit: "cover" }} />
    );
  }
  return <div style={style}>{initials(name)}</div>;
}

export interface AvatarListRowProps {
  avatarSrc?: string | null;
  name: string;
  subtitle?: string;
  trailing?: React.ReactNode;
  onClick?: () => void;
}

export function AvatarListRow({ avatarSrc, name, subtitle, trailing, onClick }: AvatarListRowProps) {
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "0.625rem 0",
        cursor: onClick ? "pointer" : undefined,
      }}
    >
      <Avatar src={avatarSrc} name={name} size={36} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="ds-text-body-compact" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
          {name}
        </div>
        {subtitle && (
          <div className="ds-text-helper" style={{ color: "var(--text-tertiary)" }}>
            {subtitle}
          </div>
        )}
      </div>
      {trailing}
    </div>
  );
}
