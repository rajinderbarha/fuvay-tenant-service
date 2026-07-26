"use client";
import React, { useState, useCallback, useRef } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, CardHeader, SectionHeader, StatCard, Badge, Btn, Modal, DataTable,
} from "../../../components/shared/ui";
import {
  Search, RefreshCw, Image, FileText, Video, File, Trash2, AlertCircle,
  Download, Eye, Archive, Flag, Shield, CheckCircle, X, Filter, MoreVertical,
  ChevronDown, Lock, Unlock, HardDrive, Upload, Grid, List, Tag, Clock,
  Link2, FolderOpen, BarChart2, ChevronRight, ChevronLeft, Plus, Copy,
  ExternalLink, RotateCcw, ZoomIn, Layers,
} from "lucide-react";
import {
  mediaAdminApi,
  type MediaAssetAdmin, type MediaSummary, type MediaLinkedRecord, type MediaAuditLog,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

// ── Helpers ──────────────────────────────────────────────────────────────────

const fmtBytes = (b: number): string => {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`;
  return `${(b / 1073741824).toFixed(1)} GB`;
};
const fmtDate = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};
const fmtDateShort = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" })} · ${fmtBytes(0)}`;
};
const getMimeIcon = (mime: string | null | undefined, size = 16) => {
  if (!mime) return <File size={size} />;
  if (mime.startsWith("image/")) return <Image size={size} />;
  if (mime.startsWith("video/")) return <Video size={size} />;
  if (mime.includes("pdf") || mime.startsWith("text/")) return <FileText size={size} />;
  return <File size={size} />;
};
const getMimeColor = (mime: string | null | undefined): string => {
  if (!mime) return "#6b7280";
  if (mime.startsWith("image/")) return "#8b5cf6";
  if (mime.startsWith("video/")) return "#ef4444";
  if (mime.includes("pdf")) return "var(--warning)";
  return "#6b7280";
};
type BV = "default" | "success" | "warning" | "danger" | "info" | "muted" | "golden" | "terra";
const statusV = (s: string): BV => ({
  active: "success", archived: "muted", quarantined: "danger",
  flagged: "danger", replaced: "info", deleted: "danger",
} as Record<string, BV>)[s] ?? "muted";

const PAGE_SIZE = 25;
const STORAGE_LIMIT_BYTES = 500 * 1024 * 1024 * 1024; // 500 GB

// ── Interfaces ────────────────────────────────────────────────────────────────

interface Filters {
  q: string; context: string; ownerType: string; fileType: string;
  status: string; visibility: string; isFlagged: string;
  dateFrom: string; dateTo: string; sort: string;
}
const DEFAULT_FILTERS: Filters = {
  q: "", context: "", ownerType: "", fileType: "", status: "",
  visibility: "", isFlagged: "", dateFrom: "", dateTo: "", sort: "newest",
};

type TabKey = "all" | "images" | "documents" | "videos" | "flagged" | "recent" | "archived";
const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: "all",       label: "All Files",       icon: <Layers size={13} />     },
  { key: "images",    label: "Images",           icon: <Image size={13} />      },
  { key: "documents", label: "Documents",        icon: <FileText size={13} />   },
  { key: "videos",    label: "Videos",           icon: <Video size={13} />      },
  { key: "flagged",   label: "Flagged",          icon: <Flag size={13} />       },
  { key: "recent",    label: "Recently Uploaded",icon: <Clock size={13} />      },
  { key: "archived",  label: "Archived",         icon: <Archive size={13} />    },
];

type ActiveModal =
  | { type: "flag"; asset: MediaAssetAdmin }
  | { type: "quarantine"; asset: MediaAssetAdmin }
  | { type: "delete"; asset: MediaAssetAdmin }
  | { type: "upload" }
  | { type: "bulk_visibility" }
  | null;

// ── Summary Cards ─────────────────────────────────────────────────────────────

function SummaryCards({ s }: { s: MediaSummary }) {
  const pct = (n: number) => s.total > 0 ? `${((n / s.total) * 100).toFixed(1)}% of total` : "—";
  const storagePct = ((s.total_size_bytes / STORAGE_LIMIT_BYTES) * 100).toFixed(1);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
      <StatCard
        label="Total Files"
        value={s.total.toLocaleString()}
        change={s.recent_count > 0 ? `+${s.recent_count} this week` : undefined}
        trend="up"
        icon={<HardDrive />}
        accent="var(--brand)"
      />
      <StatCard
        label="Images"
        value={s.images_count.toLocaleString()}
        change={pct(s.images_count)}
        trend="neutral"
        icon={<Image />}
        accent="#8b5cf6"
      />
      <StatCard
        label="Documents"
        value={s.documents_count.toLocaleString()}
        change={pct(s.documents_count)}
        trend="neutral"
        icon={<FileText />}
        accent="var(--warning)"
      />
      <StatCard
        label="Videos"
        value={s.videos_count.toLocaleString()}
        change={pct(s.videos_count)}
        trend="neutral"
        icon={<Video />}
        accent="#ef4444"
      />
      <StatCard
        label="Storage Used"
        value={fmtBytes(s.total_size_bytes)}
        change={`${storagePct}% of 500 GB`}
        trend={Number(storagePct) > 80 ? "down" : "neutral"}
        icon={<BarChart2 />}
        accent="var(--success)"
      />
      <StatCard
        label="Flagged Files"
        value={s.flagged.toLocaleString()}
        change={s.flagged > 0 ? "Need review" : "All clear"}
        trend={s.flagged > 0 ? "down" : "neutral"}
        icon={<Flag />}
        alert={s.flagged > 0}
      />
    </div>
  );
}

// ── Tab Bar ───────────────────────────────────────────────────────────────────

