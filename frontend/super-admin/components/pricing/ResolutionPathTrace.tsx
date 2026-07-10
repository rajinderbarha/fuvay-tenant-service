"use client";

export function ResolutionPathTrace({ path, warnings }: { path?: string[]; warnings?: string[] }) {
  if (!path?.length && !warnings?.length) return null;
  return (
    <div style={{ marginTop: 12 }}>
      {!!path?.length && (
        <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
          <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Resolution Path
          </p>
          <ol style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
            {path.map((step, i) => (
              <li key={i} style={{ fontSize: 13, color: "var(--text-secondary)" }}>{step}</li>
            ))}
          </ol>
        </div>
      )}
      {!!warnings?.length && (
        <div style={{ marginTop: 8, padding: "10px 14px", borderRadius: 8, background: "var(--warning-bg, #fff8e6)",
          border: "1px solid var(--warning-border, #f0c36d)" }}>
          {warnings.map((w, i) => (
            <p key={i} style={{ margin: i === 0 ? 0 : "4px 0 0", fontSize: 12, color: "var(--warning-text, #92700a)" }}>Warning: {w}</p>
          ))}
        </div>
      )}
    </div>
  );
}
