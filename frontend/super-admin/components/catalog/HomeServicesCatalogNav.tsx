"use client";

import Link from "next/link";
import { CATALOG_SETUP_STEPS } from "./catalog-setup-sequence";
import {
  Boxes, ChevronRight, ClipboardCheck, FolderTree, GitBranch, Layers3, Tags,
} from "lucide-react";

const ITEMS = [
  { key: "categories", label: "Categories", href: "/admin/categories", icon: Layers3 },
  { key: "groups", label: "Service Groups", href: "/admin/service-groups", icon: FolderTree },
  { key: "services", label: "Master Services", href: "/admin/master-services", icon: Boxes },
  { key: "types-brands", label: "Types & Brands", href: "/admin/types-brands", icon: Tags },
  { key: "checklists", label: "Checklists", href: "/admin/checklists", icon: ClipboardCheck },
  { key: "workspace", label: "Blueprint Setup", href: "/admin/catalog-workspace", icon: GitBranch },
] as const;

export type HomeServicesCatalogSection = typeof ITEMS[number]["key"];

export default function HomeServicesCatalogNav({ active }: { active: HomeServicesCatalogSection }) {
  const stepIndex = CATALOG_SETUP_STEPS.findIndex(step => step.key === active);
  const step = CATALOG_SETUP_STEPS[stepIndex];
  const previous = CATALOG_SETUP_STEPS[stepIndex - 1];
  const next = CATALOG_SETUP_STEPS[stepIndex + 1];
  return (
    <section aria-label="Home Services catalog workflow" style={{
      marginBottom: 20, padding: 6, border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)", background: "var(--surface-sunken)",
      boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{ padding: "10px 12px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 8 }}>
        <strong style={{ fontSize: 13 }}>Catalog setup · Step {stepIndex + 1} of {ITEMS.length}</strong>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Configure in order. Navigation does not indicate completion.</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 4 }}>
        {ITEMS.map((item, index) => {
          const Icon = item.icon;
          const selected = item.key === active;
          return (
            <div key={item.key} style={{ display: "flex", alignItems: "center", flex: 1, minWidth: 132 }}>
              <Link href={item.href} aria-current={selected ? "page" : undefined} style={{
                display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "10px 12px",
                borderRadius: "var(--radius-md)", textDecoration: "none",
                background: selected ? "var(--surface)" : "transparent",
                color: selected ? "var(--text-primary)" : "var(--text-secondary)",
                border: selected ? "1px solid var(--border-strong, var(--border))" : "1px solid transparent",
                boxShadow: selected ? "var(--shadow-sm)" : "none",
              }}>
                <span style={{
                  width: 28, height: 28, borderRadius: 8, display: "inline-flex", alignItems: "center",
                  justifyContent: "center", flexShrink: 0,
                  color: selected ? "var(--brand)" : "var(--text-tertiary)",
                  background: selected ? "var(--brand-light)" : "var(--surface)",
                  border: "1px solid var(--border)",
                }}><Icon size={14}/></span>
                <span>
                  <span style={{ display: "block", fontSize: 10, color: "var(--text-tertiary)", fontWeight: 700 }}>
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span style={{ display: "block", fontSize: 12, fontWeight: selected ? 700 : 600, whiteSpace: "nowrap" }}>
                    {item.label}
                  </span>
                </span>
              </Link>
              {index < ITEMS.length - 1 && (<ChevronRight aria-hidden size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0, margin: "0 2px" }} />)}
            </div>
          );
        })}
      </div>
      <div style={{ margin: "10px 8px 6px", padding: 14, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10 }}>
        <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 700 }}>{step.label}{step.optional ? " · Service-dependent" : ""}</p>
        <p style={{ margin: "0 0 6px", fontSize: 12, color: "var(--text-secondary)" }}>{step.prerequisite} {step.task}</p>
        <p style={{ margin: "0 0 6px", fontSize: 12 }}>Before continuing: {step.done}</p>
        <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>Example: {step.example}</p>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12, marginTop: 12, fontSize: 12 }}>
          {previous ? <Link href={previous.href}>← Back: {previous.label}</Link> : <span>Start with your catalog structure</span>}
          {next ? <Link href={next.href}>Next: {next.label} →</Link> : <span>Select a service below to configure its blueprint.</span>}
        </div>
      </div>
    </section>
  );
}
