import Link from "next/link";
import React from "react";

export interface LegalSection {
  heading: string;
  paragraphs: string[];
}

export function LegalDocument({ title, updated, intro, sections }: {
  title: string;
  updated: string;
  intro: string;
  sections: LegalSection[];
}) {
  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text-primary)", padding: "40px 20px" }}>
      <article style={{ maxWidth: 820, margin: "0 auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-xl)", padding: "clamp(24px, 5vw, 48px)", boxShadow: "var(--shadow-sm)" }}>
        <Link href="/register" style={{ color: "var(--brand)", textDecoration: "none", fontWeight: 600, fontSize: 14 }}>← Back to signup</Link>
        <h1 style={{ fontSize: 34, margin: "24px 0 8px" }}>{title}</h1>
        <p style={{ color: "var(--text-secondary)", margin: "0 0 8px" }}>{intro}</p>
        <p style={{ color: "var(--text-tertiary)", fontSize: 13, margin: "0 0 32px" }}>Last updated: {updated}</p>
        {sections.map(section => (
          <section key={section.heading} style={{ marginTop: 28 }}>
            <h2 style={{ fontSize: 20, margin: "0 0 10px" }}>{section.heading}</h2>
            {section.paragraphs.map(paragraph => (
              <p key={paragraph} style={{ color: "var(--text-secondary)", lineHeight: 1.7, margin: "0 0 12px" }}>{paragraph}</p>
            ))}
          </section>
        ))}
        <p style={{ marginTop: 36, color: "var(--text-secondary)" }}>
          Questions? Contact <a href="mailto:support@serviceos.in" style={{ color: "var(--brand)" }}>support@serviceos.in</a>.
        </p>
      </article>
    </main>
  );
}
