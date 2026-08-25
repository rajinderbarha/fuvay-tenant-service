"use client";
import React, { useCallback, useMemo, useRef, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { mediaApi, mediaAssetApi, getTenantId, type MediaAsset, type MediaQuota } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  Upload, HardDrive, FolderOpen, Cloud, Image, FileText, Film, Paperclip,
  Eye, Trash2, ShieldAlert, Infinity as InfinityIcon,
} from "lucide-react";
import { PageHeader, Card, Button, Skeleton, Alert } from "@serviceos/design-system";

/**
 * Media Vault.
 *
 * Reads the CANONICAL media store (`/v1/media`, the Phase 0A asset engine) —
 * the same records every other surface writes (business logo, staff profile
 * photos, provider documents, job before/after photos) and the only store the
 * super-admin media console governs.
 *
 * It previously read `/v1/media/tenants/{id}/files`, a second, parallel store
 * (`media_files`) that nothing else in the product writes. The consequence was
 * not cosmetic: this tenant has 14 real assets totalling ~1.5 MB and the vault
 * showed an empty page, while anything uploaded here would have been invisible
 * to admin governance (scan, quarantine, flag).
 */

const PAGE_SIZE = 50;

/** Contexts a person can upload INTO from the vault. Everything else is written
 *  by the surface that owns it (a job photo belongs to a job), so offering them
 *  here would create orphans. */
const UPLOADABLE_CONTEXTS = [
  { value: "provider_document", label: "Business document" },
  { value: "provider_business_logo", label: "Business logo" },
] as const;

const CONTEXT_LABELS: Record<string, string> = {
  provider_document: "Business document",
  provider_business_logo: "Business logo",
  provider_shop: "Shop / cover photo",
  staff_profile_photo: "Staff photo",
  job_before_photo: "Job — before",
  job_after_photo: "Job — after",
  complaint_evidence: "Complaint evidence",
};

const contextLabel = (c: string) =>
  CONTEXT_LABELS[c] ?? c.replace(/_/g, " ").replace(/^\w/, m => m.toUpperCase());

function fmtBytes(b: number | null | undefined) {
  if (b == null || Number.isNaN(b)) return "—";
  if (b >= 1e9) return `${(b / 1e9).toFixed(1)} GB`;
  if (b >= 1e6) return `${(b / 1e6).toFixed(1)} MB`;
  if (b >= 1e3) return `${(b / 1e3).toFixed(0)} KB`;
  return `${b} B`;
}

function StatTile({ label, value, sub, icon, alert }: {
  label: string; value: string | number; sub: string; icon: React.ReactNode; alert?: boolean;
}) {
  return (
    <Card padding="md">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
        <span style={{ color: alert ? "var(--danger-text)" : "var(--text-tertiary)" }}>{icon}</span>
      </div>
      <p style={{ fontSize: 22, fontWeight: 800, color: alert ? "var(--danger-text)" : "var(--text-primary)", margin: 0 }}>{value}</p>
      <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "4px 0 0" }}>{sub}</p>
    </Card>
  );
}

