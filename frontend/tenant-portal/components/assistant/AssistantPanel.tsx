"use client";
/**
 * Fuvay AI — the tenant assistant panel, opened from the portal header.
 *
 * Options-first by design: everything an admin has configured is shown the
 * moment it opens, and clicking an option is a deterministic backend call
 * with no LLM involved. Free text is the fallback, not the entry point.
 *
 * The panel renders whatever the backend sends. Nothing here is hardcoded —
 * groups, labels, copy, greeting and whether free text is even allowed all
 * come from the admin configuration.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, ChevronRight, ExternalLink, LifeBuoy, Loader2, Send,
  Sparkles, ThumbsDown, ThumbsUp, X,
} from "lucide-react";

import {
  assistantApi, type AssistantAnswer, type AssistantOption,
  type AssistantPanel as PanelData,
} from "../../lib/api-tenant-assistant";

type Bubble = {
  id: string;
  role: "user" | "assistant";
  text: string;
  messageId?: string;
  citations?: { slug: string; title: string }[];
  resolution?: string;
  canEscalate?: boolean;
  shouldEscalate?: boolean;
  articles?: { slug: string; title: string; summary: string | null }[];
};

const wrap: React.CSSProperties = {
  position: "fixed", top: 0, right: 0, bottom: 0, width: "min(430px, 100vw)",
  background: "var(--surface)", borderLeft: "1px solid var(--border)",
  boxShadow: "var(--shadow-xl, 0 12px 40px rgba(0,0,0,.18))",
  display: "flex", flexDirection: "column", zIndex: 1200,
};

const groupTitle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, letterSpacing: .4, textTransform: "uppercase",
  color: "var(--text-tertiary)", margin: "14px 0 7px",
};

const optionCard: React.CSSProperties = {
  width: "100%", textAlign: "left", display: "flex", alignItems: "center",
  gap: 10, padding: "10px 12px", borderRadius: "var(--radius-lg)",
  border: "1px solid var(--border)", background: "var(--surface)",
  cursor: "pointer", color: "var(--text-primary)", fontFamily: "inherit",
  marginBottom: 6,
};

function prettyTool(raw: string): { label: string; value: string }[] {
  try {
    const obj = JSON.parse(raw);
    return Object.entries(obj)
      .filter(([, v]) => v !== null && v !== undefined && !(Array.isArray(v) && !v.length))
      .map(([k, v]) => ({
        label: k.replace(/_/g, " ").replace(/^./, s => s.toUpperCase()),
        value: Array.isArray(v)
          ? v.map(item => typeof item === "object" ? JSON.stringify(item) : String(item)).join(", ")
          : typeof v === "object" ? JSON.stringify(v) : String(v),
      }));
  } catch {
    return [{ label: "Result", value: raw }];
  }
}

export function AssistantPanel({ open, onClose, path }: {
  open: boolean; onClose: () => void; path?: string;
}) {
  const router = useRouter();
  const [panel, setPanel] = useState<PanelData | null>(null);
  const [loading, setLoading] = useState(false);
  const [thread, setThread] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [escalating, setEscalating] = useState<{ subject: string; description: string } | null>(null);
  const [escalated, setEscalated] = useState<{ number: string; link: string } | null>(null);
  const [rated, setRated] = useState<Record<string, boolean>>({});
  const endRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open || panel) return;
    setLoading(true);
    assistantApi.panel(path)
      .then(setPanel)
      .catch(e => setErr(e?.message ?? "The assistant is unavailable right now."))
      .finally(() => setLoading(false));
  }, [open, panel, path]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread, escalating, escalated]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const push = useCallback((b: Omit<Bubble, "id">) => {
    setThread(t => [...t, { ...b, id: `${Date.now()}-${Math.random()}` }]);
  }, []);

  const applyAnswer = useCallback((r: AssistantAnswer) => {
    if (r.session_id) sessionRef.current = r.session_id;

    if (r.kind === "link" && r.route) {
      router.push(r.route);
      onClose();
      return;
    }
    if (r.kind === "escalate") {
      setEscalating({ subject: r.prefill?.subject ?? "", description: "" });
      return;
    }
    if (r.kind === "article_list") {
      push({ role: "assistant", text: "", articles: r.articles ?? [] });
      return;
    }
    if (r.kind === "data") {
      push({ role: "assistant", text: r.data ?? "", messageId: r.message_id,
             resolution: "answered", canEscalate: r.can_escalate });
      return;
    }
    push({
      role: "assistant", text: r.answer ?? "", messageId: r.message_id,
      citations: r.citations, resolution: r.resolution,
      canEscalate: r.can_escalate, shouldEscalate: r.should_escalate,
    });
  }, [push, router, onClose]);

  const runOption = async (o: AssistantOption) => {
    setBusy(true); setErr(null);
    push({ role: "user", text: o.label });
    try {
      applyAnswer(await assistantApi.runOption(o.id, path));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "That did not work. Try again.");
    } finally { setBusy(false); }
  };

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput(""); setBusy(true); setErr(null);
    push({ role: "user", text: q });
    try {
      applyAnswer(await assistantApi.ask(q, path));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Your question was not sent. Try again.");
    } finally { setBusy(false); }
  };

  const openArticle = async (slug: string, title: string) => {
    setBusy(true);
    push({ role: "user", text: title });
    try {
      const a = await assistantApi.article(slug);
      push({ role: "assistant", text: a.body || a.summary || a.title,
             citations: [{ slug: a.slug, title: a.title }], resolution: "answered",
             canEscalate: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "That article could not be opened.");
    } finally { setBusy(false); }
  };

  const submitEscalation = async () => {
    if (!escalating || busy) return;
    setBusy(true); setErr(null);
    try {
      const t = await assistantApi.escalate({
        session_id: sessionRef.current,
        subject: escalating.subject.trim() || "Help needed",
        description: escalating.description.trim(),
      });
      setEscalated({ number: t.ticket_number, link: t.deep_link });
      setEscalating(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "The request was not raised. Try again.");
    } finally { setBusy(false); }
  };

  const rate = async (messageId: string, helpful: boolean) => {
    setRated(r => ({ ...r, [messageId]: helpful }));
    try { await assistantApi.feedback(messageId, helpful); } catch { /* non-blocking */ }
  };

  if (!open) return null;
  const id = panel?.assistant;
  const showMenu = thread.length === 0 && !escalating && !escalated;

  return (
    <>
      <div onClick={onClose} style={{
        position: "fixed", inset: 0, background: "rgba(15,23,42,.32)", zIndex: 1199,
      }}/>
      <aside style={wrap} role="dialog" aria-label={id?.display_name ?? "Assistant"}>
        {/* header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "13px 16px",
                      borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
          {thread.length > 0 && !escalating && (
            <button onClick={() => { setThread([]); setEscalated(null); }}
              aria-label="Back to topics"
              style={{ background: "none", border: "none", cursor: "pointer",
                       color: "var(--text-secondary)", padding: 2, display: "flex" }}>
              <ArrowLeft size={16}/>
            </button>
          )}
          <span style={{ fontSize: 19 }}>{id?.avatar_emoji ?? "✨"}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
              {id?.display_name ?? "Assistant"}
            </div>
            {id?.tagline && (
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{id.tagline}</div>
            )}
          </div>
          <button onClick={onClose} aria-label="Close assistant"
            style={{ background: "none", border: "none", cursor: "pointer",
                     color: "var(--text-secondary)", padding: 2, display: "flex" }}>
            <X size={17}/>
          </button>
        </div>

        {/* body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 16px" }}>
          {loading && (
            <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
              <Loader2 size={20} className="spin" style={{ color: "var(--text-tertiary)" }}/>
            </div>
          )}

          {panel && panel.enabled === false && (
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 20 }}>
              {panel.message}
            </p>
          )}

          {showMenu && panel?.enabled && (
            <>
              {id?.greeting && (
                <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--text-secondary)",
                            margin: "14px 0 4px" }}>{id.greeting}</p>
              )}

              {panel.live_state && panel.live_state.blockers.length > 0 && (
                <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: "var(--radius-lg)",
                              background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--warning-text)" }}>
                    Needs your attention
                  </div>
                  <ul style={{ margin: "5px 0 0", paddingLeft: 16, fontSize: 12,
                               color: "var(--warning-text)", lineHeight: 1.6 }}>
                    {panel.live_state.blockers.map(b => <li key={b}>{b}</li>)}
                  </ul>
                </div>
              )}

              {!!panel.open_requests?.length && (
                <>
                  <div style={groupTitle}>Your open requests</div>
                  {panel.open_requests.map(r => (
                    <button key={r.ticket_number} style={optionCard}
                      onClick={() => { router.push("/help-support?tab=requests"); onClose(); }}>
                      <LifeBuoy size={15} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
                      <span style={{ flex: 1, minWidth: 0 }}>
                        <span style={{ display: "block", fontSize: 13, fontWeight: 600 }}>{r.subject}</span>
                        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {r.ticket_number} · {r.status.replace(/_/g, " ")}
                          {r.unread_replies > 0 && ` · ${r.unread_replies} new reply`}
                        </span>
                      </span>
                      <ChevronRight size={14} style={{ color: "var(--text-tertiary)" }}/>
                    </button>
                  ))}
                </>
              )}

              {panel.groups?.map(g => (
                <div key={g.key}>
                  <div style={groupTitle}>{g.label}</div>
                  {g.options.map(o => (
                    <button key={o.id} style={optionCard} disabled={busy}
                      onClick={() => runOption(o)}>
                      <span style={{ flex: 1, minWidth: 0 }}>
                        <span style={{ display: "block", fontSize: 13, fontWeight: 600 }}>{o.label}</span>
                        {o.description && (
                          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                            {o.description}
                          </span>
                        )}
                      </span>
                      <ChevronRight size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
                    </button>
                  ))}
                </div>
              ))}

              {!!panel.most_asked?.length && (
                <>
                  <div style={groupTitle}>Most asked</div>
                  {panel.most_asked.map(a => (
                    <button key={a.slug} style={optionCard} disabled={busy}
                      onClick={() => openArticle(a.slug, a.title)}>
                      <span style={{ flex: 1, fontSize: 13 }}>{a.title}</span>
                      <ChevronRight size={14} style={{ color: "var(--text-tertiary)" }}/>
                    </button>
                  ))}
                </>
              )}
            </>
          )}

          {/* conversation */}
          {thread.map(b => (
            <div key={b.id} style={{ marginTop: 14 }}>
              {b.role === "user" ? (
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <div style={{ maxWidth: "85%", padding: "8px 12px", borderRadius: 14,
                                background: "var(--primary)", color: "#fff", fontSize: 13 }}>
                    {b.text}
                  </div>
                </div>
              ) : (
                <div>
                  {b.articles ? (
                    b.articles.length ? b.articles.map(a => (
                      <button key={a.slug} style={optionCard} disabled={busy}
                        onClick={() => openArticle(a.slug, a.title)}>
                        <span style={{ flex: 1, minWidth: 0 }}>
                          <span style={{ display: "block", fontSize: 13, fontWeight: 600 }}>{a.title}</span>
                          {a.summary && (
                            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{a.summary}</span>
                          )}
                        </span>
                        <ChevronRight size={14} style={{ color: "var(--text-tertiary)" }}/>
                      </button>
                    )) : (
                      <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        Nothing is published on this topic yet.
                      </p>
                    )
                  ) : b.text.trim().startsWith("{") ? (
                    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
                                  overflow: "hidden" }}>
                      {prettyTool(b.text).map(row => (
                        <div key={row.label} style={{
                          display: "flex", justifyContent: "space-between", gap: 12,
                          padding: "7px 11px", fontSize: 12,
                          borderBottom: "1px solid var(--border)",
                        }}>
                          <span style={{ color: "var(--text-tertiary)" }}>{row.label}</span>
                          <span style={{ fontWeight: 600, textAlign: "right" }}>{row.value}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-primary)",
                                  whiteSpace: "pre-wrap" }}>{b.text}</div>
                  )}

                  {!!b.citations?.length && (
                    <div style={{ marginTop: 7, fontSize: 11, color: "var(--text-tertiary)" }}>
                      Based on: {b.citations.map(c => c.title).join(" · ")}
                    </div>
                  )}

                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                    {b.messageId && rated[b.messageId] === undefined && (
                      <>
                        <button onClick={() => rate(b.messageId!, true)} aria-label="Helpful"
                          style={{ background: "none", border: "none", cursor: "pointer",
                                   color: "var(--text-tertiary)", display: "flex", padding: 2 }}>
                          <ThumbsUp size={13}/>
                        </button>
                        <button onClick={() => rate(b.messageId!, false)} aria-label="Not helpful"
                          style={{ background: "none", border: "none", cursor: "pointer",
                                   color: "var(--text-tertiary)", display: "flex", padding: 2 }}>
                          <ThumbsDown size={13}/>
                        </button>
                      </>
                    )}
                    {b.messageId && rated[b.messageId] !== undefined && (
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Thanks for the feedback</span>
                    )}
                    {b.canEscalate && (
                      <button
                        onClick={() => setEscalating({
                          subject: b.shouldEscalate ? "I need help from the support team" : "",
                          description: "",
                        })}
                        style={{ marginLeft: "auto", background: "none", border: "none",
                                 cursor: "pointer", fontSize: 11, fontWeight: 600,
                                 color: "var(--primary)", padding: 0 }}>
                        Raise a ticket
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* escalation form */}
          {escalating && (
            <div style={{ marginTop: 16, padding: 13, borderRadius: "var(--radius-lg)",
                          border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 9 }}>
                Raise a support request
              </div>
              <input value={escalating.subject} placeholder="Subject"
                onChange={e => setEscalating({ ...escalating, subject: e.target.value })}
                style={{ width: "100%", height: 34, padding: "0 10px", fontSize: 13, marginBottom: 8,
                         border: "1px solid var(--border)", borderRadius: "var(--radius-md)",
                         background: "var(--surface)", color: "var(--text-primary)",
                         fontFamily: "inherit" }}/>
              <textarea value={escalating.description} rows={4}
                placeholder="What do you need help with? Include what you expected and what happened."
                onChange={e => setEscalating({ ...escalating, description: e.target.value })}
                style={{ width: "100%", padding: 10, fontSize: 13, resize: "vertical",
                         border: "1px solid var(--border)", borderRadius: "var(--radius-md)",
                         background: "var(--surface)", color: "var(--text-primary)",
                         fontFamily: "inherit" }}/>
              <div style={{ display: "flex", gap: 8, marginTop: 9 }}>
                <button onClick={submitEscalation}
                  disabled={busy || escalating.description.trim().length < 10}
                  style={{ padding: "7px 13px", fontSize: 12, fontWeight: 600, borderRadius: "var(--radius-md)",
                           border: "none", background: "var(--primary)", color: "#fff",
                           cursor: busy ? "wait" : "pointer", fontFamily: "inherit" }}>
                  Send to support
                </button>
                <button onClick={() => setEscalating(null)}
                  style={{ padding: "7px 13px", fontSize: 12, borderRadius: "var(--radius-md)",
                           border: "1px solid var(--border)", background: "var(--surface)",
                           color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit" }}>
                  Cancel
                </button>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
                Your conversation with the assistant is attached so support has the context.
              </p>
            </div>
          )}

          {escalated && (
            <div style={{ marginTop: 16, padding: 13, borderRadius: "var(--radius-lg)",
                          background: "var(--success-bg)", border: "1px solid var(--success-border)" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--success-text)" }}>
                Request {escalated.number} raised
              </div>
              <p style={{ fontSize: 12, color: "var(--success-text)", margin: "5px 0 9px", lineHeight: 1.5 }}>
                The ServiceOS team will reply in Help &amp; Support, and you will get an
                email when they do.
              </p>
              <button onClick={() => { router.push(escalated.link); onClose(); }}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 11px",
                         fontSize: 12, fontWeight: 600, borderRadius: "var(--radius-md)",
                         border: "1px solid var(--success-border)", background: "var(--surface)",
                         color: "var(--success-text)", cursor: "pointer", fontFamily: "inherit" }}>
                Open the request <ExternalLink size={12}/>
              </button>
            </div>
          )}

          {err && (
            <p style={{ marginTop: 12, fontSize: 12, color: "var(--danger)" }}>{err}</p>
          )}
          <div ref={endRef}/>
        </div>

        {/* composer */}
        {panel?.enabled && id?.free_text_enabled && !escalating && (
          <div style={{ display: "flex", gap: 8, padding: 12, borderTop: "1px solid var(--border)",
                        flexShrink: 0 }}>
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={id.input_placeholder} disabled={busy}
              style={{ flex: 1, height: 36, padding: "0 12px", fontSize: 13,
                       border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
                       background: "var(--surface-sunken)", color: "var(--text-primary)",
                       outline: "none", fontFamily: "inherit" }}/>
            <button onClick={send} disabled={busy || !input.trim()} aria-label="Send"
              style={{ width: 36, height: 36, borderRadius: "var(--radius-lg)", border: "none",
                       background: input.trim() ? "var(--primary)" : "var(--surface-sunken)",
                       color: input.trim() ? "#fff" : "var(--text-tertiary)",
                       cursor: input.trim() ? "pointer" : "default", display: "flex",
                       alignItems: "center", justifyContent: "center" }}>
              {busy ? <Loader2 size={15} className="spin"/> : <Send size={15}/>}
            </button>
          </div>
        )}
      </aside>
    </>
  );
}

/** Header launcher — the only entry point, per the product decision. */
export function AssistantLauncher({ path }: { path?: string }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("Fuvay AI");
  const [emoji, setEmoji] = useState("✨");
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    assistantApi.panel(path)
      .then(p => {
        setAvailable(!!p.enabled);
        if (p.assistant) { setName(p.assistant.display_name); setEmoji(p.assistant.avatar_emoji); }
      })
      .catch(() => setAvailable(false));
    // Deliberately fetched once per mount: the launcher only needs identity,
    // and the panel re-fetches its full contents when it opens.
  }, [path]);

  if (available === false) return null;

  return (
    <>
      <button onClick={() => setOpen(true)} title={name} aria-label={`Open ${name}`}
        style={{ display: "flex", alignItems: "center", gap: 7, height: 36, padding: "0 12px",
                 borderRadius: 999, cursor: "pointer", fontFamily: "inherit",
                 border: "1px solid var(--primary-border, var(--border))",
                 background: "var(--primary-bg, var(--surface-sunken))",
                 color: "var(--primary-text, var(--text-primary))" }}>
        <Sparkles size={14}/>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{name}</span>
      </button>
      <AssistantPanel open={open} onClose={() => setOpen(false)} path={path}/>
    </>
  );
}
