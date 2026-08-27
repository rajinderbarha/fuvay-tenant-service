"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity, AlertTriangle, BarChart3, BookOpen, BrainCircuit, CheckCircle2,
  CircleDollarSign, Clock3, Database, Gauge, History, ListChecks, Play,
  RefreshCw, Search, ServerCog, Sparkles, TriangleAlert, UsersRound,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Badge, Btn, Input, Modal, Pagination, Select, SummaryCard } from "../../../components/shared/ui";
import { PageHeader } from "@serviceos/design-system";
import { useAction, useApi } from "../../../hooks/useApi";
import {
  intelligenceCmdApi, kbApi,
  type AiUsageLogItem, type DataQualityCheck, type DataQualityFailure,
  type IntelAnomaly, type IntelligenceAuditItem, type IntelligenceEventFailure,
  type IntelligenceEventSource, type IntelligenceSummary, type KnowledgeBase,
  type KBSummary, type ModelRegistryItem, type PredictionJob, type RiskScore,
} from "../../../lib/api";
import styles from "./intelligence.module.css";

type TabId = "overview" | "rag" | "events" | "risk" | "anomalies" | "models" |
  "prediction-jobs" | "data-quality" | "ai-usage" | "audit";
type IconType = React.ComponentType<{ size?: number }>;

const PAGE_SIZE = 25;
const TABS: Array<{ id: TabId; label: string; icon: IconType }> = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "rag", label: "Knowledge & RAG", icon: BookOpen },
  { id: "events", label: "Event pipeline", icon: Activity },
  { id: "risk", label: "Provider risk", icon: Gauge },
  { id: "anomalies", label: "Anomalies", icon: TriangleAlert },
  { id: "models", label: "Model registry", icon: BrainCircuit },
  { id: "prediction-jobs", label: "Automation runs", icon: Play },
  { id: "data-quality", label: "Data quality", icon: ListChecks },
  { id: "ai-usage", label: "AI usage", icon: Sparkles },
  { id: "audit", label: "Audit trail", icon: History },
];

