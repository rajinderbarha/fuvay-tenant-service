"use client";
/**
 * Tenant AI Assistant — configuration console.
 *
 * Everything the tenant-facing assistant does is set here: whether it runs,
 * how it speaks, which tenant data it may read, how strict its grounding
 * gate is, what its opening menu contains, and when it hands over to the
 * human support queue.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, BarChart3, Bot, Check, Plus, Save, Settings2,
  Sparkles, Trash2, Wrench, X,
} from "lucide-react";

import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Badge, Btn, Card, Input, SectionHeader, Select, Skeleton, StatCard, Textarea,
} from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import {
  assistantAdminApi, type AssistantConfig, type AssistantOptionRow,
} from "../../../lib/api-assistant";

type Tab = "behaviour" | "menu" | "insights";

const row: React.CSSProperties = {
  display: "grid", gridTemplateColumns: "220px minmax(0, 1fr)",
  gap: 16, alignItems: "start", padding: "13px 0",
  borderBottom: "1px solid var(--border)",
};
const labelCol: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: "var(--text-primary)" };
const hint: React.CSSProperties = { fontSize: 11, color: "var(--text-tertiary)", marginTop: 3, lineHeight: 1.5 };

function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button type="button" onClick={() => onChange(!on)} aria-pressed={on} aria-label={label}
      style={{
        width: 40, height: 22, borderRadius: 999, position: "relative", cursor: "pointer",
        border: "1px solid var(--border)", flexShrink: 0,
        background: on ? "var(--success)" : "var(--surface-sunken)",
        transition: "background .15s",
      }}>
      <span style={{
        position: "absolute", top: 2, left: on ? 20 : 2, width: 16, height: 16,
        borderRadius: "50%", background: "#fff", transition: "left .15s",
        boxShadow: "0 1px 3px rgba(0,0,0,.25)",
      }}/>
    </button>
  );
}

export default function TenantAssistantConsole() {
  const [tab, setTab] = useState<Tab>("behaviour");
  const [draft, setDraft] = useState<AssistantConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const config = useApi(useCallback(() => assistantAdminApi.getConfig(), []));
  const caps = useApi(useCallback(() => assistantAdminApi.capabilities(), []));
  const options = useApi(useCallback(() => assistantAdminApi.listOptions(), []));
  const stats = useApi(useCallback(() => assistantAdminApi.analytics(30), []));

  useEffect(() => { if (config.data && !draft) setDraft(config.data); }, [config.data, draft]);

  const set = <K extends keyof AssistantConfig>(k: K, v: AssistantConfig[K]) => {
    setDraft(d => (d ? { ...d, [k]: v } : d));
    setSaved(false);
  };

  const save = async () => {
    if (!draft) return;
    setSaving(true); setErr(null);
    try {
      const updated = await assistantAdminApi.updateConfig(draft);
      setDraft(updated); setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "The configuration was not saved.");
    } finally { setSaving(false); }
  };

  const toggleTool = (name: string) => {
    if (!draft) return;
    const has = draft.allowed_tools.includes(name);
    set("allowed_tools", has
      ? draft.allowed_tools.filter(t => t !== name)
      : [...draft.allowed_tools, name]);
  };

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "behaviour", label: "Behaviour", icon: <Settings2 size={15}/> },
    { key: "menu",      label: "Opening menu", icon: <Sparkles size={15}/> },
    { key: "insights",  label: "Insights",     icon: <BarChart3 size={15}/> },
  ];

  return (
    <AdminLayout activeNav="tenant-assistant">
      <SectionHeader
        title="Tenant AI Assistant"
        subtitle="The in-portal support agent every provider business sees in their header."
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {saved && (
              <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12,
                             color: "var(--success-text)" }}>
                <Check size={14}/> Saved
              </span>
            )}
            <Btn onClick={save} loading={saving} disabled={!draft || saving}
                 icon={<Save size={14}/>}>Save changes</Btn>
          </div>
        }
      />

      {err && (
        <Card style={{ marginBottom: 14, borderColor: "var(--danger-border)" }}>
          <div style={{ display: "flex", gap: 9, alignItems: "center", color: "var(--danger)" }}>
            <AlertTriangle size={16}/><span style={{ fontSize: 13 }}>{err}</span>
          </div>
        </Card>
      )}

      {/* status strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: 12, marginBottom: 18 }}>
        <StatCard label="Assistant" value={draft?.is_enabled ? "Live" : "Off"}
                  icon={<Bot size={16}/>}/>
        <StatCard label="Answer rate"
                  value={stats.data?.answer_rate != null
                    ? `${Math.round(stats.data.answer_rate * 100)}%` : "—"}/>
        <StatCard label="Escalations (30d)" value={String(stats.data?.escalations ?? "—")}/>
        <StatCard label="Tools enabled"
                  value={`${draft?.allowed_tools.length ?? 0} / ${caps.data?.tools.length ?? 0}`}
                  icon={<Wrench size={16}/>}/>
      </div>

      {/* tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              display: "flex", alignItems: "center", gap: 7, padding: "8px 14px",
              fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
              borderRadius: "var(--radius-lg)",
              border: `1px solid ${tab === t.key ? "var(--primary)" : "var(--border)"}`,
              background: tab === t.key ? "var(--primary-bg, var(--surface-sunken))" : "var(--surface)",
              color: tab === t.key ? "var(--primary-text, var(--text-primary))" : "var(--text-secondary)",
            }}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {config.loading && <Skeleton />}

      {draft && tab === "behaviour" && (
        <>
          <Card>
            <div style={row}>
              <div>
                <div style={labelCol}>Assistant is live</div>
                <div style={hint}>When off, the header button disappears for every tenant.</div>
              </div>
              <Toggle on={draft.is_enabled} onChange={v => set("is_enabled", v)} label="Enabled"/>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Name and avatar</div>
                   <div style={hint}>Shown on the header button and panel.</div></div>
              <div style={{ display: "flex", gap: 9 }}>
                <div style={{ flex: 1 }}>
                  <Input value={draft.display_name} onChange={v => set("display_name", v)}/>
                </div>
                <div style={{ width: 76 }}>
                  <Input value={draft.avatar_emoji} onChange={v => set("avatar_emoji", v)}/>
                </div>
              </div>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Tagline</div></div>
              <Input value={draft.tagline ?? ""} onChange={v => set("tagline", v)}/>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Greeting</div>
                   <div style={hint}>First thing a tenant reads when the panel opens.</div></div>
              <Textarea value={draft.greeting ?? ""} rows={3}
                        onChange={v => set("greeting", v)}/>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Input placeholder</div></div>
              <Input value={draft.input_placeholder}
                     onChange={v => set("input_placeholder", v)}/>
            </div>
          </Card>

          <Card style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Grounding</div>
            <p style={{ ...hint, marginBottom: 8 }}>
              The assistant answers only from help articles and this tenant&apos;s own data.
              These settings decide how sure it must be before it answers at all.
            </p>

            <div style={row}>
              <div><div style={labelCol}>Use the language model</div>
                   <div style={hint}>Off means answers are quoted from help articles verbatim —
                     still useful, never paraphrased.</div></div>
              <Toggle on={draft.llm_enabled} onChange={v => set("llm_enabled", v)} label="LLM"/>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Confidence threshold</div>
                   <div style={hint}>Below this retrieval score the assistant refuses and offers a
                     ticket instead of guessing. Higher is stricter.</div></div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <input type="range" min={0} max={0.6} step={0.01} value={draft.retrieval_min_score}
                  onChange={e => set("retrieval_min_score", Number(e.target.value))}
                  style={{ flex: 1 }}/>
                <span style={{ fontSize: 13, fontWeight: 700, minWidth: 42 }}>
                  {draft.retrieval_min_score.toFixed(2)}
                </span>
              </div>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Passages retrieved</div></div>
              <div style={{ width: 120 }}>
                <Input type="number" value={String(draft.retrieval_top_k)}
                       onChange={v => set("retrieval_top_k", Number(v))}/>
              </div>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Temperature</div>
                   <div style={hint}>Keep low. This assistant should restate facts, not invent phrasing.</div></div>
              <div style={{ width: 120 }}>
                <Input type="number" value={String(draft.temperature)}
                       onChange={v => set("temperature", Number(v))}/>
              </div>
            </div>

            <div style={row}>
              <div><div style={labelCol}>Refusal message</div>
                   <div style={hint}>Sent when the question is outside the tenant&apos;s business.</div></div>
              <Textarea value={draft.out_of_scope_message} rows={2}
                        onChange={v => set("out_of_scope_message", v)}/>
            </div>

            <div style={row}>
              <div><div style={labelCol}>No-answer message</div>
                   <div style={hint}>Sent when nothing relevant was found.</div></div>
              <Textarea value={draft.no_answer_message} rows={2}
                        onChange={v => set("no_answer_message", v)}/>
            </div>

            <div style={row}>
              <div><div style={labelCol}>System prompt</div>
                   <div style={hint}>The rules the model must follow. Editing this changes how
                     every tenant is answered — keep the grounding rules intact.</div></div>
              <Textarea value={draft.system_prompt} rows={10}
                        onChange={v => set("system_prompt", v)}/>
            </div>
          </Card>

          <Card style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Tenant data it may read</div>
            <p style={{ ...hint, marginBottom: 10 }}>
              Every tool is read-only and scoped to the caller&apos;s own business. Anything
              unchecked is never offered to the model and is rejected if it asks.
            </p>
            <div style={{ display: "grid", gap: 8 }}>
              {caps.data?.tools.map(t => {
                const on = draft.allowed_tools.includes(t.name);
                return (
                  <button key={t.name} onClick={() => toggleTool(t.name)}
                    style={{
                      display: "flex", alignItems: "center", gap: 11, padding: "9px 12px",
                      textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                      borderRadius: "var(--radius-lg)", background: "var(--surface)",
                      border: `1px solid ${on ? "var(--success-border)" : "var(--border)"}`,
                    }}>
                    <Toggle on={on} onChange={() => toggleTool(t.name)} label={t.name}/>
                    <span style={{ minWidth: 0 }}>
                      <span style={{ display: "block", fontSize: 13, fontWeight: 600,
                                     fontFamily: "var(--font-mono, monospace)" }}>{t.name}</span>
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{t.description}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Handover to humans</div>
            <div style={row}>
              <div><div style={labelCol}>Allow raising tickets</div>
                   <div style={hint}>Creates a real support request. Replies appear on the
                     tenant&apos;s Help &amp; Support page and are emailed.</div></div>
              <Toggle on={draft.escalation_enabled}
                      onChange={v => set("escalation_enabled", v)} label="Escalation"/>
            </div>
            <div style={row}>
              <div><div style={labelCol}>Offer a ticket after</div>
                   <div style={hint}>Consecutive unanswered questions before the assistant
                     proactively offers to hand over.</div></div>
              <div style={{ width: 120 }}>
                <Input type="number" value={String(draft.auto_escalate_after_unresolved)}
                       onChange={v => set("auto_escalate_after_unresolved", Number(v))}/>
              </div>
            </div>
            <div style={row}>
              <div><div style={labelCol}>Attach the conversation</div>
                   <div style={hint}>Gives the support agent the full context the tenant already gave.</div></div>
              <Toggle on={draft.escalation_include_transcript}
                      onChange={v => set("escalation_include_transcript", v)} label="Transcript"/>
            </div>
            <div style={row}>
              <div><div style={labelCol}>Ticket category</div></div>
              <div style={{ width: 240 }}>
                <Input value={draft.escalation_category}
                       onChange={v => set("escalation_category", v)}/>
              </div>
            </div>
          </Card>

          <Card style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Panel contents</div>
            {([
              ["show_categories",      "Topic groups"],
              ["show_most_asked",      "Most-asked articles"],
              ["show_live_state",      "This business's pending items"],
              ["show_recent_requests", "Their open support requests"],
              ["show_page_context",    "Options for the page they are on"],
              ["show_announcements",   "Platform announcements"],
            ] as [keyof AssistantConfig, string][]).map(([key, label]) => (
              <div key={key} style={row}>
                <div><div style={labelCol}>{label}</div></div>
                <Toggle on={Boolean(draft[key])}
                        onChange={v => set(key, v as never)} label={label}/>
              </div>
            ))}
            <div style={row}>
              <div><div style={labelCol}>Maximum options shown</div></div>
              <div style={{ width: 120 }}>
                <Input type="number" value={String(draft.max_options_total)}
                       onChange={v => set("max_options_total", Number(v))}/>
              </div>
            </div>
            <div style={row}>
              <div><div style={labelCol}>Requests per hour, per business</div></div>
              <div style={{ width: 120 }}>
                <Input type="number" value={String(draft.rate_limit_per_hour)}
                       onChange={v => set("rate_limit_per_hour", Number(v))}/>
              </div>
            </div>
          </Card>
        </>
      )}

      {tab === "menu" && (
        <OptionsEditor
          rows={options.data?.options ?? []}
          groups={caps.data?.groups ?? []}
          tools={caps.data?.tools.map(t => t.name) ?? []}
          routes={caps.data?.portal_routes ?? []}
          areas={caps.data?.knowledge_areas ?? []}
          onChanged={() => options.refetch?.()}
        />
      )}

      {tab === "insights" && (
        <>
          <Card>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
              What tenants asked that the assistant could not answer
            </div>
            {!stats.data?.content_gaps.length ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
                Nothing unanswered in the last 30 days.
              </p>
            ) : (
              <>
                <p style={{ ...hint, marginBottom: 10 }}>
                  Each row is a help article worth writing. Publish one and the assistant
                  answers that question from then on.
                </p>
                {stats.data.content_gaps.map(g => (
                  <div key={g.question} style={{
                    display: "flex", justifyContent: "space-between", gap: 12,
                    padding: "9px 0", borderBottom: "1px solid var(--border)", fontSize: 13,
                  }}>
                    <span>{g.question}</span>
                    <Badge variant="warning">{g.times}×</Badge>
                  </div>
                ))}
              </>
            )}
          </Card>

          <Card style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Most used options</div>
            {(stats.data?.top_options ?? []).map(o => (
              <div key={o.label} style={{
                display: "flex", justifyContent: "space-between", gap: 12,
                padding: "9px 0", borderBottom: "1px solid var(--border)", fontSize: 13,
              }}>
                <span>{o.label}<span style={{ color: "var(--text-tertiary)" }}> · {o.group}</span></span>
                <span style={{ fontWeight: 700 }}>{o.clicks}</span>
              </div>
            ))}
          </Card>

          <Card style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Outcomes (30 days)</div>
            {Object.entries(stats.data?.by_resolution ?? {}).map(([k, v]) => (
              <div key={k} style={{
                display: "flex", justifyContent: "space-between",
                padding: "9px 0", borderBottom: "1px solid var(--border)", fontSize: 13,
              }}>
                <span style={{ textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</span>
                <span style={{ fontWeight: 700 }}>{v}</span>
              </div>
            ))}
          </Card>
        </>
      )}
    </AdminLayout>
  );
}

function OptionsEditor({ rows, groups, tools, routes, areas, onChanged }: {
  rows: AssistantOptionRow[];
  groups: { key: string; label: string }[];
  tools: string[];
  routes: { key: string; label: string }[];
  areas: { product_area: string; article_count: number }[];
  onChanged: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<AssistantOptionRow>>({
    group_key: groups[0]?.key ?? "getting_started",
    action_type: "prompt", display_order: 100, is_enabled: true,
  });

  const create = async () => {
    setErr(null);
    try {
      await assistantAdminApi.createOption(form);
      setAdding(false); onChanged();
      setForm({ group_key: groups[0]?.key ?? "getting_started", action_type: "prompt",
                display_order: 100, is_enabled: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "The option was not added.");
    }
  };

  const toggle = async (o: AssistantOptionRow) => {
    await assistantAdminApi.updateOption(o.id, { is_enabled: !o.is_enabled });
    onChanged();
  };

  const remove = async (o: AssistantOptionRow) => {
    await assistantAdminApi.deleteOption(o.id);
    onChanged();
  };

  const byGroup = groups
    .map(g => ({ ...g, items: rows.filter(r => r.group_key === g.key) }))
    .filter(g => g.items.length);

  const targetHelp: Record<string, string> = {
    article: "Article slug",
    topic:   `Product area — ${areas.map(a => a.product_area).join(", ") || "none published"}`,
    tool:    `Tool name — ${tools.join(", ")}`,
    prompt:  "The exact question to run through the assistant",
    link:    `Portal route key — ${routes.map(r => r.key).join(", ")}`,
    ticket:  "No target needed",
  };

  return (
    <>
      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                      marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>Opening menu</div>
            <div style={hint}>
              What every tenant sees the instant the panel opens. Clicking one of these
              never calls the language model.
            </div>
          </div>
          <Btn size="sm" icon={<Plus size={14}/>} onClick={() => setAdding(a => !a)}>
            Add option
          </Btn>
        </div>

        {err && <p style={{ fontSize: 12, color: "var(--danger)", marginBottom: 10 }}>{err}</p>}

        {adding && (
          <div style={{ padding: 13, marginBottom: 14, borderRadius: "var(--radius-lg)",
                        border: "1px solid var(--border)", background: "var(--surface-sunken)",
                        display: "grid", gap: 9 }}>
            <Input label="Label" value={form.label ?? ""}
                   onChange={v => setForm({ ...form, label: v as string })}/>
            <Input label="Description" value={form.description ?? ""}
                   onChange={v => setForm({ ...form, description: v as string })}/>
            <Select label="Group" value={form.group_key ?? ""}
                    onChange={v => setForm({ ...form, group_key: v as string })}
                    options={groups.map(g => ({ value: g.key, label: g.label }))}/>
            <Select label="Action" value={form.action_type ?? "prompt"}
                    onChange={v => setForm({ ...form, action_type: v as AssistantOptionRow["action_type"] })}
                    options={["prompt", "topic", "article", "tool", "link", "ticket"]
                      .map(t => ({ value: t, label: t }))}/>
            {form.action_type !== "ticket" && (
              <Input label={targetHelp[form.action_type ?? "prompt"]}
                     value={form.action_target ?? ""}
                     onChange={v => setForm({ ...form, action_target: v as string })}/>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              <Btn size="sm" onClick={create} disabled={!form.label}>Add</Btn>
              <Btn size="sm" variant="secondary" onClick={() => setAdding(false)}
                   icon={<X size={13}/>}>Cancel</Btn>
            </div>
          </div>
        )}

        {byGroup.map(g => (
          <div key={g.key} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                          letterSpacing: .4, color: "var(--text-tertiary)", marginBottom: 7 }}>
              {g.label}
            </div>
            {g.items.map(o => (
              <div key={o.id} style={{
                display: "flex", alignItems: "center", gap: 11, padding: "9px 11px",
                border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
                marginBottom: 6, opacity: o.is_enabled ? 1 : .55,
              }}>
                <Toggle on={o.is_enabled} onChange={() => toggle(o)} label={o.label}/>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{o.label}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {o.action_type}
                    {o.action_target ? ` → ${o.action_target}` : ""}
                    {o.click_count > 0 ? ` · ${o.click_count} clicks` : ""}
                  </div>
                </div>
                {o.is_featured && <Badge variant="info">Featured</Badge>}
                <button onClick={() => remove(o)} aria-label={`Delete ${o.label}`}
                  style={{ background: "none", border: "none", cursor: "pointer",
                           color: "var(--danger)", padding: 4, display: "flex" }}>
                  <Trash2 size={14}/>
                </button>
              </div>
            ))}
          </div>
        ))}
      </Card>
    </>
  );
}
