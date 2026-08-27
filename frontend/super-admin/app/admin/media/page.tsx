"use client";
import React, { useState, useCallback, useEffect, useRef } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, CardHeader, SectionHeader, StatCard, KpiGrid, Badge, Btn, Modal, DataTable,
} from "../../../components/shared/ui";
import {
  Search, RefreshCw, Image, FileText, Video, File, Trash2, AlertCircle,
  Download, Eye, Archive, Flag, Shield, CheckCircle, X, Filter, MoreVertical,
  ChevronDown, Lock, Unlock, HardDrive, Upload, Grid, List, Tag, Clock,
  Link2, BarChart2, ChevronRight, ChevronLeft,
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
const EMPTY_STATE_COPY: Record<TabKey, { title: string; description: string; upload: boolean }> = {
  all: { title: "No media files found", description: "Files from bookings, jobs, complaints, provider verification, and catalog workflows will appear here.", upload: true },
  images: { title: "No images found", description: "Upload a platform image or wait for image-producing workflows to create one.", upload: true },
  documents: { title: "No documents found", description: "Verification, policy, invoice, and other document workflows will appear here.", upload: true },
  videos: { title: "No videos found", description: "Uploaded video evidence and platform video assets will appear here.", upload: true },
  flagged: { title: "Moderation queue is clear", description: "No files currently require administrator review.", upload: false },
  recent: { title: "No recent uploads", description: "No files were uploaded during the last seven days.", upload: false },
  archived: { title: "No archived files", description: "Files removed from active use will remain available here according to retention policy.", upload: false },
};

type ActiveModal =
  | { type: "flag"; asset: MediaAssetAdmin }
  | { type: "quarantine"; asset: MediaAssetAdmin }
  | { type: "delete"; asset: MediaAssetAdmin }
  | { type: "upload" }
  | { type: "bulk_visibility" }
  | null;

// ── Summary Cards ─────────────────────────────────────────────────────────────

function SummaryCards({ s, onOpenTab }: { s: MediaSummary; onOpenTab: (tab: TabKey) => void }) {
  return (
    <KpiGrid minCardWidth={210} style={{ marginBottom: 20 }}>
      <StatCard onClick={() => onOpenTab("all")} label="Managed assets" value={s.total.toLocaleString()} change={`${s.active.toLocaleString()} active`} trend="neutral" icon={<HardDrive />} accent="var(--brand)" />
      <StatCard onClick={() => onOpenTab("all")} label="Active storage" value={fmtBytes(s.active_size_bytes)} change={`${s.public_count.toLocaleString()} public · ${s.private_count.toLocaleString()} private`} trend="neutral" icon={<BarChart2 />} accent="var(--success)" />
      <StatCard onClick={() => onOpenTab("flagged")} label="Moderation queue" value={(s.flagged + s.quarantined).toLocaleString()} change={s.flagged + s.quarantined ? "Requires administrator review" : "Queue clear"} trend={s.flagged + s.quarantined ? "down" : "neutral"} icon={<Shield />} alert={s.flagged + s.quarantined > 0} />
      <StatCard onClick={() => onOpenTab("recent")} label="Uploaded in 7 days" value={s.recent_count.toLocaleString()} change={`${s.images_count.toLocaleString()} images · ${s.documents_count.toLocaleString()} documents`} trend="neutral" icon={<Clock />} accent="#8b5cf6" />
    </KpiGrid>
  );
}
interface MediaFilterOptions {
  contexts: Array<{ value: string; count: number }>;
  owner_types: Array<{ value: string; count: number }>;
  statuses: string[];
  file_types: string[];
  visibilities: string[];
  upload_contexts: Array<{ value: string; max_mb: number; allowed_types: string[] }>;
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

function Toolbar({ filters, onChange, viewMode, onViewMode, onUpload, options }: {
  filters: Filters; onChange: (f: Filters) => void;
  viewMode: "grid" | "list"; onViewMode: (v: "grid" | "list") => void;
  onUpload: () => void; options?: MediaFilterOptions | null;
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
          {(options?.contexts ?? []).map(({ value, count }) => (
            <option key={value} value={value}>{value.replace(/_/g, " ")} ({count})</option>
          ))}
        </select>
        <select value={filters.fileType} onChange={set("fileType")} style={inp}>
          <option value="">All Types</option>
          {(options?.file_types ?? ["image", "video", "application", "text"]).map((value) => <option key={value} value={value}>{value === "application" ? "Documents" : value.charAt(0).toUpperCase() + value.slice(1) + "s"}</option>)}
        </select>
        <select value={filters.status} onChange={set("status")} style={inp}>
          <option value="">All Statuses</option>
          {(options?.statuses ?? ["active", "archived", "quarantined"]).filter((value) => value !== "deleted").map((value) => <option key={value} value={value}>{value.replace(/_/g, " ")}</option>)}
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
          <button title="Grid view" aria-label="Grid view" aria-pressed={viewMode === "grid"} onClick={() => onViewMode("grid")} style={{ padding: "6px 10px", background: viewMode === "grid" ? "var(--brand)" : "var(--surface)", color: viewMode === "grid" ? "#fff" : "var(--text-secondary)", border: "none", cursor: "pointer" }}>
            <Grid size={14} />
          </button>
          <button title="List view" aria-label="List view" aria-pressed={viewMode === "list"} onClick={() => onViewMode("list")} style={{ padding: "6px 10px", background: viewMode === "list" ? "var(--brand)" : "var(--surface)", color: viewMode === "list" ? "#fff" : "var(--text-secondary)", border: "none", cursor: "pointer" }}>
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
          {(options?.owner_types ?? []).map(({ value, count }) => <option key={value} value={value}>{value} ({count})</option>)}
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

// ── Media Grid Card ───────────────────────────────────────────────────────────

function SecureThumbnail({ asset, fit = "cover" }: { asset: MediaAssetAdmin; fit?: "cover" | "contain" }) {
  const [source, setSource] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    if (!asset.mime_type?.startsWith("image/") || !asset.preview_url) return;
    mediaAdminApi.fetchSignedFile(asset.preview_url)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setSource(objectUrl);
      })
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [asset.id, asset.mime_type, asset.preview_url]);

  if (source) return <img src={source} alt="" style={{ width: "100%", height: "100%", objectFit: fit }} />;
  return (
    <div style={{ color: getMimeColor(asset.mime_type), display: "grid", placeItems: "center", gap: 5 }}>
      {getMimeIcon(asset.mime_type, 36)}
      <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{failed ? "Preview unavailable" : "Loading preview"}</span>
    </div>
  );
}

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
          ? <SecureThumbnail asset={asset} />
          : <div style={{ color: mColor }}>{getMimeIcon(asset.mime_type, 36)}</div>
        }
        {/* Checkbox overlay */}
        <div role="checkbox" aria-checked={selected} aria-label={(selected ? "Deselect " : "Select ") + asset.file_name_original} tabIndex={0} style={{ position: "absolute", top: 8, left: 8 }} onKeyDown={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); onSelect(); } }} onClick={(e) => { e.stopPropagation(); onSelect(); }}>
          <div style={{ width: 18, height: 18, borderRadius: 4, border: `2px solid ${selected ? "var(--brand)" : "#fff"}`, background: selected ? "var(--brand)" : "rgba(0,0,0,.4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            {selected && <CheckCircle size={10} color="#fff" />}
          </div>
        </div>
        {/* Hover actions */}
        {hov && (
          <div style={{ position: "absolute", bottom: 8, right: 8, display: "flex", gap: 4 }}>
            <button title="Open secure preview" aria-label="Open secure preview" onClick={(e) => { e.stopPropagation(); onPreview(); }} style={{ width: 30, height: 30, borderRadius: 7, background: "rgba(0,0,0,.72)", border: "1px solid rgba(255,255,255,.2)", cursor: "pointer", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}><ZoomIn size={13} /></button>
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
          <Btn aria-label="View details" variant="ghost" size="sm" onClick={onDetail} style={{ padding: "3px 6px", fontSize: 11 }}><Eye size={11} /></Btn>
          {asset.status === "archived"
            ? <Btn aria-label="Restore file" variant="ghost" size="sm" onClick={onArchive} style={{ padding: "3px 6px", fontSize: 11 }}><RotateCcw size={11} /></Btn>
            : <Btn aria-label="Archive file" variant="ghost" size="sm" onClick={onArchive} style={{ padding: "3px 6px", fontSize: 11 }}><Archive size={11} /></Btn>}
          <Btn aria-label="Move to trash" variant="ghost" size="sm" onClick={onDelete} style={{ padding: "3px 6px", fontSize: 11, color: "#ef4444" }}><Trash2 size={11} /></Btn>
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

function linkedRecordHref(link: MediaLinkedRecord): string | null {
  const moduleName = link.module_name.toLowerCase();
  if (moduleName === "booking" || moduleName === "job") return "/admin/home-services/bookings-jobs?" + moduleName + "_id=" + encodeURIComponent(link.record_id);
  if (moduleName === "complaint") return "/admin/home-services/complaints/" + encodeURIComponent(link.record_id);
  if (moduleName === "provider") return "/admin/home-services/providers/" + encodeURIComponent(link.record_id);
  if (moduleName === "invoice") return "/admin/home-services/finance?tab=invoices&invoice_id=" + encodeURIComponent(link.record_id);
  return null;
}

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
    const blob = await mediaAdminApi.fetchSignedFile(signed.url);
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  });
  const { execute: execDownload } = useAction(async () => {
    const signed = await mediaAdminApi.createSignedDownloadUrl(asset.id);
    const blob = await mediaAdminApi.fetchSignedFile(signed.url);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = asset.file_name_original; a.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
  });

  const Row = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div style={{ display: "flex", gap: 8, paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 130, flexShrink: 0, fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", paddingTop: 2 }}>{label}</div>
      <div style={{ flex: 1, fontSize: 13 }}>{value ?? "—"}</div>
    </div>
  );

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1200, display: "flex" }}>
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
            <Btn aria-label={asset.status === "archived" ? "Restore file" : "Archive file"} variant="secondary" size="sm" onClick={onArchive}>
              {asset.status === "archived" ? <RotateCcw size={12} /> : <Archive size={12} />}
            </Btn>
            <Btn aria-label="Move to trash" variant="danger" size="sm" onClick={onDelete}><Trash2 size={12} /></Btn>
            <button aria-label="Close file detail" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", padding: 4 }}><X size={16} /></button>
          </div>
        </div>

        {/* Preview */}
        {asset.mime_type?.startsWith("image/") && asset.preview_url && (
          <div style={{ padding: "12px 20px", height: 244, borderBottom: "1px solid var(--border)", background: "var(--bg)", display: "grid", placeItems: "center", overflow: "hidden" }}>
            <SecureThumbnail asset={asset} fit="contain" />
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
              <Row label="Owner ID"   value={<span style={{ fontFamily: "monospace", fontSize: 11 }}>{asset.owner_id}</span>} />
              {asset.tenant_id && <Row label="Tenant ID" value={<span style={{ fontFamily: "monospace", fontSize: 11 }}>{asset.tenant_id}</span>} />}
              {asset.customer_id && <Row label="Customer ID" value={<span style={{ fontFamily: "monospace", fontSize: 11 }}>{asset.customer_id}</span>} />}
              {asset.description && <Row label="Description" value={asset.description} />}
              {asset.tags_json?.length > 0 && <Row label="Tags" value={<div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>{asset.tags_json.map((tag) => <Badge key={tag} variant="info" size="sm">{tag}</Badge>)}</div>} />}
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
                    {linkedRecordHref(l) && <button aria-label={"Open " + l.record_type} onClick={() => window.open(linkedRecordHref(l)!, "_blank", "noopener,noreferrer")} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}><ExternalLink size={12} /></button>}
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

function UploadModal({ onClose, onDone, options }: { onClose: () => void; onDone: () => void; options?: MediaFilterOptions | null }) {
  const [file, setFile]             = useState<File | null>(null);
  const [context, setContext]       = useState("marketing_asset");
  const [isPublic, setIsPublic]     = useState(false);
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadContexts = options?.upload_contexts ?? [
    { value: "marketing_asset", max_mb: 20, allowed_types: ["image/jpeg", "image/png", "image/webp", "image/gif"] },
  ];
  const contextRule = uploadContexts.find((item) => item.value === context) ?? uploadContexts[0];
  const { execute, loading, error } = useAction(async () => {
    if (!file) throw new Error("Please select a file.");
    await mediaAdminApi.uploadMedia(file, context, "admin", isPublic, description, tags.split(",").map((value) => value.trim()).filter(Boolean));
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
            onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(event) => { event.preventDefault(); setDragActive(false); setFile(event.dataTransfer.files?.[0] ?? null); }}
            style={{ border: `2px dashed ${file || dragActive ? "var(--brand)" : "var(--border)"}`, borderRadius:"var(--radius-md)", padding: "24px", textAlign: "center", cursor: "pointer", background: file || dragActive ? "var(--accent-muted)" : "var(--surface-sunken)" }}
          >
            {file ? (
              <div style={{ fontSize: 13 }}>{file.name} · {fmtBytes(file.size)}</div>
            ) : (
              <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                <Upload size={20} style={{ display: "block", margin: "0 auto 6px" }} />
                Click to select or drag and drop
                <span style={{ display: "block", fontSize: 11, marginTop: 5 }}>Files are validated and access-controlled before publication.</span>
              </div>
            )}
          </div>
          <input ref={inputRef} type="file" accept={(contextRule?.allowed_types ?? []).join(",")} style={{ display: "none" }} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Context *</label>
          <select value={context} onChange={(e) => setContext(e.target.value)} style={inp}>
            {uploadContexts.map((item) => (
              <option key={item.value} value={item.value}>{item.value.replace(/_/g, " ")}</option>
            ))}
          </select>
          <div style={{ marginTop: 5, fontSize: 11, color: "var(--text-tertiary)" }}>Up to {contextRule?.max_mb ?? 10} MB · {(contextRule?.allowed_types ?? []).map((value) => value.replace("image/", "").replace("application/", "")).join(", ")}</div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Ownership</label>
            <div style={{ ...inp, display: "flex", alignItems: "center", color: "var(--text-secondary)" }}><Shield size={13} style={{ marginRight: 7 }} /> Platform managed</div>
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
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Search tags</label>
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="catalog, campaign, policy (comma separated)" style={inp} />
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
  const { execute, loading, error } = useAction(async () => {
    if (!asset) return;
    await mediaAdminApi.deleteMedia(asset.id, false);
    onDone();
  });
  return (
    <Modal open={open} title="Move file to trash" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Move <strong>{asset?.file_name_original}</strong> to trash? The stored object is retained according to the platform retention policy.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 12 }}>{error}</div>}
      <div style={{ fontSize: 12, color: "var(--text-secondary)", padding: "10px 12px", background: "var(--surface-sunken)", borderRadius: 7, marginBottom: 16 }}>Files linked to active bookings, jobs, complaints, invoices, disputes, or compliance records cannot be trashed.</div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="danger" onClick={() => execute()} disabled={loading}>Move to trash</Btn>
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
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<Array<string | null>>([]);
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
  const { data: filterOptions } = useApi(() => mediaAdminApi.getFilterOptions(), []);
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
        sort: f.sort as "newest" | "oldest" | "largest" | "smallest",
        cursor: cursor || undefined,
        page,
        pageSize,
      });
    },
    [efKey, cursor, page, pageSize],
  );

  const refresh = useCallback(() => { reload(); reloadSummary(); setSelected(new Set()); }, [reload, reloadSummary]);

  const { execute: execArchive }   = useAction(async (a: MediaAssetAdmin) => { await mediaAdminApi.archiveMedia(a.id); refresh(); });
  const { execute: execRestore }   = useAction(async (a: MediaAssetAdmin) => { await mediaAdminApi.restoreMedia(a.id); refresh(); });
  const { execute: execMarkClean } = useAction(async (a: MediaAssetAdmin) => { await mediaAdminApi.markClean(a.id); refresh(); });
  const { execute: execPreview }  = useAction(async (a: MediaAssetAdmin) => {
    const signed = await mediaAdminApi.createSignedPreviewUrl(a.id);
    const blob = await mediaAdminApi.fetchSignedFile(signed.url);
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
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
      const blob = await mediaAdminApi.exportCsv({
        q: ef.q || undefined, context: ef.context || undefined, ownerType: ef.ownerType || undefined,
        visibility: ef.visibility || undefined, status: ef.status || undefined,
        isFlagged: ef.isFlagged === "" ? undefined : ef.isFlagged === "true",
        fileType: ef.fileType || undefined, dateFrom: ef.dateFrom || undefined,
        dateTo: ef.dateTo || undefined, sort: ef.sort,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "media_export.csv"; a.click();
    } catch { /* silent */ }
  };

  const items      = (listData?.items ?? []) as Row[];
  const total      = listData?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);
  const hasActiveFilters = Object.entries(filters).some(([key, value]) => key !== "sort" && Boolean(value));
  const emptyCopy = EMPTY_STATE_COPY[tab];

  const toggleSelect = (id: string) => {
    setSelected((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  };
  const selectAll = () => setSelected(new Set(items.map((i) => i.id as string)));
  const clearAll  = () => setSelected(new Set());

  const handleTabChange = (t: TabKey) => {
    setTab(t); setPage(1); setCursor(null); setCursorHistory([]); clearAll();
    setFilters((f) => ({ ...f, fileType: "", status: "", isFlagged: "", dateFrom: "" }));
  };

  const applyFilters = (next: Filters) => {
    setFilters(next);
    setPage(1);
    setCursor(null);
    setCursorHistory([]);
    clearAll();
  };

  const goNext = () => {
    if (!listData?.next_cursor) return;
    setCursorHistory((history) => [...history, cursor]);
    setCursor(listData.next_cursor);
    setPage((value) => value + 1);
    clearAll();
  };

  const goPrevious = () => {
    if (!cursorHistory.length) return;
    const previous = cursorHistory[cursorHistory.length - 1] ?? null;
    setCursorHistory((history) => history.slice(0, -1));
    setCursor(previous);
    setPage((value) => Math.max(1, value - 1));
    clearAll();
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
          <Btn aria-label="View details" variant="ghost" size="sm" onClick={() => setDetail(row as MediaAssetAdmin)} style={{ padding: "3px 6px" }}><Eye size={11} /></Btn>
          <Btn aria-label={(row as MediaAssetAdmin).status === "archived" ? "Restore file" : "Archive file"} variant="ghost" size="sm" onClick={() => (row as MediaAssetAdmin).status === "archived" ? execRestore(row as MediaAssetAdmin) : execArchive(row as MediaAssetAdmin)} style={{ padding: "3px 6px" }}>{(row as MediaAssetAdmin).status === "archived" ? <RotateCcw size={11} /> : <Archive size={11} />}</Btn>
          <Btn aria-label="Move to trash" variant="ghost" size="sm" onClick={() => setModal({ type: "delete", asset: row as MediaAssetAdmin })} style={{ padding: "3px 6px", color: "#ef4444" }}><Trash2 size={11} /></Btn>
        </div>
      ),
    },
  ];

  return (
    <AdminLayout>
      <div style={{ padding: "28px 32px 48px", minHeight: "100vh", maxWidth: 1680, margin: "0 auto" }}>
        {/* Header */}
        <SectionHeader
          title="Media Library"
          subtitle="Securely find, review, govern, and export files across every platform workflow"
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
        {summary && <SummaryCards s={summary} onOpenTab={handleTabChange} />}

        {/* Tabs */}
        <TabBar active={tab} onChange={handleTabChange} summary={summary ?? null} />

        {/* Search and operational results */}
        <div style={{ minWidth: 0 }}>
            {/* Toolbar */}
            <Toolbar
              filters={filters}
              onChange={applyFilters}
              viewMode={viewMode}
              onViewMode={setViewMode}
              onUpload={() => setModal({ type: "upload" })}
              options={filterOptions as MediaFilterOptions | null}
            />

            {/* Active filter chips */}
            <ActiveChips filters={filters} onChange={applyFilters} />

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
              {loading && items.length === 0 && (
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
                  <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>{emptyCopy.title}</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 400, margin: "0 auto 20px" }}>
                    {hasActiveFilters
                      ? "No files match these filters. Try changing or clearing your filters."
                      : emptyCopy.description}
                  </div>
                  {hasActiveFilters
                    ? <Btn variant="secondary" size="sm" onClick={() => applyFilters(DEFAULT_FILTERS)}>Clear Filters</Btn>
                    : emptyCopy.upload
                      ? <Btn variant="primary" size="sm" onClick={() => setModal({ type: "upload" })}><Upload size={12} /> Upload media</Btn>
                      : null
                  }
                </div>
              )}

              {/* Grid view */}
              {items.length > 0 && viewMode === "grid" && (
                <MediaGrid
                  items={items as MediaAssetAdmin[]}
                  selected={selected}
                  onSelect={toggleSelect}
                  onPreview={(a) => execPreview(a)}
                  onDetail={(a) => setDetail(a)}
                  onArchive={(a) => a.status === "archived" ? execRestore(a) : execArchive(a)}
                  onDelete={(a) => setModal({ type: "delete", asset: a })}
                  onFlag={(a) => setModal({ type: "flag", asset: a })}
                  onCopyLink={(a) => execPreview(a)}
                />
              )}

              {/* List view */}
              {items.length > 0 && viewMode === "list" && (
                <DataTable<Row>
                  columns={columns}
                  rows={items}
                  onRowClick={(row) => setDetail(row as MediaAssetAdmin)}
                />
              )}

              {/* Pagination */}
              {(cursorHistory.length > 0 || Boolean(listData?.has_next)) && (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                    Rows per page:
                    {[10, 25, 50, 100].map((n) => (
                      <button key={n} onClick={() => { setPageSize(n); setPage(1); setCursor(null); setCursorHistory([]); }} style={{ padding: "2px 8px", borderRadius: 4, border: "1px solid var(--border)", background: pageSize === n ? "var(--brand)" : "var(--surface)", color: pageSize === n ? "#fff" : "var(--text)", cursor: "pointer", fontSize: 11 }}>{n}</button>
                    ))}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page}{totalPages > 0 ? ` of ${totalPages.toLocaleString()}` : ""}</span>
                    <Btn aria-label="Previous page" variant="secondary" size="sm" disabled={!cursorHistory.length} onClick={goPrevious}><ChevronLeft size={13} /></Btn>
                    <Btn aria-label="Next page" variant="secondary" size="sm" disabled={!listData?.has_next} onClick={goNext}><ChevronRight size={13} /></Btn>
                  </div>
                </div>
              )}
            </Card>
        </div>
      </div>

      {/* Detail Drawer */}
      {detail && (
        <DetailDrawer
          asset={detail}
          onClose={() => setDetail(null)}
          onArchive={() => { detail.status === "archived" ? execRestore(detail) : execArchive(detail); setDetail(null); }}
          onFlag={() => { setModal({ type: "flag", asset: detail }); setDetail(null); }}
          onMarkClean={() => { execMarkClean(detail); }}
          onDelete={() => { setModal({ type: "delete", asset: detail }); setDetail(null); }}
        />
      )}

      {/* Modals */}
      {modal?.type === "upload" && (
        <UploadModal options={filterOptions as MediaFilterOptions | null} onClose={() => setModal(null)} onDone={() => { setModal(null); refresh(); }} />
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
