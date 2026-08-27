import Link from "next/link";
import React from "react";

/**
 * Renders a legal document served by /v1/public/legal/*.
 *
 * This component used to take a hand-written `sections` array, which meant
 * the actual wording of the Terms and Privacy Notice lived in two page
 * components and could only change with a frontend deploy. It now renders the
 * Markdown body stored in `legal_document_versions`.
 *
 * The Markdown subset is intentionally narrow — `##` headings, paragraphs and
 * `-` bullets — matching what the authoring console tells authors to write.
 * A full Markdown parser is not pulled in for this: the text is authored by
 * the platform team, not by users, and a hand-rolled subset keeps the
 * dependency surface of a page that renders legal text at zero.
 */

export interface LegalSection {
  heading: string;
  paragraphs: string[];
}

export interface LegalDocumentProps {
  title: string;
  /** Rendered as "Last updated" — the version's effective date. */
  updated: string;
  intro?: string | null;
  /**
   * Markdown, as stored in `legal_document_versions`. This is how the Terms
   * and Privacy Notice arrive — they are versioned agreements people accept,
   * so their text must come from the API, never from this repo.
   */
  body?: string;
  /**
   * Static sections, for informational pages that are NOT versioned
   * agreements (the security-practices page). Nobody accepts these, so there
   * is no consent record to tie them to and no reason to version them. Given
   * `body`, this is ignored.
   */
  sections?: LegalSection[];
  /** Shown alongside the date so a reader can cite what they read. */
  version?: string | null;
}

type Block =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] };

function parseBlocks(markdown: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list.length) {
      blocks.push({ kind: "list", items: list });
      list = [];
    }
  };

  for (const raw of markdown.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = /^#{1,6}\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ kind: "heading", text: heading[1] });
      continue;
    }
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    if (bullet) {
      flushParagraph();
      list.push(bullet[1]);
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();
  return blocks;
}

export function LegalDocument({ title, updated, intro, body, sections, version }: LegalDocumentProps) {
  const blocks: Block[] = body !== undefined
    ? parseBlocks(body)
    : (sections ?? []).flatMap(section => [
        { kind: "heading", text: section.heading } as Block,
        ...section.paragraphs.map(text => ({ kind: "paragraph", text }) as Block),
      ]);

  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text-primary)", padding: "40px 20px" }}>
      <article style={{ maxWidth: 820, margin: "0 auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-xl)", padding: "clamp(24px, 5vw, 48px)", boxShadow: "var(--shadow-sm)" }}>
        <Link href="/register" style={{ color: "var(--brand)", textDecoration: "none", fontWeight: 600, fontSize: 14 }}>← Back to signup</Link>
        <h1 style={{ fontSize: 34, margin: "24px 0 8px" }}>{title}</h1>
        {intro ? <p style={{ color: "var(--text-secondary)", margin: "0 0 8px" }}>{intro}</p> : null}
        <p style={{ color: "var(--text-tertiary)", fontSize: 13, margin: "0 0 32px" }}>
          Last updated: {updated}{version ? ` · Version ${version}` : ""}
        </p>

        {blocks.map((block, i) => {
          if (block.kind === "heading") {
            return <h2 key={i} style={{ fontSize: 20, margin: "28px 0 10px" }}>{block.text}</h2>;
          }
          if (block.kind === "list") {
            return (
              <ul key={i} style={{ color: "var(--text-secondary)", lineHeight: 1.7, margin: "0 0 12px", paddingLeft: 22 }}>
                {block.items.map((item, j) => <li key={j} style={{ marginBottom: 6 }}>{item}</li>)}
              </ul>
            );
          }
          return <p key={i} style={{ color: "var(--text-secondary)", lineHeight: 1.7, margin: "0 0 12px" }}>{block.text}</p>;
        })}
      </article>
    </main>
  );
}

/**
 * Shown when the document cannot be loaded.
 *
 * Says so plainly instead of rendering a hardcoded copy. A second copy of the
 * Terms baked into the frontend is the exact failure this engine removed: it
 * would drift from the published version and nobody would notice.
 */
export function LegalDocumentUnavailable({ title }: { title: string }) {
  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text-primary)", padding: "40px 20px" }}>
      <article style={{ maxWidth: 820, margin: "0 auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-xl)", padding: "clamp(24px, 5vw, 48px)", boxShadow: "var(--shadow-sm)" }}>
        <Link href="/register" style={{ color: "var(--brand)", textDecoration: "none", fontWeight: 600, fontSize: 14 }}>← Back to signup</Link>
        <h1 style={{ fontSize: 34, margin: "24px 0 12px" }}>{title}</h1>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.7, margin: "0 0 12px" }}>
          This document is temporarily unavailable. Please try again shortly.
        </p>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.7 }}>
          If you need a copy now, contact{" "}
          <a href="mailto:support@serviceos.in" style={{ color: "var(--brand)" }}>support@serviceos.in</a>.
        </p>
      </article>
    </main>
  );
}
