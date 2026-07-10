"use client";

export function SummaryCard({ label, value, accent, onClick }: { label: string; value: number | string; accent?: boolean; onClick?: () => void }) {
  return (
    <div onClick={onClick} style={{
      background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12,
      padding: "16px 20px", flex: "1 1 130px", minWidth: 110,
      borderTop: accent ? "3px solid var(--accent)" : "1px solid var(--border)",
      cursor: onClick ? "pointer" : "default",
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: accent ? "var(--accent)" : "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
    </div>
  );
}

export function SummaryCardsRow({ cards }: { cards: { label: string; value: number | string; accent?: boolean; onClick?: () => void }[] }) {
  return (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
      {cards.map(c => <SummaryCard key={c.label} label={c.label} value={c.value} accent={c.accent} onClick={c.onClick} />)}
    </div>
  );
}