function TabBar({ active, onChange, summary }: { active: TabKey; onChange: (t: TabKey) => void; summary: MediaSummary | null }) {
  const counts: Record<TabKey, number | undefined> = {
    all:       summary?.total,
    images:    summary?.images_count,
    documents: summary?.documents_count,
    videos:    summary?.videos_count,
    flagged:   summary?.flagged,
    recent:    summary?.recent_count,
    archived:  summary?.archived,
  };
  return (
    <div style={{ display: "flex", gap: 2, marginBottom: 16, borderBottom: "1px solid var(--border)", overflowX: "auto" }}>
      {TABS.map((t) => (
        <button key={t.key} onClick={() => onChange(t.key)} style={{
          display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
          border: "none", borderBottom: active === t.key ? "2px solid var(--brand)" : "2px solid transparent",
          background: "none", cursor: "pointer", whiteSpace: "nowrap",
          color: active === t.key ? "var(--brand)" : "var(--text-secondary)",
          fontWeight: active === t.key ? 600 : 400, fontSize: 13,
        }}>
          {t.icon} {t.label}
          {counts[t.key] !== undefined && counts[t.key]! > 0 && (
            <span style={{ fontSize: 11, background: active === t.key ? "var(--brand)" : "var(--surface-sunken)", color: active === t.key ? "#fff" : "var(--text-secondary)", borderRadius: 999, padding: "1px 7px", fontWeight: 700 }}>
              {counts[t.key]!.toLocaleString()}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// ── Toolbar ───────────────────────────────────────────────────────────────────

function Toolbar({ filters, onChange, viewMode, onViewMode, onUpload }: {
  filters: Filters; onChange: (f: Filters) => void;
  viewMode: "grid" | "list"; onViewMode: (v: "grid" | "list") => void;
  onUpload: () => void;
}) {
  const [showMore, setShowMore] = useState(false);
  const set = (k: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...filters, [k]: e.target.value });
  const inp: React.CSSProperties = { height: 34, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 12 };

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }} />
          <input placeholder="Search files by name, tag, owner…" value={filters.q} onChange={set("q")}
            style={{ ...inp, width: "100%", paddingLeft: 30, paddingRight: 10 }} />
        </div>
        <select value={filters.context} onChange={set("context")} style={inp}>
          <option value="">All Contexts</option>
          {["provider_document","profile_photo","shop_photo","complaint_evidence","job_photo","chat_attachment","review_media","marketing_asset","booking_photo","catalog_icon"].map(c => (
            <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select value={filters.fileType} onChange={set("fileType")} style={inp}>
          <option value="">All Types</option>
          <option value="image">Images</option>
          <option value="video">Videos</option>
          <option value="application">Documents</option>
          <option value="text">Text</option>
        </select>
        <select value={filters.status} onChange={set("status")} style={inp}>
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="quarantined">Quarantined</option>
        </select>
        <select value={filters.sort} onChange={set("sort")} style={inp}>
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="largest">Largest First</option>
          <option value="smallest">Smallest First</option>
        </select>
        <Btn variant="secondary" size="sm" onClick={() => setShowMore(!showMore)} style={{ flexShrink: 0 }}>
          <Filter size={12} /> More {showMore ? <ChevronDown size={11} style={{ transform: "rotate(180deg)" }} /> : <ChevronDown size={11} />}
        </Btn>
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
          <button onClick={() => onViewMode("grid")} style={{ padding: "6px 10px", background: viewMode === "grid" ? "var(--brand)" : "var(--surface)", color: viewMode === "grid" ? "#fff" : "var(--text-secondary)", border: "none", cursor: "pointer" }}>
            <Grid size={14} />
          </button>
          <button onClick={() => onViewMode("list")} style={{ padding: "6px 10px", background: viewMode === "list" ? "var(--brand)" : "var(--surface)", color: viewMode === "list" ? "#fff" : "var(--text-secondary)", border: "none", cursor: "pointer" }}>
            <List size={14} />
          </button>
        </div>
        <Btn variant="primary" size="sm" onClick={onUpload} style={{ flexShrink: 0 }}>
          <Upload size={12} /> Upload
        </Btn>
      </div>
      {showMore && (
        <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select value={filters.ownerType} onChange={set("ownerType")} style={inp}>
            <option value="">All Owners</option>
            <option value="tenant">Tenant</option>
            <option value="user">User</option>
            <option value="customer">Customer</option>
            <option value="admin">Admin</option>
          </select>
          <select value={filters.visibility} onChange={set("visibility")} style={inp}>
            <option value="">All Visibility</option>
            <option value="public">Public</option>
            <option value="private">Private</option>
          </select>
          <select value={filters.isFlagged} onChange={set("isFlagged")} style={inp}>
            <option value="">All</option>
            <option value="true">Flagged Only</option>
            <option value="false">Not Flagged</option>
          </select>
          <input type="date" value={filters.dateFrom} onChange={set("dateFrom")} style={inp} />
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>to</span>
          <input type="date" value={filters.dateTo} onChange={set("dateTo")} style={inp} />
          <Btn variant="secondary" size="sm" onClick={() => { onChange(DEFAULT_FILTERS); setShowMore(false); }}>Clear All</Btn>
        </div>
      )}
    </div>
  );
}

// ── Active Filter Chips ───────────────────────────────────────────────────────

function ActiveChips({ filters, onChange }: { filters: Filters; onChange: (f: Filters) => void }) {
  const chips: { key: keyof Filters; label: string }[] = [];
  if (filters.q)          chips.push({ key: "q",          label: `"${filters.q}"` });
  if (filters.context)    chips.push({ key: "context",    label: filters.context.replace(/_/g, " ") });
  if (filters.fileType)   chips.push({ key: "fileType",   label: filters.fileType });
  if (filters.status)     chips.push({ key: "status",     label: filters.status });
  if (filters.visibility) chips.push({ key: "visibility", label: filters.visibility });
  if (filters.isFlagged)  chips.push({ key: "isFlagged",  label: filters.isFlagged === "true" ? "Flagged" : "Not flagged" });
  if (filters.ownerType)  chips.push({ key: "ownerType",  label: filters.ownerType });
  if (filters.dateFrom)   chips.push({ key: "dateFrom",   label: `From ${filters.dateFrom}` });
  if (filters.dateTo)     chips.push({ key: "dateTo",     label: `To ${filters.dateTo}` });
  if (!chips.length) return null;
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
      {chips.map((c) => (
        <span key={c.key} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, background: "var(--accent-muted)", color: "var(--accent)", border: "1px solid var(--border)", borderRadius: 999, padding: "2px 10px" }}>
          {c.label}
          <button onClick={() => onChange({ ...filters, [c.key]: "" })} style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", padding: 0, lineHeight: 1 }}><X size={10} /></button>
        </span>
      ))}
      <Btn variant="ghost" size="sm" onClick={() => onChange(DEFAULT_FILTERS)} style={{ fontSize: 11 }}>Clear all</Btn>
    </div>
  );
}

// ── Bulk Action Bar ───────────────────────────────────────────────────────────

function BulkActionBar({ count, onArchive, onDelete, onChangeVisibility, onClear }: {
  count: number; onArchive: () => void; onDelete: () => void;
  onChangeVisibility: () => void; onClear: () => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", background: "var(--accent-muted)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", marginBottom: 12 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent)" }}>{count} selected</span>
      <div style={{ display: "flex", gap: 6 }}>
        <Btn variant="secondary" size="sm" onClick={onArchive}><Archive size={12} /> Archive</Btn>
        <Btn variant="secondary" size="sm" onClick={onChangeVisibility}><Lock size={12} /> Visibility</Btn>
        <Btn variant="danger" size="sm" onClick={onDelete}><Trash2 size={12} /> Delete</Btn>
      </div>
      <button onClick={onClear} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}><X size={14} /></button>
    </div>
  );
}