export default function MediaPage() {
  // `media_context` is a filter the endpoint really declares, so this refetches
  // server-side rather than slicing one client-side page.
  const [context, setContext] = useState<string>("");
  const [uploadContext, setUploadContext] = useState<string>(UPLOADABLE_CONTEXTS[0].value);

  const assets = useApi(
    useCallback(
      () => mediaAssetApi.listAssets({
        page: 1, page_size: PAGE_SIZE,
        ...(context ? { media_context: context } : {}),
      }),
      [context],
    ),
    [context],
  );
  const quota = useApi(() => mediaApi.getQuota(), []);

  const [toast, setToast] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const deleteAsset = useAction(async (assetId: string) => {
    await mediaAssetApi.delete(assetId);
    await assets.refetch();
    await quota.refetch();
    notify("File deleted.");
  });

  /**
   * Upload goes through the asset engine's server-side multipart endpoint.
   *
   * The old vault used a presigned direct-to-storage flow and PUT the raw file
   * at the upload URL while ignoring the signed `upload_params` it was handed —
   * which the storage provider rejected outright ("Upload preset must be
   * specified when using unsigned upload"). Uploading from this page could
   * never have succeeded.
   */
  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const tenantId = getTenantId();
    if (!tenantId) { setUploadError("We couldn't identify your business. Please sign in again."); return; }

    setUploading(true);
    setUploadError("");
    try {
      // Business logos are public by design (they appear to customers);
      // documents are private.
      const isPublic = uploadContext === "provider_business_logo";
      await mediaAssetApi.upload(uploadContext, "tenant", tenantId, file, isPublic);
      await assets.refetch();
      await quota.refetch();
      notify(`${file.name} uploaded.`);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, [uploadContext, assets, quota]);

  const q = quota.data as MediaQuota | null;

  // `unlimited` is a real state (home services is quota-exempt), not "zero
  // allowed" — dividing by a null quota is what rendered NaN in these tiles.
  const unlimited = !!q?.unlimited || q?.quota_bytes == null;
  const usedPct = q && !unlimited ? Math.round(q.usage_pct ?? 0) : 0;
  const freeBytes = q && !unlimited && q.quota_bytes != null
    ? Math.max(0, q.quota_bytes - q.used_bytes)
    : null;

  const items = useMemo(() => assets.data?.items ?? [], [assets.data]);

  // Facets come from what is actually in the vault, so a chip can never be a
  // dead end.
  const contexts = useMemo(() => {
    const seen = new Map<string, number>();
    items.forEach(a => seen.set(a.media_context, (seen.get(a.media_context) ?? 0) + 1));
    return [...seen.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const iconFor = (mime: string): React.ReactNode => {
    if (mime?.startsWith("image/")) return <Image size={44} />;
    if (mime === "application/pdf") return <FileText size={44} />;
    if (mime?.startsWith("video/")) return <Film size={44} />;
    return <Paperclip size={44} />;
  };

  return (
    <TenantLayout activeNav="media">
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        <PageHeader
          title="Media Vault"
          description="Every file your business has uploaded — logos, documents, staff photos and job evidence"
          actions={
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <select
                value={uploadContext}
                onChange={e => setUploadContext(e.target.value)}
                aria-label="What are you uploading?"
                style={{
                  padding: "6px 12px", border: "1px solid var(--border)", borderRadius: 9,
                  background: "var(--surface)", color: "var(--text-primary)", fontSize: 13,
                  height: 36, outline: "none", cursor: "pointer",
                }}>
                {UPLOADABLE_CONTEXTS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              <Button size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading} leftIcon={<Upload size={14} />}>
                Upload file
              </Button>
              <input ref={fileInputRef} type="file" style={{ display: "none" }}
                onChange={handleUpload} accept="image/*,application/pdf,video/*" />
            </div>
          }
        />

        {toast && <Alert tone="success">{toast}</Alert>}
        {uploadError && <Alert tone="danger">{uploadError}</Alert>}
        {assets.error && <Alert tone="danger">We couldn&apos;t load your files. {String(assets.error)}</Alert>}

        {/* Storage */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          {quota.loading ? (
            [...Array(3)].map((_, i) => <Skeleton key={i} height="6.5rem" radius="12px" />)
          ) : !q ? null : <>
            <StatTile
              label="Storage used"
              value={fmtBytes(q.used_bytes)}
              sub={unlimited ? "No storage cap on your plan" : `of ${fmtBytes(q.quota_bytes)} included`}
              icon={<HardDrive size={16} />}
              alert={!unlimited && q.alert}
            />
            <StatTile
              label="Files stored"
              value={q.file_count}
              sub={q.file_count === 1 ? "file in the vault" : "files in the vault"}
              icon={<FolderOpen size={16} />}
            />
            <StatTile
              label={unlimited ? "Plan" : "Free space"}
              value={unlimited ? "Unlimited" : fmtBytes(freeBytes)}
              sub={unlimited ? "Home services is not storage-capped" : `${Math.max(0, 100 - usedPct)}% remaining`}
              icon={unlimited ? <InfinityIcon size={16} /> : <Cloud size={16} />}
              alert={!unlimited && usedPct > 90}
            />
          </>}
        </div>

        {/* A usage bar is meaningless without a cap, so it is omitted for an
            unlimited plan rather than pinned at 0% forever. */}
        {q && !unlimited && (
          <Card padding="md">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Storage usage</span>
              <span style={{
                fontSize: 12, fontWeight: 700,
                color: usedPct > 90 ? "var(--danger-text)" : usedPct > 70 ? "var(--warning-text)" : "var(--success-text)",
              }}>{usedPct}%</span>
            </div>
            <div style={{ background: "var(--surface-sunken)", borderRadius: 999, height: 8, overflow: "hidden" }}>
              <div style={{
                height: "100%", width: `${Math.min(100, usedPct)}%`, borderRadius: 999,
                background: usedPct > 90 ? "var(--danger)" : usedPct > 70 ? "var(--warning)" : "var(--brand)",
                transition: "width 0.4s ease",
              }} />
            </div>
            {usedPct > 85 && (
              <p style={{ margin: "10px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
                Running low. Upgrade your package for more storage.
              </p>
            )}
          </Card>
        )}

        {/* Context filter — server-side, so it searches the whole vault rather
            than the current page. */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button variant={context === "" ? "primary" : "secondary"} size="sm" onClick={() => setContext("")}>
            All files
          </Button>
          {contexts.map(([c, n]) => (
            <Button key={c} variant={context === c ? "primary" : "secondary"} size="sm" onClick={() => setContext(c)}>
              {contextLabel(c)} {context === "" ? `(${n})` : ""}
            </Button>
          ))}
        </div>

        {/* Files */}
        <Card padding="md">
          {assets.loading ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px,1fr))", gap: 12 }}>
              {[...Array(8)].map((_, i) => (
                <div key={i} style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
                  <Skeleton height="7.5rem" radius="0" />
                  <div style={{ padding: "10px 12px" }}>
                    <Skeleton height="0.75rem" width="80%" />
                    <div style={{ marginTop: 6 }}><Skeleton height="0.625rem" width="50%" /></div>
                  </div>
                </div>
              ))}
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: "center", padding: 56 }}>
              <div style={{ display: "flex", justifyContent: "center", color: "var(--text-tertiary)", margin: "0 0 10px" }}>
                <FolderOpen size={42} />
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: 14, fontWeight: 500 }}>
                {context ? `No ${contextLabel(context).toLowerCase()} files.` : "No files yet."}
              </p>
              <p style={{ color: "var(--text-tertiary)", fontSize: 13, margin: "4px 0 16px" }}>
                {context ? "Try another category, or upload a new file." : "Upload your first file using the button above."}
              </p>
              {context
                ? <Button size="sm" variant="secondary" onClick={() => setContext("")}>Show all files</Button>
                : <Button size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading} leftIcon={<Upload size={14} />}>Upload file</Button>}
            </div>
          ) : (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px,1fr))", gap: 12 }}>
                {items.map((a: MediaAsset) => (
                  <AssetCard key={a.id} asset={a}
                    onDelete={() => deleteAsset.execute(a.id)}
                    deleting={deleteAsset.loading}
                    iconFor={iconFor}
                  />
                ))}
              </div>
              {(assets.data?.total ?? 0) > items.length && (
                <p style={{ marginTop: 14, fontSize: 12, color: "var(--text-tertiary)", textAlign: "center" }}>
                  Showing {items.length} of {assets.data?.total} files.
                </p>
              )}
            </>
          )}
        </Card>
      </div>
    </TenantLayout>
  );
}