const safeNum = (value: unknown) => Number.isFinite(Number(value)) ? Number(value) : 0;
const n = safeNum;
const number = (value: unknown) => n(value).toLocaleString("en-IN");
const fmtMs = (value: unknown) => value == null ? "No queries yet" : `${number(value)} ms`;
const money = (value: unknown) => `₹${n(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const dateTime = (value: unknown) => value ? new Date(String(value)).toLocaleString("en-IN") : "Not available";
const text = (value: unknown, fallback = "Not available") => value == null || value === "" ? fallback : String(value);
const title = (value: unknown) => text(value).replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());

function useDebounced<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const timer = setTimeout(() => setDebounced(value), delay); return () => clearTimeout(timer); }, [value, delay]);
  return debounced;
}

function Status({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const variant = ["healthy", "active", "completed", "passed", "resolved", "success", "indexed"].includes(normalized)
    ? "success" : ["critical", "failed", "error"].includes(normalized)
      ? "danger" : ["high", "warning", "open", "degraded", "investigating"].includes(normalized)
        ? "warning" : "muted";
  return <Badge size="sm" variant={variant}>{title(value)}</Badge>;
}

function Metric({ label, value, help, icon: Icon, tone = "var(--brand)" }: {
  label: string; value: React.ReactNode; help: string; icon: IconType; tone?: string;
}) {
  const semanticTone = tone.includes("danger") ? "danger" : tone.includes("warning") ? "warning" : tone.includes("success") ? "success" : tone.includes("info") ? "info" : undefined;
  return <SummaryCard label={label} value={value} sub={help} icon={<Icon />} tone={semanticTone} />;
}

function SectionHeader({ title: heading, description, actions }: { title: string; description: string; actions?: React.ReactNode }) {
  return <div className={styles.sectionHeader}><div><h2 className={styles.sectionTitle}>{heading}</h2><p className={styles.sectionDescription}>{description}</p></div>{actions && <div className={styles.sectionActions}>{actions}</div>}</div>;
}

function Panel({ title: heading, meta, children, toolbar }: { title: string; meta?: React.ReactNode; children: React.ReactNode; toolbar?: React.ReactNode }) {
  return <section className={styles.panel}><div className={styles.panelHeader}><h3 className={styles.panelTitle}>{heading}</h3>{meta && <div className={styles.panelMeta}>{meta}</div>}</div>{toolbar}{children}</section>;
}

function Empty({ title: heading, detail }: { title: string; detail: string }) {
  return <div className={styles.empty}><div><span className={styles.emptyIcon}><Database size={21} /></span><h3 className={styles.emptyTitle}>{heading}</h3><p className={styles.emptyText}>{detail}</p></div></div>;
}

function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className={styles.searchWrap}><Search className={styles.searchIcon} size={14} /><input className={styles.search} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} /></label>;
}

function Table({ headers, children, minWidth = 820 }: { headers: string[]; children: React.ReactNode; minWidth?: number }) {
  return <div className={styles.tableScroll}><TableSurface className={styles.table} style={{ minWidth }}><thead><tr>{headers.map(header => <th key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></TableSurface></div>;
}

function Pager({ page, total, onPage }: { page: number; total: number; onPage: (page: number) => void }) {
  return <div className={styles.pagination}><Pagination page={page} total={total} pageSize={PAGE_SIZE} onPage={onPage} alwaysShow /></div>;
}

export default function IntelligencePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [secondaryFilter, setSecondaryFilter] = useState("");
  const [toast, setToast] = useState("");
  const [createKB, setCreateKB] = useState(false);
  const [kbName, setKbName] = useState("");
  const [kbScope, setKbScope] = useState("platform");
  const [selectedCheck, setSelectedCheck] = useState<DataQualityCheck | null>(null);
  const debouncedQuery = useDebounced(query.trim());
  const notify = (message: string) => { setToast(message); window.setTimeout(() => setToast(""), 3500); };

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("tab") as TabId | null;
    if (requested && TABS.some(tab => tab.id === requested)) setActiveTab(requested);
  }, []);
  const selectTab = (tab: TabId) => {
    setActiveTab(tab); setPage(1); setQuery(""); setFilter(""); setSecondaryFilter(""); setSelectedCheck(null);
    const url = new URL(window.location.href); tab === "overview" ? url.searchParams.delete("tab") : url.searchParams.set("tab", tab);
    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  };

  const { data: summary, loading: summaryLoading, refetch: refreshSummary } = useApi(() => intelligenceCmdApi.getSummary(), []);
  const { data: kbSummary, refetch: refreshKBSummary } = useApi(() => activeTab === "rag" ? kbApi.getSummary() : Promise.resolve(null), [activeTab]);
  const { data: kbData, loading: kbLoading, refetch: refreshKB } = useApi(() => activeTab === "rag" ? kbApi.list({ page, page_size: PAGE_SIZE, ...(debouncedQuery && { q: debouncedQuery }), ...(filter && { status: filter }), ...(secondaryFilter && { scope_type: secondaryFilter }) }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter, secondaryFilter]);
  const { data: eventSummary } = useApi(() => activeTab === "events" ? intelligenceCmdApi.getEventSummary() : Promise.resolve(null), [activeTab]);
  const { data: eventSources } = useApi(() => activeTab === "events" ? intelligenceCmdApi.getEventSources() : Promise.resolve(null), [activeTab]);
  const { data: eventFailures, loading: eventLoading } = useApi(() => activeTab === "events" ? intelligenceCmdApi.getEventFailures({ page, page_size: PAGE_SIZE, q: debouncedQuery, engine_id: filter }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter]);
  const { data: riskSummary } = useApi(() => activeTab === "risk" ? intelligenceCmdApi.getRiskSummary() : Promise.resolve(null), [activeTab]);
  const { data: riskData, loading: riskLoading, refetch: refreshRisk } = useApi(() => activeTab === "risk" ? intelligenceCmdApi.getRiskEntities({ page, page_size: PAGE_SIZE, q: debouncedQuery, risk_level: filter }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter]);
  const { data: anomalyData, loading: anomalyLoading, refetch: refreshAnomalies } = useApi(() => activeTab === "anomalies" ? intelligenceCmdApi.getAnomalies({ page, page_size: PAGE_SIZE, q: debouncedQuery, status: filter, severity: secondaryFilter }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter, secondaryFilter]);
  const { data: modelData, loading: modelLoading, refetch: refreshModels } = useApi(() => activeTab === "models" ? intelligenceCmdApi.getModels({ page, page_size: PAGE_SIZE, q: debouncedQuery, status: filter, model_type: secondaryFilter }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter, secondaryFilter]);
  const { data: jobData, loading: jobLoading, refetch: refreshJobs } = useApi(() => activeTab === "prediction-jobs" ? intelligenceCmdApi.getPredictionJobs({ page, page_size: PAGE_SIZE, status: filter, job_type: secondaryFilter }) : Promise.resolve(null), [activeTab, page, filter, secondaryFilter]);
  const { data: dqSummary, refetch: refreshDQSummary } = useApi(() => activeTab === "data-quality" ? intelligenceCmdApi.getDQSummary() : Promise.resolve(null), [activeTab]);
  const { data: dqData, loading: dqLoading, refetch: refreshDQ } = useApi(() => activeTab === "data-quality" ? intelligenceCmdApi.getDQChecks() : Promise.resolve(null), [activeTab]);
  const { data: dqFailures, loading: dqFailureLoading, refetch: refreshDQFailures } = useApi(() => activeTab === "data-quality" && selectedCheck ? intelligenceCmdApi.getDQFailures(selectedCheck.check_key, { page, page_size: PAGE_SIZE }) : Promise.resolve(null), [activeTab, selectedCheck?.check_key, page]);
  const { data: aiSummary } = useApi(() => activeTab === "ai-usage" ? intelligenceCmdApi.getAiUsageSummary() : Promise.resolve(null), [activeTab]);
  const { data: costBreakdown } = useApi(() => activeTab === "ai-usage" ? intelligenceCmdApi.getCostBreakdown() : Promise.resolve(null), [activeTab]);
  const { data: aiData, loading: aiLoading } = useApi(() => activeTab === "ai-usage" ? intelligenceCmdApi.getAiUsageLogs({ page, page_size: PAGE_SIZE, q: debouncedQuery, status: filter, feature_key: secondaryFilter }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter, secondaryFilter]);
  const { data: auditData, loading: auditLoading } = useApi(() => activeTab === "audit" ? intelligenceCmdApi.getAuditLogs({ page, page_size: PAGE_SIZE, q: debouncedQuery, engine_id: filter, high_risk: secondaryFilter === "high" ? true : undefined }) : Promise.resolve(null), [activeTab, page, debouncedQuery, filter, secondaryFilter]);

  const { execute: runPredictions, loading: predictionRunning, error: predictionError } = useAction(async () => {
    const result = await intelligenceCmdApi.createPredictionJob({ job_type: "daily_tenant_risk" });
    refreshJobs(); refreshRisk(); refreshSummary(); notify(`Risk scoring completed for ${number(result.total_processed)} providers.`);
  });
  const { execute: runScan, loading: scanRunning, error: scanError } = useAction(async () => {
    const result = await intelligenceCmdApi.runAnomalyScan(); refreshAnomalies(); refreshSummary();
    notify(`Scan completed: ${number(result.new_anomalies)} new, ${number(result.updated)} updated.`);
  });
  const anomalyAction = useAction(async (id: string, action: "investigate" | "resolve" | "false-positive") => {
    if (action === "investigate") await intelligenceCmdApi.investigateAnomaly(id);
    else if (action === "resolve") await intelligenceCmdApi.resolveAnomaly(id);
    else await intelligenceCmdApi.markAnomalyFalsePositive(id);
    refreshAnomalies(); refreshSummary(); notify(`Anomaly marked ${action === "resolve" ? "resolved" : action === "false-positive" ? "false positive" : "under investigation"}.`);
  });
  const modelAction = useAction(async (id: string, action: "activate" | "disable" | "evaluate") => {
    if (action === "activate") await intelligenceCmdApi.activateModel(id);
    else if (action === "disable") await intelligenceCmdApi.deactivateModel(id);
    else { const result = await intelligenceCmdApi.evaluateModel(id); notify(`Evaluation complete: ${number(result.success_rate)}% success, ${number(result.avg_latency_ms)} ms average latency.`); }
    refreshModels(); if (action !== "evaluate") notify(`Model ${action === "activate" ? "activated" : "disabled"}.`);
  });
  const dqAction = useAction(async (check: DataQualityCheck) => {
    await intelligenceCmdApi.runDQCheck(check.check_key); refreshDQ(); refreshDQSummary(); refreshDQFailures(); refreshSummary(); notify(`${check.check_name} completed.`);
  });
  const kbCreateAction = useAction(async () => {
    const created = await kbApi.create({
      name: kbName.trim(),
      scope_type: kbScope,
      ...(kbScope === "vertical" && { vertical_key: "home_services" }),
      knowledge_type: "operational",
      owner_team: "platform_operations",
      rag_enabled: true,
    });
    setCreateKB(false); setKbName("");
    router.push(`/admin/intelligence/knowledge-bases/${created.id}`);
  });
  const kbStatusAction = useAction(async (id: string, action: "activate" | "disable") => {
    action === "activate" ? await kbApi.activate(id) : await kbApi.disable(id); refreshKB(); refreshKBSummary(); notify(`Knowledge base ${action}d.`);
  });

  const s = summary as IntelligenceSummary | null;
  const activeLabel = TABS.find(tab => tab.id === activeTab)?.label ?? "Overview";
  const errors = [predictionError, scanError, anomalyAction.error, modelAction.error, dqAction.error, kbCreateAction.error, kbStatusAction.error].filter(Boolean);
  const lastUpdated = s?.generated_at ? dateTime(s.generated_at) : summaryLoading ? "Loading live telemetry" : "Not yet measured";

  const toolbar = (placeholder: string, first?: React.ReactNode, second?: React.ReactNode) => <div className={styles.toolbar}><div className={styles.toolbarGroup}><SearchBox value={query} onChange={value => { setQuery(value); setPage(1); }} placeholder={placeholder} />{first}{second}</div><span className={styles.panelMeta}>25 rows per page</span></div>;
  const noRows = (loading: boolean, heading: string, detail: string) => loading ? <div className={styles.empty}><div className="skeleton" style={{ width: 280, height: 80, borderRadius: 12 }} /></div> : <Empty title={heading} detail={detail} />;

  return <AdminLayout activeNav="intelligence"><main className={styles.workspace}>
    {toast && <div className={styles.toast}><CheckCircle2 size={16} />{toast}</div>}
    {errors.length > 0 && <div className={styles.notice}><AlertTriangle size={17} /><span>{String(errors[0])}</span></div>}

    <PageHeader eyebrow="Intelligence control plane" context={activeLabel} title="Intelligence & analytics" description="Operate Home Services risk scoring, event integrity, knowledge retrieval, anomaly response and AI governance from one auditable workspace." actions={<div className={styles.headerActions}><span className={styles.freshness}><i className={styles.freshnessDot} />Live data · {lastUpdated}</span><Btn variant="secondary" size="sm" loading={predictionRunning} onClick={() => runPredictions()}><Play size={14} /> Run risk scoring</Btn><Btn variant="secondary" size="sm" loading={scanRunning} onClick={() => runScan()}><TriangleAlert size={14} /> Scan anomalies</Btn><Btn variant="ghost" size="sm" onClick={refreshSummary}><RefreshCw size={14} /> Refresh</Btn></div>} />

    <section className={styles.primaryMetrics} aria-label="Intelligence overview metrics">
      <Metric label="Providers at risk" value={number(s?.tenants_at_risk)} help="High and critical Home Services providers" icon={UsersRound} tone="var(--warning)" />
      <Metric label="Open anomalies" value={number(s?.open_anomalies)} help="Signals awaiting investigation" icon={TriangleAlert} tone="var(--danger)" />
      <Metric label="Events today" value={number(s?.events_today)} help="Events received by the analytics pipeline" icon={Activity} tone="var(--info, var(--brand))" />
      <Metric label="AI cost today" value={money(s?.ai_cost_today)} help="Tracked model usage across platform features" icon={CircleDollarSign} tone="var(--success)" />
    </section>
    <section className={styles.signalStrip} aria-label="Supporting intelligence signals">
      {[ ["Current risk scores", number(s?.predictions_computed)], ["RAG queries", number(s?.rag_queries)], ["Indexed documents", number(s?.indexed_documents)], ["Average AI latency", fmtMs(s?.avg_ai_latency_ms)], ["Failed runs", number(s?.failed_jobs)] ].map(([label, value]) => <div className={styles.signal} key={label}><span className={styles.signalLabel}>{label}</span><span className={styles.signalValue}>{value}</span></div>)}
    </section>

    <nav className={styles.tabsShell} aria-label="Intelligence sections"><div className={styles.tabs}>{TABS.map(tab => { const Icon = tab.icon; return <button className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ""}`} key={tab.id} onClick={() => selectTab(tab.id)} aria-current={activeTab === tab.id ? "page" : undefined}><Icon size={14} />{tab.label}</button>; })}</div></nav>

    {activeTab === "overview" && <div className={styles.overviewGrid}><div className={styles.stack}><SectionHeader title="System readiness" description="Health is calculated from actual event freshness, the latest scoring run, data-quality results and indexed content." /><Panel title="Engine health" meta={`${s?.engine_health?.length ?? 0} monitored systems`}><div className={styles.panelBody}><div className={styles.healthGrid}>{(s?.engine_health ?? []).map(engine => <div className={styles.healthItem} key={engine.key}><div className={styles.healthCopy}><div className={styles.healthName}>{engine.label}</div><div className={styles.healthDetail}>{engine.detail}</div></div><span className={styles.statusDot} style={{ "--dot-tone": engine.status === "healthy" ? "var(--success)" : engine.status === "degraded" ? "var(--warning)" : "var(--text-tertiary)" } as React.CSSProperties} title={engine.status} /></div>)}</div></div></Panel><Panel title="Operational snapshot"><div className={styles.panelBody}><div className={styles.summaryGrid}><div className={styles.summaryCard}><div className={styles.summaryLabel}>Active providers</div><div className={styles.summaryValue}>{number(s?.active_tenants)}</div></div><div className={styles.summaryCard}><div className={styles.summaryLabel}>Risk coverage</div><div className={styles.summaryValue}>{number(s?.predictions_computed)}</div></div><div className={styles.summaryCard}><div className={styles.summaryLabel}>Knowledge assets</div><div className={styles.summaryValue}>{number(s?.indexed_documents)}</div></div><div className={styles.summaryCard}><div className={styles.summaryLabel}>Failed runs</div><div className={styles.summaryValue}>{number(s?.failed_jobs)}</div></div></div></div></Panel></div><div className={styles.stack}><SectionHeader title="Attention queue" description="Prioritized issues derived from current platform state." /><Panel title="Actions requiring review" meta={`${(s?.action_items ?? []).length} queues`}><div className={styles.panelBody}>{(s?.action_items ?? []).length ? <div className={styles.actionList}>{s!.action_items.map(item => <button className={styles.actionItem} key={item.type} onClick={() => selectTab(item.tab as TabId)}><span className={styles.actionCount}>{number(item.count)}</span><span className={styles.actionLabel}>{item.label}</span><span>→</span></button>)}</div> : <Empty title="No urgent actions" detail="The monitored intelligence queues currently have no unresolved high-priority work." />}</div></Panel><div className={styles.notice}><ServerCog size={17} /><span>This workspace is limited to Home Services runtime signals. It does not mix Real Estate data or legacy health-score records.</span></div></div></div>}

    {activeTab === "rag" && <div className={styles.stack}><SectionHeader title="Knowledge and retrieval" description="Govern reusable operational knowledge, RAG visibility, indexing state and access scope." actions={<Btn variant="primary" size="sm" onClick={() => { kbCreateAction.clearError(); setCreateKB(true); }}>Create knowledge base</Btn>} /><div className={styles.summaryGrid}>{[["Total", n((kbSummary as KBSummary | null)?.total)], ["Active", n((kbSummary as KBSummary | null)?.active)], ["Indexed", n((kbSummary as KBSummary | null)?.by_indexing_status?.indexed)], ["Draft", n((kbSummary as KBSummary | null)?.draft)]].map(([label, value]) => <div className={styles.summaryCard} key={String(label)}><div className={styles.summaryLabel}>{label}</div><div className={styles.summaryValue}>{number(value)}</div></div>)}</div><Panel title="Knowledge base directory" meta={`${number(kbData?.pagination?.total)} records`} toolbar={toolbar("Search name, code or owner…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="active">Active</option><option value="draft">Draft</option><option value="disabled">Disabled</option><option value="archived">Archived</option></select>, <select className={styles.select} value={secondaryFilter} onChange={e => { setSecondaryFilter(e.target.value); setPage(1); }}><option value="">All scopes</option><option value="platform">Platform</option><option value="vertical">Vertical</option><option value="compliance">Compliance</option><option value="support">Support</option></select>)}>{(kbData?.items ?? []).length ? <><Table headers={["Knowledge base", "Scope", "Status", "Indexing", "Visibility", "Updated", "Actions"]}>{(kbData?.items ?? []).map((kb: KnowledgeBase) => <tr key={kb.id}><td><span className={styles.primaryCell}>{kb.name}</span><span className={`${styles.secondaryCell} ${styles.mono}`}>{kb.kb_code ?? kb.id}</span></td><td>{title(kb.scope_type)}</td><td><Status value={kb.status} /></td><td><Status value={kb.indexing_status} /></td><td>{kb.customer_visible ? "Customer" : kb.tenant_visible ? "Provider" : "Admin only"}</td><td>{dateTime(kb.updated_at)}</td><td><div className={styles.rowActions}><Btn size="xs" variant="ghost" onClick={() => router.push(`/admin/intelligence/knowledge-bases/${kb.id}`)}>Manage</Btn>{kb.status === "active" ? <Btn size="xs" variant="secondary" onClick={() => kbStatusAction.execute(kb.id, "disable")}>Disable</Btn> : <Btn size="xs" variant="secondary" onClick={() => kbStatusAction.execute(kb.id, "activate")}>Activate</Btn>}</div></td></tr>)}</Table><Pager page={page} total={n(kbData?.pagination?.total)} onPage={setPage} /></> : noRows(kbLoading, "No knowledge bases found", "Change the filters or create a governed knowledge source.")}</Panel></div>}

    {activeTab === "events" && <div className={styles.stack}><SectionHeader title="Event pipeline" description="Inspect real analytics-event ingestion, source freshness and failure signals." /><div className={styles.summaryGrid}>{[["Events today", eventSummary?.total_events_today], ["Failure signals", eventSummary?.failure_signals_today], ["Active sources", eventSummary?.active_sources_today], ["Last event", eventSummary?.last_event_at ? dateTime(eventSummary.last_event_at) : "None"]].map(([label, value]) => <div className={styles.summaryCard} key={String(label)}><div className={styles.summaryLabel}>{label}</div><div className={styles.summaryValue}>{typeof value === "number" ? number(value) : text(value)}</div></div>)}</div><Panel title="Source health" meta={`${number(eventSources?.total)} sources`}><Table headers={["Source", "Status", "Today", "Failures", "All events", "Last event"]}>{(eventSources?.items ?? []).map((source: IntelligenceEventSource) => <tr key={source.source}><td className={styles.primaryCell}>{source.source}</td><td><Status value={source.status} /></td><td className={styles.numeric}>{number(source.events_today)}</td><td className={styles.numeric}>{number(source.failure_signals)}</td><td>{number(source.total_events)}</td><td>{dateTime(source.last_event_at)}</td></tr>)}</Table></Panel><Panel title="Failure-event explorer" meta={`${number(eventFailures?.total)} records`} toolbar={toolbar("Search event, entity or tenant…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All engines</option>{(eventSources?.items ?? []).map((source: IntelligenceEventSource) => <option key={source.source} value={source.source}>{source.source}</option>)}</select>)}>{(eventFailures?.items ?? []).length ? <><Table headers={["Event", "Engine", "Entity", "Tenant", "Occurred"]}>{(eventFailures?.items ?? []).map((item: IntelligenceEventFailure) => <tr key={item.event_id}><td><span className={styles.primaryCell}>{title(item.event_type)}</span><span className={`${styles.secondaryCell} ${styles.mono}`}>{item.event_id}</span></td><td>{item.engine_id}</td><td>{item.entity_type ? `${item.entity_type} · ${item.entity_id ?? "—"}` : "System"}</td><td className={styles.mono}>{item.tenant_id ?? "—"}</td><td>{dateTime(item.occurred_at)}</td></tr>)}</Table><Pager page={page} total={n(eventFailures?.total)} onPage={setPage} /></> : noRows(eventLoading, "No failure events", "No matching failure signals were found in the analytics event stream.")}</Panel></div>}

    {activeTab === "risk" && <div className={styles.stack}><SectionHeader title="Provider risk" description="Current, deduplicated risk scores for active Home Services providers." actions={<Btn variant="primary" size="sm" loading={predictionRunning} onClick={() => runPredictions()}>Run scoring</Btn>} /><div className={styles.summaryGrid}>{["critical", "high", "medium", "low"].map(level => <div className={styles.summaryCard} key={level}><div className={styles.summaryLabel}>{level}</div><div className={styles.summaryValue}>{number(riskSummary?.[level])}</div></div>)}</div><Panel title="Provider risk directory" meta={`${number(riskData?.total)} providers`} toolbar={toolbar("Search provider name, code or ID…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All risk levels</option>{["critical", "high", "medium", "low"].map(x => <option key={x} value={x}>{title(x)}</option>)}</select>)}>{(riskData?.items ?? []).length ? <><Table headers={["Provider", "Score", "Level", "Confidence", "Top reasons", "Computed", "Action"]}>{(riskData?.items ?? []).map((item: RiskScore) => <tr key={item.id}><td><span className={styles.primaryCell}>{item.entity_label ?? item.entity_id}</span><span className={`${styles.secondaryCell} ${styles.mono}`}>{item.entity_code ?? item.entity_id}</span></td><td className={styles.numeric}>{n(item.risk_score).toFixed(1)}</td><td><Status value={item.risk_level} /></td><td>{n(item.confidence_score).toFixed(0)}%</td><td>{(item.top_reasons_json ?? []).slice(0, 2).join(" · ") || "No risk drivers"}</td><td>{dateTime(item.computed_at)}</td><td><Btn size="xs" variant="secondary" onClick={async () => { await intelligenceCmdApi.recomputeRisk(item.entity_type, item.entity_id); refreshRisk(); notify("Provider risk recomputed."); }}>Recompute</Btn></td></tr>)}</Table><Pager page={page} total={n(riskData?.total)} onPage={setPage} /></> : noRows(riskLoading, "No risk scores", "Run provider risk scoring to create current scores.")}</Panel></div>}

    {activeTab === "anomalies" && <div className={styles.stack}><SectionHeader title="Anomaly operations" description="Triage real provider, finance and AI-usage signals with an explicit investigation lifecycle." actions={<Btn variant="primary" size="sm" loading={scanRunning} onClick={() => runScan()}>Run scan</Btn>} /><Panel title="Detected anomalies" meta={`${number(anomalyData?.total)} records`} toolbar={toolbar("Search type, summary or entity…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="open">Open</option><option value="investigating">Investigating</option><option value="resolved">Resolved</option><option value="false_positive">False positive</option></select>, <select className={styles.select} value={secondaryFilter} onChange={e => { setSecondaryFilter(e.target.value); setPage(1); }}><option value="">All severities</option>{["critical", "high", "medium", "low"].map(x => <option key={x} value={x}>{title(x)}</option>)}</select>)}>{(anomalyData?.items ?? []).length ? <><Table headers={["Signal", "Severity", "Entity", "Confidence", "Status", "Detected", "Actions"]}>{(anomalyData?.items ?? []).map((item: IntelAnomaly) => <tr key={item.id}><td><span className={styles.primaryCell}>{title(item.anomaly_type)}</span><span className={styles.secondaryCell}>{item.summary}</span></td><td><Status value={item.severity} /></td><td>{item.entity_type ?? "System"}</td><td>{n(item.confidence_score).toFixed(0)}%</td><td><Status value={item.status} /></td><td>{dateTime(item.detected_at)}</td><td><div className={styles.rowActions}>{item.status === "open" && <Btn size="xs" variant="secondary" onClick={() => anomalyAction.execute(item.id, "investigate")}>Investigate</Btn>}{!["resolved", "false_positive"].includes(item.status) && <><Btn size="xs" variant="ghost" onClick={() => anomalyAction.execute(item.id, "false-positive")}>False positive</Btn><Btn size="xs" variant="primary" onClick={() => anomalyAction.execute(item.id, "resolve")}>Resolve</Btn></>}</div></td></tr>)}</Table><Pager page={page} total={n(anomalyData?.total)} onPage={setPage} /></> : noRows(anomalyLoading, "No matching anomalies", "Run a scan or change the filters to inspect historical anomaly records.")}</Panel></div>}

    {activeTab === "models" && <div className={styles.stack}><SectionHeader title="Model registry" description="Govern deployed model metadata and evaluate observed 30-day production performance." /><div className={styles.notice}><BrainCircuit size={17} /><span>Activation controls registry eligibility. Runtime traffic remains controlled by each engine's configured model routing policy.</span></div><Panel title="Registered models" meta={`${number(modelData?.total)} models`} toolbar={toolbar("Search model name or version…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="deprecated">Deprecated</option></select>, <select className={styles.select} value={secondaryFilter} onChange={e => { setSecondaryFilter(e.target.value); setPage(1); }}><option value="">All model types</option><option value="risk_scoring">Risk scoring</option><option value="anomaly_detection">Anomaly detection</option><option value="rag">RAG</option><option value="language_model">Language model</option></select>)}>{(modelData?.items ?? []).length ? <><Table headers={["Model", "Type", "Status", "Accuracy", "Latency", "Last used", "Actions"]}>{(modelData?.items ?? []).map((item: ModelRegistryItem) => <tr key={item.id}><td><span className={styles.primaryCell}>{item.name}</span><span className={styles.secondaryCell}>Version {item.version}</span></td><td>{title(item.model_type)}</td><td><Status value={item.status} /></td><td>{item.accuracy_score == null ? "Not measured" : `${n(item.accuracy_score).toFixed(1)}%`}</td><td>{item.avg_latency_ms == null ? "No calls" : `${number(item.avg_latency_ms)} ms`}</td><td>{dateTime(item.last_used_at)}</td><td><div className={styles.rowActions}><Btn size="xs" variant="ghost" onClick={() => modelAction.execute(item.id, "evaluate")}>Evaluate</Btn><Btn size="xs" variant="secondary" onClick={() => modelAction.execute(item.id, item.status === "active" ? "disable" : "activate")}>{item.status === "active" ? "Disable" : "Activate"}</Btn></div></td></tr>)}</Table><Pager page={page} total={n(modelData?.total)} onPage={setPage} /></> : noRows(modelLoading, "No registered models", "Model entries appear when a supported runtime model is registered.")}</Panel></div>}

    {activeTab === "prediction-jobs" && <div className={styles.stack}><SectionHeader title="Automation runs" description="Track provider-risk scoring executions, processed volume and failures." actions={<Btn variant="primary" size="sm" loading={predictionRunning} onClick={() => runPredictions()}>Run now</Btn>} /><Panel title="Run history" meta={`${number(jobData?.total)} runs`} toolbar={<div className={styles.toolbar}><div className={styles.toolbarGroup}><select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="running">Running</option><option value="completed">Completed</option><option value="failed">Failed</option><option value="cancelled">Cancelled</option></select><select className={styles.select} value={secondaryFilter} onChange={e => { setSecondaryFilter(e.target.value); setPage(1); }}><option value="">All run types</option><option value="daily_tenant_risk">Provider risk scoring</option></select></div><span className={styles.panelMeta}>25 rows per page</span></div>}>{(jobData?.items ?? []).length ? <><Table headers={["Run", "Status", "Processed", "Failed", "Triggered by", "Started", "Completed", "Action"]}>{(jobData?.items ?? []).map((item: PredictionJob) => <tr key={item.id}><td><span className={styles.primaryCell}>{title(item.job_type)}</span><span className={`${styles.secondaryCell} ${styles.mono}`}>{item.id}</span></td><td><Status value={item.status} /></td><td className={styles.numeric}>{number(item.total_processed)}</td><td>{number(item.total_failed)}</td><td>{title(item.triggered_by)}</td><td>{dateTime(item.started_at)}</td><td>{dateTime(item.completed_at)}</td><td>{item.status === "running" ? <Btn size="xs" variant="danger" onClick={async () => { await intelligenceCmdApi.cancelPredictionJob(item.id); refreshJobs(); notify("Run cancelled."); }}>Cancel</Btn> : item.status === "failed" ? <Btn size="xs" variant="secondary" onClick={async () => { await intelligenceCmdApi.retryPredictionJob(item.id); refreshJobs(); refreshSummary(); notify("Failed run retried."); }}>Retry</Btn> : "—"}</td></tr>)}</Table><Pager page={page} total={n(jobData?.total)} onPage={setPage} /></> : noRows(jobLoading, "No automation runs", "Run provider risk scoring to create an auditable execution record.")}</Panel></div>}

    {activeTab === "data-quality" && <div className={styles.stack}><SectionHeader title="Data quality" description="Validate Home Services provider, booking, catalog and credit-ledger integrity." /><div className={styles.summaryGrid}>{["passed", "failed", "warning", "not_run"].map(status => <div className={styles.summaryCard} key={status}><div className={styles.summaryLabel}>{title(status)}</div><div className={styles.summaryValue}>{number(dqSummary?.[status])}</div></div>)}</div><Panel title="Quality controls" meta={`${number(dqData?.total)} checks`}>{(dqData?.items ?? []).length ? <Table headers={["Check", "Severity", "Status", "Failures", "Last run", "Actions"]}>{(dqData?.items ?? []).map((item: DataQualityCheck) => <tr key={item.id}><td><span className={styles.primaryCell}>{item.check_name}</span><span className={styles.secondaryCell}>{item.description ?? "Operational integrity rule"}</span></td><td><Status value={item.severity} /></td><td><Status value={item.last_status} /></td><td className={styles.numeric}>{number(item.failure_count)}</td><td>{dateTime(item.last_run_at)}</td><td><div className={styles.rowActions}>{n(item.failure_count) > 0 && <Btn size="xs" variant="ghost" onClick={() => { setSelectedCheck(item); setPage(1); }}>View failures</Btn>}<Btn size="xs" variant="secondary" onClick={() => dqAction.execute(item)}>Run check</Btn></div></td></tr>)}</Table> : noRows(dqLoading, "No quality checks", "No active Home Services quality checks are configured.")}</Panel>{selectedCheck && <Panel title={`${selectedCheck.check_name} failures`} meta={`${number(dqFailures?.total)} records`}>{(dqFailures?.items ?? []).length ? <><Table headers={["Entity", "Label", "Reason"]}>{(dqFailures?.items ?? []).map((item: DataQualityFailure) => <tr key={`${item.entity_type}-${item.entity_id}`}><td><span className={styles.primaryCell}>{title(item.entity_type)}</span><span className={`${styles.secondaryCell} ${styles.mono}`}>{item.entity_id}</span></td><td>{item.label}</td><td>{item.reason}</td></tr>)}</Table><Pager page={page} total={n(dqFailures?.total)} onPage={setPage} /></> : noRows(dqFailureLoading, "No current failures", "This check has no failing records in the current dataset.")}</Panel>}</div>}

    {activeTab === "ai-usage" && <div className={styles.stack}><SectionHeader title="AI cost and usage" description="Monitor model calls, latency, tokens, failures and attributable cost." /><div className={styles.summaryGrid}>{[["Cost today", money(aiSummary?.total_cost_today)], ["Monthly cost", money(aiSummary?.monthly_cost)], ["Total calls", number(aiSummary?.total_queries)], ["Failed calls", number(aiSummary?.failed_calls)]].map(([label, value]) => <div className={styles.summaryCard} key={String(label)}><div className={styles.summaryLabel}>{label}</div><div className={styles.summaryValue}>{value}</div></div>)}</div>{(costBreakdown?.breakdown ?? []).length > 0 && <Panel title="Cost allocation" meta={`${number(costBreakdown?.total_features)} features`}><div className={styles.panelBody}><div className={styles.healthGrid}>{costBreakdown!.breakdown.map(item => <div className={styles.healthItem} key={item.feature}><span className={styles.healthName}>{title(item.feature)}</span><span className={styles.numeric}>{money(item.cost)}</span></div>)}</div></div></Panel>}<Panel title="Usage ledger" meta={`${number(aiData?.total)} calls`} toolbar={toolbar("Search feature, model or error code…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="success">Success</option><option value="failed">Failed</option></select>)}>{(aiData?.items ?? []).length ? <><Table headers={["Feature", "Model", "Tokens", "Cost", "Latency", "Status", "Recorded"]}>{(aiData?.items ?? []).map((item: AiUsageLogItem) => <tr key={item.id}><td><span className={styles.primaryCell}>{title(item.feature_key)}</span><span className={styles.secondaryCell}>{item.app_scope ?? "Platform"}</span></td><td>{item.model_name ?? "Unspecified"}</td><td>{number(n(item.tokens_in) + n(item.tokens_out))}</td><td className={styles.numeric}>{money(item.cost_amount)}</td><td>{item.latency_ms == null ? "—" : `${number(item.latency_ms)} ms`}</td><td><Status value={item.status} /></td><td>{dateTime(item.created_at)}</td></tr>)}</Table><Pager page={page} total={n(aiData?.total)} onPage={setPage} /></> : noRows(aiLoading, "No AI usage", "No model calls match the selected filters.")}</Panel></div>}

    {activeTab === "audit" && <div className={styles.stack}><SectionHeader title="Audit trail" description="Append-only governance history for intelligence, analytics, RAG and AI operations." /><Panel title="Intelligence audit records" meta={`${number(auditData?.total)} records`} toolbar={toolbar("Search action, actor, target or request ID…", <select className={styles.select} value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}><option value="">All engines</option><option value="intelligence">Intelligence</option><option value="analytics">Analytics</option><option value="rag">RAG</option><option value="ai_conversation">AI conversation</option><option value="data_science">Data science</option></select>, <select className={styles.select} value={secondaryFilter} onChange={e => { setSecondaryFilter(e.target.value); setPage(1); }}><option value="">All risk levels</option><option value="high">High-risk actions</option></select>)}>{(auditData?.items ?? []).length ? <><Table headers={["Time", "Actor", "Engine", "Action", "Target", "Risk", "Request"]}>{(auditData?.items ?? []).map((item: IntelligenceAuditItem) => <tr key={item.id}><td>{dateTime(item.time)}</td><td><span className={styles.primaryCell}>{item.actor_role ?? "System"}</span><span className={`${styles.secondaryCell} ${styles.mono}`}>{item.actor ?? "Automated"}</span></td><td>{title(item.engine_id)}</td><td>{title(item.action)}</td><td>{item.target ? `${item.target} · ${item.target_id ?? "—"}` : "—"}</td><td>{item.is_high_risk ? <Badge size="sm" variant="warning">High risk</Badge> : <Badge size="sm" variant="muted">Standard</Badge>}</td><td className={styles.mono}>{item.request_id ?? "—"}</td></tr>)}</Table><Pager page={page} total={n(auditData?.total)} onPage={setPage} /></> : noRows(auditLoading, "No audit records", "No intelligence operations match the selected filters.")}</Panel></div>}

    <Modal open={createKB} onClose={() => { kbCreateAction.clearError(); setCreateKB(false); }} title="Create knowledge base" size="md"><div className={styles.stack}><div className={styles.notice}><BookOpen size={17} /><span>This creates the governed container. After creation, you will continue to its workspace to add documents, articles, access rules and indexing configuration.</span></div><Input label="Name" value={kbName} onChange={setKbName} placeholder="Example: Home Services support policy" /><Select label="Scope" value={kbScope} onChange={value => { kbCreateAction.clearError(); setKbScope(value); }} options={[{ value: "platform", label: "Platform" }, { value: "vertical", label: "Home Services vertical" }, { value: "compliance", label: "Compliance" }, { value: "support", label: "Support" }]} />{kbCreateAction.error && <div className={styles.formError} role="alert"><AlertTriangle size={16} /><span>{kbCreateAction.error}</span></div>}<div className={styles.sectionActions} style={{ justifyContent: "flex-end" }}><Btn variant="secondary" onClick={() => { kbCreateAction.clearError(); setCreateKB(false); }}>Cancel</Btn><Btn variant="primary" loading={kbCreateAction.loading} disabled={kbName.trim().length < 3} onClick={() => kbCreateAction.execute()}>Create &amp; configure</Btn></div></div></Modal>
  </main></AdminLayout>;
}