// ── Filter Sidebar ────────────────────────────────────────────────────────────

function FilterSidebar({ filters, onChange, onSaveView }: {
  filters: Filters; onChange: (f: Filters) => void; onSaveView?: () => void;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const toggle = (k: string) => setCollapsed((p) => ({ ...p, [k]: !p[k] }));
  const sel: React.CSSProperties = { width: "100%", height: 32, border: "1px solid var(--border)", borderRadius: 6, padding: "0 8px", background: "var(--surface)", color: "var(--text)", fontSize: 12 };

  const Section = ({ title, k, children }: { title: string; k: string; children: React.ReactNode }) => (
    <div style={{ marginBottom: 14, borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
      <button onClick={() => toggle(k)} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", background: "none", border: "none", cursor: "pointer", padding: "0 0 6px", color: "var(--text)", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {title} {collapsed[k] ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
      </button>
      {!collapsed[k] && <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>}
    </div>
  );

  return (
    <div style={{ width: 200, flexShrink: 0, padding: "0 16px 0 0" }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 16, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Filters</div>

      <Section title="Context" k="ctx">
        <select value={filters.context} onChange={(e) => onChange({ ...filters, context: e.target.value })} style={sel}>
          <option value="">All</option>
          {["provider_document","profile_photo","shop_photo","complaint_evidence","job_photo","chat_attachment","review_media","marketing_asset","booking_photo","catalog_icon"].map(c => (
            <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
          ))}
        </select>
      </Section>

      <Section title="Owner Type" k="own">
        {["tenant","user","customer","admin"].map((o) => (
          <label key={o} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer" }}>
            <input type="radio" name="ownerType" checked={filters.ownerType === o} onChange={() => onChange({ ...filters, ownerType: o })} />
            {o.charAt(0).toUpperCase() + o.slice(1)}
          </label>
        ))}
        {filters.ownerType && <Btn variant="ghost" size="sm" onClick={() => onChange({ ...filters, ownerType: "" })} style={{ fontSize: 10, padding: "2px 6px" }}>Clear</Btn>}
      </Section>

      <Section title="File Type" k="ft">
        {[["image","Images"],["video","Videos"],["application","Documents"],["text","Text"]].map(([v, l]) => (
          <label key={v} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer" }}>
            <input type="radio" name="fileType" checked={filters.fileType === v} onChange={() => onChange({ ...filters, fileType: v })} />
            {l}
          </label>
        ))}
        {filters.fileType && <Btn variant="ghost" size="sm" onClick={() => onChange({ ...filters, fileType: "" })} style={{ fontSize: 10, padding: "2px 6px" }}>Clear</Btn>}
      </Section>

      <Section title="Visibility" k="vis">
        {[["","All"],["public","Public"],["private","Private"]].map(([v, l]) => (
          <label key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer" }}>
            <input type="radio" name="visibility" checked={filters.visibility === v} onChange={() => onChange({ ...filters, visibility: v })} />
            {l}
          </label>
        ))}
      </Section>

      <Section title="Status" k="sta">
        {[["","All"],["active","Active"],["archived","Archived"],["quarantined","Quarantined"]].map(([v, l]) => (
          <label key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer" }}>
            <input type="radio" name="status" checked={filters.status === v} onChange={() => onChange({ ...filters, status: v })} />
            {l}
          </label>
        ))}
      </Section>

      <Section title="Flagged" k="flg">
        {[["","All"],["true","Flagged only"],["false","Not flagged"]].map(([v, l]) => (
          <label key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer" }}>
            <input type="radio" name="isFlagged" checked={filters.isFlagged === v} onChange={() => onChange({ ...filters, isFlagged: v })} />
            {l}
          </label>
        ))}
      </Section>

      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Upload Date</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <input type="date" value={filters.dateFrom} onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })} style={{ ...sel, fontSize: 11 }} />
          <input type="date" value={filters.dateTo} onChange={(e) => onChange({ ...filters, dateTo: e.target.value })} style={{ ...sel, fontSize: 11 }} />
        </div>
      </div>

      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 4, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Saved Views</div>
        {["Complaint Evidence","Provider Docs","Booking Photos","Flagged Files"].map((v) => (
          <button key={v} style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: 12, padding: "3px 0", textAlign: "left" }}
            onClick={() => onChange({ ...DEFAULT_FILTERS, context: v.toLowerCase().replace(/ /g, "_") })}>
            <FolderOpen size={11} /> {v}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Media Grid Card ───────────────────────────────────────────────────────────

function MediaCard({ asset, selected, onSelect, onPreview, onDetail, onArchive, onDelete, onFlag, onCopyLink }: {
  asset: MediaAssetAdmin; selected: boolean;
  onSelect: () => void; onPreview: () => void; onDetail: () => void;
  onArchive: () => void; onDelete: () => void; onFlag: () => void; onCopyLink: () => void;
}) {
  const [hov, setHov] = useState(false);
  const isImage = asset.mime_type?.startsWith("image/");
  const mColor = getMimeColor(asset.mime_type);

  return (
    <div
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ position: "relative", border: `2px solid ${selected ? "var(--brand)" : hov ? "var(--border-strong)" : "var(--border)"}`, borderRadius: 10, overflow: "hidden", background: "var(--surface)", transition: "all 0.15s", cursor: "pointer" }}
    >
      {/* Thumbnail */}
      <div style={{ height: 120, background: isImage ? "#f3f4f6" : `${mColor}12`, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}
        onClick={onDetail}>
        {isImage && asset.preview_url
          ? <img src={asset.preview_url} alt={asset.file_name_original} style={{ width: "100%", height: "100%", objectFit: "cover" }} onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          : <div style={{ color: mColor }}>{getMimeIcon(asset.mime_type, 36)}</div>
        }
        {/* Checkbox overlay */}
        <div style={{ position: "absolute", top: 8, left: 8 }} onClick={(e) => { e.stopPropagation(); onSelect(); }}>
          <div style={{ width: 18, height: 18, borderRadius: 4, border: `2px solid ${selected ? "var(--brand)" : "#fff"}`, background: selected ? "var(--brand)" : "rgba(0,0,0,.4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            {selected && <CheckCircle size={10} color="#fff" />}
          </div>
        </div>
        {/* Hover actions */}
        {hov && (
          <div style={{ position: "absolute", bottom: 8, right: 8, display: "flex", gap: 4 }}>
            <button onClick={(e) => { e.stopPropagation(); onPreview(); }} style={{ width: 28, height: 28, borderRadius: 6, background: "rgba(0,0,0,.6)", border: "none", cursor: "pointer", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}><ZoomIn size={12} /></button>
            <button onClick={(e) => { e.stopPropagation(); onCopyLink(); }} style={{ width: 28, height: 28, borderRadius: 6, background: "rgba(0,0,0,.6)", border: "none", cursor: "pointer", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}><Copy size={12} /></button>
          </div>
        )}
        {/* Badges */}
        <div style={{ position: "absolute", top: 8, right: 8, display: "flex", flexDirection: "column", gap: 3 }}>
          {asset.is_flagged && <Badge variant="danger" size="sm"><Flag size={8} /></Badge>}
          {!asset.is_public && <Badge variant="muted" size="sm"><Lock size={8} /></Badge>}
        </div>
      </div>

      {/* Info */}
      <div style={{ padding: "10px 12px" }}>
        <div style={{ fontSize: 12, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: 3 }} title={asset.file_name_original}>
          {asset.file_name_original}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 4 }}>
          {asset.media_context?.replace(/_/g, " ")}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{fmtBytes(asset.file_size_bytes)}</span>
          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{fmtDate(asset.created_at)}</span>
        </div>
        <div style={{ marginTop: 6, display: "flex", gap: 4, justifyContent: "flex-end" }} onClick={(e: React.MouseEvent) => e.stopPropagation()}>
          <Btn variant="ghost" size="sm" onClick={onDetail} style={{ padding: "3px 6px", fontSize: 11 }}><Eye size={11} /></Btn>
          <Btn variant="ghost" size="sm" onClick={onArchive} style={{ padding: "3px 6px", fontSize: 11 }}><Archive size={11} /></Btn>
          <Btn variant="ghost" size="sm" onClick={onDelete} style={{ padding: "3px 6px", fontSize: 11, color: "#ef4444" }}><Trash2 size={11} /></Btn>
        </div>
      </div>
    </div>
  );
}

// ── Media Grid ────────────────────────────────────────────────────────────────

function MediaGrid({ items, selected, onSelect, onPreview, onDetail, onArchive, onDelete, onFlag, onCopyLink }: {
  items: MediaAssetAdmin[]; selected: Set<string>;
  onSelect: (id: string) => void; onPreview: (a: MediaAssetAdmin) => void;
  onDetail: (a: MediaAssetAdmin) => void; onArchive: (a: MediaAssetAdmin) => void;
  onDelete: (a: MediaAssetAdmin) => void; onFlag: (a: MediaAssetAdmin) => void;
  onCopyLink: (a: MediaAssetAdmin) => void;
}) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
      {items.map((a) => (
        <MediaCard
          key={a.id} asset={a} selected={selected.has(a.id)}
          onSelect={() => onSelect(a.id)} onPreview={() => onPreview(a)}
          onDetail={() => onDetail(a)} onArchive={() => onArchive(a)}
          onDelete={() => onDelete(a)} onFlag={() => onFlag(a)} onCopyLink={() => onCopyLink(a)}
        />
      ))}
    </div>
  );
}

// ── Detail Drawer ─────────────────────────────────────────────────────────────

function DetailDrawer({ asset, onClose, onArchive, onFlag, onMarkClean, onDelete }: {
  asset: MediaAssetAdmin; onClose: () => void;
  onArchive: () => void; onFlag: () => void;
  onMarkClean: () => void; onDelete: () => void;
}) {
  const { data: links } = useApi(() => mediaAdminApi.getLinkedRecords(asset.id), [asset.id]);
  const { data: logs  } = useApi(() => mediaAdminApi.getAuditLogs(asset.id, 30), [asset.id]);
  const [tab, setTab]   = useState<"info" | "access" | "links" | "audit">("info");
  const { execute: execPreview } = useAction(async () => {
    const signed = await mediaAdminApi.createSignedPreviewUrl(asset.id);
    window.open(signed.url, "_blank");
  });
  const { execute: execDownload } = useAction(async () => {
    const signed = await mediaAdminApi.createSignedDownloadUrl(asset.id);
    const a = document.createElement("a"); a.href = signed.url; a.click();
  });

  const Row = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div style={{ display: "flex", gap: 8, paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 130, flexShrink: 0, fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", paddingTop: 2 }}>{label}</div>
      <div style={{ flex: 1, fontSize: 13 }}>{value ?? "—"}</div>
    </div>
  );

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex" }}>
      <div style={{ flex: 1, background: "rgba(0,0,0,.4)" }} onClick={onClose} />
      <div style={{ width: 520, background: "var(--surface)", borderLeft: "1px solid var(--border)", overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", position: "sticky", top: 0, background: "var(--surface)", zIndex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 15 }}>File Detail</div>
          <div style={{ display: "flex", gap: 6 }}>
            <Btn variant="secondary" size="sm" onClick={() => execPreview()}><Eye size={12} /> Preview</Btn>
            <Btn variant="secondary" size="sm" onClick={() => execDownload()}><Download size={12} /> Download</Btn>
            {asset.is_flagged
              ? <Btn variant="success" size="sm" onClick={onMarkClean}><Shield size={12} /> Mark Clean</Btn>
              : <Btn variant="warning" size="sm" onClick={onFlag}><Flag size={12} /> Flag</Btn>
            }
            <Btn variant="danger" size="sm" onClick={onDelete}><Trash2 size={12} /></Btn>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", padding: 4 }}><X size={16} /></button>
          </div>
        </div>

        {/* Preview */}
        {asset.mime_type?.startsWith("image/") && asset.preview_url && (
          <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)", background: "var(--bg)" }}>
            <img src={asset.preview_url} alt={asset.file_name_original}
              style={{ width: "100%", maxHeight: 220, objectFit: "contain", borderRadius:"var(--radius-md)" }} />
          </div>
        )}
        {!asset.mime_type?.startsWith("image/") && (
          <div style={{ padding: "24px 20px", borderBottom: "1px solid var(--border)", background: "var(--bg)", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <div style={{ width: 64, height: 64, borderRadius: 14, background: `${getMimeColor(asset.mime_type)}14`, display: "flex", alignItems: "center", justifyContent: "center", color: getMimeColor(asset.mime_type) }}>
              {getMimeIcon(asset.mime_type, 28)}
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{asset.mime_type}</div>
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)", padding: "0 20px" }}>
          {(["info","access","links","audit"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} style={{ padding: "10px 14px", border: "none", borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent", background: "none", cursor: "pointer", color: tab === t ? "var(--brand)" : "var(--text-secondary)", fontWeight: tab === t ? 600 : 400, fontSize: 12, textTransform: "capitalize" }}>
              {t === "info" ? "Overview" : t === "access" ? "Access" : t === "links" ? "Linked Records" : "Audit Log"}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ padding: "16px 20px", flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          {tab === "info" && (
            <>
              <Row label="Filename"   value={asset.file_name_original} />
              <Row label="MIME Type"  value={asset.mime_type} />
              <Row label="Size"       value={fmtBytes(asset.file_size_bytes)} />
              <Row label="Context"    value={asset.media_context?.replace(/_/g, " ")} />
              <Row label="Owner Type" value={asset.owner_type} />
              <Row label="Status"     value={<Badge variant={statusV(asset.status)}>{asset.status}</Badge>} />
              <Row label="Visibility" value={asset.is_public ? <Badge variant="info"><Unlock size={10} /> Public</Badge> : <Badge variant="muted"><Lock size={10} /> Private</Badge>} />
              <Row label="Flagged"    value={asset.is_flagged ? <Badge variant="danger"><Flag size={10} /> Yes — {asset.flag_reason}</Badge> : <Badge variant="success">No</Badge>} />
              <Row label="Moderation" value={<Badge variant={asset.moderation_status === "clean" ? "success" : "warning"}>{asset.moderation_status || "clean"}</Badge>} />
              <Row label="Uploaded"   value={fmtDate(asset.created_at)} />
              <Row label="Archived"   value={fmtDate(asset.archived_at)} />
              {asset.width && asset.height && <Row label="Dimensions" value={`${asset.width} × ${asset.height}`} />}
            </>
          )}
          {tab === "access" && (
            <>
              <Row label="Public URL"      value={asset.is_public ? "Accessible" : "Restricted"} />
              <Row label="Direct Access"   value={asset.is_public ? "Yes" : "Signed URL only"} />
              <Row label="Preview Access"  value="Signed URL (15 min TTL)" />
              <Row label="Download Access" value="Signed URL (60 min TTL)" />
              <Row label="Storage Driver"  value={asset.storage_driver} />
              <div style={{ marginTop: 8, padding: 12, background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", fontSize: 12, color: "var(--text-secondary)" }}>
                <strong>Security:</strong> Private files require a signed URL. Links are single-use and expire. All admin access is audit-logged.
              </div>
            </>
          )}
          {tab === "links" && (
            <div>
              {!links || (links as MediaLinkedRecord[]).length === 0
                ? <div style={{ textAlign: "center", padding: "24px 0", color: "var(--text-secondary)", fontSize: 13 }}>No linked records found.</div>
                : (links as MediaLinkedRecord[]).map((l) => (
                  <div key={l.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{l.module_name} / {l.record_type}</div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{l.display_name || l.record_id} · <Badge variant={l.status === "active" ? "success" : "muted"} size="sm">{l.status}</Badge></div>
                    </div>
                    <button style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}><ExternalLink size={12} /></button>
                  </div>
                ))
              }
            </div>
          )}
          {tab === "audit" && (
            <div>
              {!logs || (logs as MediaAuditLog[]).length === 0
                ? <div style={{ textAlign: "center", padding: "24px 0", color: "var(--text-secondary)", fontSize: 13 }}>No audit events.</div>
                : (logs as MediaAuditLog[]).map((l) => (
                  <div key={l.id} style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--accent-muted)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Clock size={12} color="var(--accent)" />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{l.action_type.replace(/_/g, " ")}</div>
                      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{l.actor_role || "system"} · {fmtDate(l.created_at)}</div>
                    </div>
                  </div>
                ))
              }
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Upload Modal ──────────────────────────────────────────────────────────────

function UploadModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [file, setFile]             = useState<File | null>(null);
  const [context, setContext]       = useState("general");
  const [ownerType, setOwnerType]   = useState("admin");
  const [isPublic, setIsPublic]     = useState(false);
  const [description, setDescription] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const { execute, loading, error } = useAction(async () => {
    if (!file) throw new Error("Please select a file.");
    await mediaAdminApi.uploadMedia(file, context, ownerType, isPublic);
    onDone();
  });
  const inp: React.CSSProperties = { width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 13 };

  return (
    <Modal open title="Upload Media" onClose={onClose} size="md">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>File *</label>
          <div
            onClick={() => inputRef.current?.click()}
            style={{ border: `2px dashed ${file ? "var(--brand)" : "var(--border)"}`, borderRadius:"var(--radius-md)", padding: "20px", textAlign: "center", cursor: "pointer", background: file ? "var(--accent-muted)" : "var(--surface-sunken)" }}
          >
            {file ? (
              <div style={{ fontSize: 13 }}>{file.name} · {fmtBytes(file.size)}</div>
            ) : (
              <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                <Upload size={20} style={{ display: "block", margin: "0 auto 6px" }} />
                Click to select or drag and drop
              </div>
            )}
          </div>
          <input ref={inputRef} type="file" style={{ display: "none" }} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Context *</label>
          <select value={context} onChange={(e) => setContext(e.target.value)} style={inp}>
            {["general","provider_document","profile_photo","shop_photo","complaint_evidence","job_photo","marketing_asset","catalog_icon"].map(c => (
              <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Owner Type</label>
            <select value={ownerType} onChange={(e) => setOwnerType(e.target.value)} style={inp}>
              <option value="admin">Admin</option>
              <option value="tenant">Tenant</option>
              <option value="user">User</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Visibility</label>
            <select value={isPublic ? "public" : "private"} onChange={(e) => setIsPublic(e.target.value === "public")} style={inp}>
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
          </div>
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional description…" style={inp} />
        </div>
        {error && <div style={{ fontSize: 12, color: "#ef4444", padding: "8px 12px", background: "var(--danger-bg)", borderRadius: 6 }}>{error}</div>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", paddingTop: 4 }}>
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" onClick={() => execute()} disabled={loading || !file}>
            <Upload size={13} /> {loading ? "Uploading…" : "Upload File"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Action Modals ─────────────────────────────────────────────────────────────

function FlagModal({ open, asset, onClose, onDone }: { open: boolean; asset: MediaAssetAdmin | null; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const { execute, loading } = useAction(async () => {
    if (!asset) return;
    await mediaAdminApi.flagMedia(asset.id, reason || "Flagged by admin");
    setReason(""); onDone();
  });
  return (
    <Modal open={open} title="Flag File" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Flag <strong>{asset?.file_name_original}</strong> for review.</p>
      <select value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", marginBottom: 16 }}>
        <option value="">Select reason…</option>
        <option value="virus_scan_failed">Virus scan failed</option>
        <option value="sensitive_document">Sensitive document</option>
        <option value="policy_violation">Policy violation</option>
        <option value="reported_by_user">Reported by user</option>
        <option value="manual_review">Manual review required</option>
        <option value="invalid_file_type">Invalid file type</option>
        <option value="oversized_file">Oversized file</option>
      </select>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="danger" onClick={() => execute()} disabled={loading}>Flag File</Btn>
      </div>
    </Modal>
  );
}

function DeleteModal({ open, asset, onClose, onDone }: { open: boolean; asset: MediaAssetAdmin | null; onClose: () => void; onDone: () => void }) {
  const [force, setForce] = useState(false);
  const { execute, loading, error } = useAction(async () => {
    if (!asset) return;
    await mediaAdminApi.deleteMedia(asset.id, force);
    setForce(false); onDone();
  });
  return (
    <Modal open={open} title="Delete File" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Delete <strong>{asset?.file_name_original}</strong>? This action cannot be undone.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 12 }}>{error}</div>}
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 16, cursor: "pointer" }}>
        <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
        Force delete (bypass active-link guard)
      </label>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="danger" onClick={() => execute()} disabled={loading}>Delete</Btn>
      </div>
    </Modal>
  );
}

function BulkVisibilityModal({ open, count, onClose, onDone }: { open: boolean; count: number; onClose: () => void; onDone: (isPublic: boolean) => void }) {
  const [isPublic, setIsPublic] = useState(false);
  return (
    <Modal open={open} title="Change Visibility" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Change visibility of <strong>{count} selected files</strong>.</p>
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13 }}>
          <input type="radio" checked={!isPublic} onChange={() => setIsPublic(false)} /> <Lock size={13} /> Private
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13 }}>
          <input type="radio" checked={isPublic} onChange={() => setIsPublic(true)} /> <Unlock size={13} /> Public
        </label>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" onClick={() => onDone(isPublic)}>Apply</Btn>
      </div>
    </Modal>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Row = MediaAssetAdmin & Record<string, unknown>;

export default function MediaLibraryPage() {
  const [filters, setFilters]   = useState<Filters>(DEFAULT_FILTERS);
  const [tab, setTab]           = useState<TabKey>("all");
  const [page, setPage]         = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [detail, setDetail]     = useState<MediaAssetAdmin | null>(null);
  const [modal, setModal]       = useState<ActiveModal>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Derive effective filters from active tab
  const effectiveFilters = useCallback(() => {
    const f = { ...filters };
    if (tab === "images")    { f.fileType = "image"; }
    if (tab === "documents") { f.fileType = "application"; }
    if (tab === "videos")    { f.fileType = "video"; }
    if (tab === "flagged")   { f.isFlagged = "true"; }
    if (tab === "archived")  { f.status = "archived"; }
    if (tab === "recent") {
      const d = new Date(); d.setDate(d.getDate() - 7);
      f.dateFrom = d.toISOString().split("T")[0];
    }
    return f;
  }, [filters, tab]);

  const ef = effectiveFilters();
  // Stringify to a stable primitive so useApi only re-fetches when values change,
  // not on every render when the object reference changes.
  const efKey = JSON.stringify(ef);

  const { data: summary, refetch: reloadSummary } = useApi(() => mediaAdminApi.getSummary(), []);
  const { data: listData, loading, refetch: reload } = useApi(
    () => {
      const f: Filters = JSON.parse(efKey) as Filters;
      return mediaAdminApi.listMedia({
        q: f.q || undefined,
        context: f.context || undefined,
        ownerType: f.ownerType || undefined,
        fileType: f.fileType || undefined,
        status: f.status || undefined,
        visibility: f.visibility || undefined,
        isFlagged: f.isFlagged === "" ? undefined : f.isFlagged === "true",
        dateFrom: f.dateFrom || undefined,
        dateTo: f.dateTo || undefined,
        page,
        pageSize,
      });
    },
    [efKey, page, pageSize],
  );

  const refresh = useCallback(() => { reload(); reloadSummary(); setSelected(new Set()); }, [reload, reloadSummary]);

  const { execute: execArchive }   = useAction(async (a: MediaAssetAdmin) => { await mediaAdminApi.archiveMedia(a.id); refresh(); });
  const { execute: execRestore }   = useAction(async (a: MediaAssetAdmin) => { await mediaAdminApi.restoreMedia(a.id); refresh(); });
  const { execute: execMarkClean } = useAction(async (a: MediaAssetAdmin) => { await mediaAdminApi.markClean(a.id); refresh(); });
  const { execute: execCopyLink }  = useAction(async (a: MediaAssetAdmin) => {
    const signed = await mediaAdminApi.createSignedPreviewUrl(a.id);
    await navigator.clipboard.writeText(window.location.origin + signed.url).catch(() => {});
  });
  const { execute: execBulkArchive, loading: bulkArchiving } = useAction(async () => {
    await mediaAdminApi.bulkArchive(Array.from(selected));
    refresh();
  });
  const { execute: execBulkDelete } = useAction(async () => {
    await mediaAdminApi.bulkDelete(Array.from(selected));
    refresh();
  });
  const { execute: execBulkVisibility } = useAction(async (isPublic: boolean) => {
    await mediaAdminApi.bulkChangeVisibility(Array.from(selected), isPublic);
    setModal(null); refresh();
  });

  const handleExport = async () => {
    try {
      const blob = await mediaAdminApi.exportCsv({ context: ef.context, status: ef.status, isFlagged: ef.isFlagged === "true" ? true : undefined });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "media_export.csv"; a.click();
    } catch { /* silent */ }
  };

  const items      = (listData?.items ?? []) as Row[];
  const total      = listData?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  const toggleSelect = (id: string) => {
    setSelected((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  };
  const selectAll = () => setSelected(new Set(items.map((i) => i.id as string)));
  const clearAll  = () => setSelected(new Set());

  const handleTabChange = (t: TabKey) => {
    setTab(t); setPage(1); clearAll();
    setFilters((f) => ({ ...f, fileType: "", status: "", isFlagged: "", dateFrom: "" }));
  };

  // Table columns
  const columns: { key: string; label: string; render?: (_v: unknown, row: Row) => React.ReactNode }[] = [
    {
      key: "select", label: "",
      render: (_v, row) => <input type="checkbox" checked={selected.has(row.id as string)} onChange={() => toggleSelect(row.id as string)} onClick={(e) => e.stopPropagation()} />,
    },
    {
      key: "file", label: "File",
      render: (_v, row) => (
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 6, background: `${getMimeColor(row.mime_type as string)}14`, display: "flex", alignItems: "center", justifyContent: "center", color: getMimeColor(row.mime_type as string), flexShrink: 0 }}>
            {getMimeIcon(row.mime_type as string, 14)}
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.file_name_original as string}</div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{row.mime_type as string}</div>
          </div>
        </div>
      ),
    },
    { key: "media_context", label: "Context", render: (_v, row) => <span style={{ fontSize: 12 }}>{(row.media_context as string)?.replace(/_/g, " ")}</span> },
    { key: "owner_type",    label: "Owner",   render: (_v, row) => <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{row.owner_type as string}</span> },
    {
      key: "linked_module", label: "Linked To",
      render: (_v, row) => row.linked_module ? <Badge variant="info" size="sm"><Link2 size={9} /> {row.linked_module as string}</Badge> : <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>—</span>,
    },
    {
      key: "status", label: "Status",
      render: (_v, row) => (
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <Badge variant={statusV(row.status as string)} size="sm">{row.status as string}</Badge>
          {row.is_flagged && <Badge variant="danger" size="sm"><Flag size={8} /> flagged</Badge>}
        </div>
      ),
    },
    {
      key: "is_public", label: "Visibility",
      render: (_v, row) => row.is_public
        ? <Badge variant="info" size="sm"><Unlock size={9} /> Public</Badge>
        : <Badge variant="muted" size="sm"><Lock size={9} /> Private</Badge>,
    },
    { key: "file_size_bytes", label: "Size",     render: (_v, row) => <span style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{fmtBytes(row.file_size_bytes as number)}</span> },
    { key: "created_at",      label: "Uploaded", render: (_v, row) => <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{fmtDate(row.created_at as string)}</span> },
    {
      key: "actions", label: "",
      render: (_v, row) => (
        <div style={{ display: "flex", gap: 4 }} onClick={(e) => e.stopPropagation()}>
          <Btn variant="ghost" size="sm" onClick={() => setDetail(row as MediaAssetAdmin)} style={{ padding: "3px 6px" }}><Eye size={11} /></Btn>
          <Btn variant="ghost" size="sm" onClick={() => execArchive(row as MediaAssetAdmin)} style={{ padding: "3px 6px" }}><Archive size={11} /></Btn>
          <Btn variant="ghost" size="sm" onClick={() => setModal({ type: "delete", asset: row as MediaAssetAdmin })} style={{ padding: "3px 6px", color: "#ef4444" }}><Trash2 size={11} /></Btn>
        </div>
      ),
    },
  ];

  return (
    <AdminLayout>
      <div style={{ padding: "28px 32px", minHeight: "100vh" }}>
        {/* Header */}
        <SectionHeader
          title="Media Library"
          subtitle="All uploaded files across the platform"
          icon={<HardDrive />}
          actions={
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="secondary" size="sm" onClick={handleExport}><Download size={12} /> Export</Btn>
              <Btn variant="secondary" size="sm" onClick={refresh}><RefreshCw size={12} /> Refresh</Btn>
              <Btn variant="primary" size="sm" onClick={() => setModal({ type: "upload" })}><Upload size={12} /> Upload</Btn>
            </div>
          }
        />

        {/* KPI Cards */}
        {summary && <SummaryCards s={summary} />}

        {/* Tabs */}
        <TabBar active={tab} onChange={handleTabChange} summary={summary ?? null} />

        {/* Main layout: sidebar + content */}
        <div style={{ display: "flex", gap: 0, alignItems: "flex-start" }}>
          <FilterSidebar filters={filters} onChange={(f) => { setFilters(f); setPage(1); }} />

          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Toolbar */}
            <Toolbar
              filters={filters}
              onChange={(f) => { setFilters(f); setPage(1); }}
              viewMode={viewMode}
              onViewMode={setViewMode}
              onUpload={() => setModal({ type: "upload" })}
            />

            {/* Active filter chips */}
            <ActiveChips filters={filters} onChange={(f) => { setFilters(f); setPage(1); }} />

            {/* Bulk action bar */}
            {selected.size > 0 && (
              <BulkActionBar
                count={selected.size}
                onArchive={() => execBulkArchive()}
                onDelete={() => execBulkDelete()}
                onChangeVisibility={() => setModal({ type: "bulk_visibility" })}
                onClear={clearAll}
              />
            )}

            {/* Results */}
            <Card style={{ padding: "16px 20px" }}>
              {/* Row count + select all */}
              {!loading && total > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total.toLocaleString()} files
                    {selected.size > 0 && <span style={{ marginLeft: 8, color: "var(--brand)", fontWeight: 600 }}>· {selected.size} selected</span>}
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <Btn variant="ghost" size="sm" onClick={selectAll} style={{ fontSize: 11 }}>Select all</Btn>
                    {selected.size > 0 && <Btn variant="ghost" size="sm" onClick={clearAll} style={{ fontSize: 11 }}>Clear</Btn>}
                  </div>
                </div>
              )}

              {/* Loading */}
              {loading && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="skeleton" style={{ height: 180, borderRadius: 10 }} />
                  ))}
                </div>
              )}

              {/* Empty state */}
              {!loading && items.length === 0 && (
                <div style={{ textAlign: "center", padding: "56px 0" }}>
                  <div style={{ width: 64, height: 64, borderRadius: "50%", background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                    <HardDrive size={28} style={{ color: "var(--text-tertiary)" }} />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>No media files found</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 400, margin: "0 auto 20px" }}>
                    {Object.values(filters).some(Boolean)
                      ? "No files match these filters. Try changing or clearing your filters."
                      : "Files uploaded from bookings, jobs, complaints, provider verification, and catalog assets will appear here."}
                  </div>
                  {Object.values(filters).some(Boolean)
                    ? <Btn variant="secondary" size="sm" onClick={() => setFilters(DEFAULT_FILTERS)}>Clear Filters</Btn>
                    : <Btn variant="primary" size="sm" onClick={() => setModal({ type: "upload" })}><Upload size={12} /> Upload First File</Btn>
                  }
                </div>
              )}

              {/* Grid view */}
              {!loading && items.length > 0 && viewMode === "grid" && (
                <MediaGrid
                  items={items as MediaAssetAdmin[]}
                  selected={selected}
                  onSelect={toggleSelect}
                  onPreview={(a) => { execCopyLink(a); /* opens signed preview */ }}
                  onDetail={(a) => setDetail(a)}
                  onArchive={(a) => execArchive(a)}
                  onDelete={(a) => setModal({ type: "delete", asset: a })}
                  onFlag={(a) => setModal({ type: "flag", asset: a })}
                  onCopyLink={(a) => execCopyLink(a)}
                />
              )}

              {/* List view */}
              {!loading && items.length > 0 && viewMode === "list" && (
                <DataTable<Row>
                  columns={columns}
                  rows={items}
                  onRowClick={(row) => setDetail(row as MediaAssetAdmin)}
                />
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                    Rows per page:
                    {[10, 25, 50, 100].map((n) => (
                      <button key={n} onClick={() => { setPageSize(n); setPage(1); }} style={{ padding: "2px 8px", borderRadius: 4, border: "1px solid var(--border)", background: pageSize === n ? "var(--brand)" : "var(--surface)", color: pageSize === n ? "#fff" : "var(--text)", cursor: "pointer", fontSize: 11 }}>{n}</button>
                    ))}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page} of {totalPages}</span>
                    <Btn variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft size={13} /></Btn>
                    <Btn variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}><ChevronRight size={13} /></Btn>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>

      {/* Detail Drawer */}
      {detail && (
        <DetailDrawer
          asset={detail}
          onClose={() => setDetail(null)}
          onArchive={() => { execArchive(detail); setDetail(null); }}
          onFlag={() => { setModal({ type: "flag", asset: detail }); setDetail(null); }}
          onMarkClean={() => { execMarkClean(detail); }}
          onDelete={() => { setModal({ type: "delete", asset: detail }); setDetail(null); }}
        />
      )}

      {/* Modals */}
      {modal?.type === "upload" && (
        <UploadModal onClose={() => setModal(null)} onDone={() => { setModal(null); refresh(); }} />
      )}
      <FlagModal
        open={modal?.type === "flag"}
        asset={modal?.type === "flag" ? modal.asset : null}
        onClose={() => setModal(null)}
        onDone={() => { setModal(null); refresh(); }}
      />
      <DeleteModal
        open={modal?.type === "delete"}
        asset={modal?.type === "delete" ? modal.asset : null}
        onClose={() => setModal(null)}
        onDone={() => { setModal(null); refresh(); }}
      />
      <BulkVisibilityModal
        open={modal?.type === "bulk_visibility"}
        count={selected.size}
        onClose={() => setModal(null)}
        onDone={(isPublic) => execBulkVisibility(isPublic)}
      />
    </AdminLayout>
  );
}