function AssetCard({ asset, onDelete, deleting, iconFor }: {
  asset: MediaAsset;
  onDelete: () => void;
  deleting: boolean;
  iconFor: (mime: string) => React.ReactNode;
}) {
  const [hov, setHov] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);
  const mime = asset.mime_type ?? "";
  const url = asset.preview_url ?? null;
  const quarantined = asset.status === "quarantined";
  const archived = asset.status === "archived";
  const canPreview = mime.startsWith("image/") && !!url && !imgFailed && !quarantined;

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        border: `1px solid ${hov ? "var(--border-strong)" : "var(--border)"}`,
        borderRadius: "var(--radius-lg)", overflow: "hidden", display: "flex", flexDirection: "column",
        transition: "all 0.15s", boxShadow: hov ? "var(--shadow-md)" : "var(--shadow-sm)",
        transform: hov ? "translateY(-1px)" : "none",
        opacity: archived ? 0.65 : 1,
      }}>
      <div style={{
        height: 130, background: "var(--surface-sunken)",
        display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden",
      }}>
        {canPreview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url as string} alt={asset.file_name_original}
            onError={() => setImgFailed(true)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          <span style={{ color: "var(--text-tertiary)", display: "flex" }}>{iconFor(mime)}</span>
        )}
      </div>

      <div style={{ padding: "10px 12px", flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
        <p title={asset.file_name_original} style={{
          margin: 0, fontSize: 13, fontWeight: 600, whiteSpace: "nowrap",
          overflow: "hidden", textOverflow: "ellipsis", color: "var(--text-primary)",
        }}>
          {asset.file_name_original}
        </p>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
            background: "var(--surface-sunken)", color: "var(--text-secondary)", border: "1px solid var(--border)",
          }}>
            {contextLabel(asset.media_context)}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{fmtBytes(asset.file_size_bytes)}</span>
        </div>
        {/* Governance state the admin console can set, which the tenant could
            not see at all before. */}
        {quarantined && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--danger-text)" }}>
            <ShieldAlert size={12} /> Quarantined by the platform
          </span>
        )}
        {archived && (
          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Archived</span>
        )}
        <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
          {new Date(asset.created_at).toLocaleDateString()}
        </p>
      </div>

      <div style={{
        padding: "8px 12px", borderTop: "1px solid var(--border)",
        display: "flex", gap: 6, alignItems: "center",
      }}>
        {url && !quarantined ? (
          <a href={url} target="_blank" rel="noopener noreferrer" style={{ flex: 1 }}>
            <Button variant="secondary" size="sm" leftIcon={<Eye size={13} />} style={{ width: "100%", justifyContent: "center" }}>View</Button>
          </a>
        ) : (
          <span style={{ flex: 1, fontSize: 11, color: "var(--text-tertiary)" }}>
            {quarantined ? "Blocked by the platform" : "No preview available"}
          </span>
        )}
        <Button variant="icon" size="sm" aria-label={deleting ? "Deleting…" : "Delete file"} onClick={onDelete}>
          <Trash2 size={13} />
        </Button>
      </div>
    </div>
  );
}
