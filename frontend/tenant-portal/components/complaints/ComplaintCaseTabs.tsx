"use client";
/**
 * Conversation / Evidence / Resolution tabs for the complaint case workspace.
 *
 * These three were placeholders reading "ships in a later phase". Two of the
 * three only ever needed wiring — `/messages`, `/respond`, `/resolutions` and
 * `/offer-resolution` already existed on the secured provider router. The
 * third, Evidence, had a service method (`ComplaintService.list_media`) that
 * NO router exposed, so photos a customer attached to their complaint were
 * stored and then unreachable by the provider who needed them to judge the
 * case; that endpoint now exists.
 */
import React, { useCallback, useState } from "react";
import { Info, Send, Paperclip, FileText, ShieldCheck } from "lucide-react";
import { Badge, Skeleton, Btn } from "../shared/ui";
import {
  tenantComplaintsApi, ServiceOSError,
  type ComplaintMessageItem, type ComplaintMediaItem, type ComplaintResolutionItem,
  type ComplaintResolutionOption,
} from "../../lib/api";
import { useApi } from "../../hooks/useApi";
import { statusLabel } from "./ComplaintQueueList";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

const SENDER_LABEL: Record<string, string> = {
  customer: "Customer", provider: "You", admin: "Fuvay Admin",
  staff: "Your staff", system: "System", ai: "System",
};

const fieldStyle: React.CSSProperties = {
  width: "100%", height: 36, padding: "0 10px", fontSize: 13,
  background: "var(--surface-sunken)", border: "1px solid var(--border)",
  borderRadius: 8, color: "var(--text-primary)", fontFamily: "inherit", boxSizing: "border-box",
};

/* ── Conversation ─────────────────────────────────────────────────────────── */

export function ConversationTab({ complaintId, canReply }: { complaintId: string; canReply: boolean }) {
  const thread = useApi(useCallback(() => tenantComplaintsApi.messages(complaintId), [complaintId]));
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messages: ComplaintMessageItem[] = Array.isArray(thread.data) ? thread.data : [];

  async function send() {
    const body = text.trim();
    if (!body) return;
    setSending(true);
    setError(null);
    try {
      await tenantComplaintsApi.respond(complaintId, body);
      setText("");
      thread.refetch();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Your reply could not be sent.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {thread.loading ? <Skeleton height={160}/> : messages.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
          No messages on this case yet. Your reply is the first thing the customer will see.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {messages.map(m => {
            const mine = m.sender_type === "provider";
            return (
              <div key={m.id} style={{ display: "flex", justifyContent: mine ? "flex-end" : "flex-start" }}>
                <div style={{
                  maxWidth: "78%", padding: "10px 12px", borderRadius: 10,
                  background: mine ? "var(--accent-muted)" : "var(--surface-sunken)",
                  border: `1px solid ${mine ? "var(--brand)" : "var(--border)"}`,
                }}>
                  <p style={{
                    fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em",
                    color: mine ? "var(--brand)" : "var(--text-tertiary)", margin: "0 0 4px",
                  }}>
                    {SENDER_LABEL[m.sender_type] ?? m.sender_type}
                  </p>
                  <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                    {m.message_text}
                  </p>
                  <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "6px 0 0" }}>{fmtDate(m.created_at)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {canReply ? (
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          <label htmlFor="cmp-reply" style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
            Reply to the customer
          </label>
          <textarea
            id="cmp-reply" rows={3} value={text}
            onChange={e => setText(e.target.value.slice(0, 4000))}
            placeholder="Acknowledge the issue and say what you will do next…"
            style={{
              width: "100%", padding: 10, fontSize: 13, background: "var(--surface-sunken)",
              border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)",
              resize: "vertical", fontFamily: "inherit", boxSizing: "border-box",
            }}
          />
          {error && <p role="alert" style={{ fontSize: 12, color: "var(--danger-text)", margin: "6px 0 0" }}>{error}</p>}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{text.length} / 4000 · visible to the customer</span>
            <Btn variant="primary" size="sm" icon={<Send size={12}/>} loading={sending} disabled={!text.trim()} onClick={send}>
              Send reply
            </Btn>
          </div>
        </div>
      ) : (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          This case is closed — no further replies can be sent.
        </p>
      )}
    </div>
  );
}

/* ── Evidence ─────────────────────────────────────────────────────────────── */

function isImage(m: ComplaintMediaItem) {
  return m.media_type === "image" || (m.mime_type ?? "").startsWith("image/");
}
function fmtBytes(n: number | null) {
  if (!n) return "";
  return n < 1024 * 1024 ? `${Math.round(n / 1024)} KB` : `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function EvidenceTab({ complaintId }: { complaintId: string }) {
  const media = useApi(useCallback(() => tenantComplaintsApi.evidence(complaintId), [complaintId]));
  const items: ComplaintMediaItem[] = media.data?.items ?? [];

  if (media.loading) return <Skeleton height={140}/>;
  if (items.length === 0) {
    return (
      <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
        No photos or documents have been attached to this case.
      </p>
    );
  }
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12 }}>
      {items.map(m => (
        <a
          key={m.id} href={m.file_url} target="_blank" rel="noopener noreferrer"
          style={{ textDecoration: "none", border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden", background: "var(--surface-sunken)" }}
        >
          {isImage(m) ? (
            <img
              src={m.file_url} alt={m.caption ?? m.file_name ?? "Case evidence"}
              style={{ width: "100%", height: 110, objectFit: "cover", display: "block" }}
            />
          ) : (
            <div style={{ height: 110, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <FileText size={26} style={{ color: "var(--text-tertiary)" }}/>
            </div>
          )}
          <div style={{ padding: "8px 10px" }}>
            <p style={{ fontSize: 11.5, color: "var(--text-primary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {m.caption || m.file_name || "Attachment"}
            </p>
            <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "2px 0 0", display: "flex", alignItems: "center", gap: 4 }}>
              <Paperclip size={9}/>{SENDER_LABEL[m.uploaded_by_type] ?? m.uploaded_by_type}
              {fmtBytes(m.file_size) ? ` · ${fmtBytes(m.file_size)}` : ""}
            </p>
          </div>
        </a>
      ))}
    </div>
  );
}

/* ── Resolution ───────────────────────────────────────────────────────────── */

/** Labels for offers already on a case, including types older cases may
 *  carry. What can be offered NOW comes from the server (`options`): the list
 *  used to be hardcoded here and included "partial_refund" and "credit",
 *  which the engine never modelled -- accepting them resolved the case with
 *  no remedy at all. */
const RESOLUTION_LABELS: Record<string, string> = {
  rework: "Free rework visit", refund: "Refund", callback: "Callback",
  apology: "Apology / goodwill", no_action: "No action required",
  partial_refund: "Partial refund", credit: "Service credit",
  provider_reassignment: "Reassign provider",
};

export function ResolutionTab({ complaintId, options, canOffer, blockedReason, onChanged }: {
  complaintId: string; options: ComplaintResolutionOption[]; canOffer: boolean;
  blockedReason: string | null; onChanged: () => void;
}) {
  const list = useApi(useCallback(() => tenantComplaintsApi.resolutions(complaintId), [complaintId]));
  const [type, setType] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const offers: ComplaintResolutionItem[] = Array.isArray(list.data) ? list.data : [];
  const selected = options.find(o => o.value === type) ?? options[0];
  const amountValue = Number(amount);
  const amountValid = !selected?.requires_amount || (amount.trim() !== "" && Number.isFinite(amountValue) && amountValue > 0);

  async function submit() {
    if (!description.trim() || !selected || !amountValid) return;
    setSaving(true);
    setError(null);
    try {
      await tenantComplaintsApi.offerResolution(complaintId, {
        resolution_type: selected.value,
        description: description.trim(),
        customer_visible_notes: notes.trim() || undefined,
        ...(selected.requires_amount ? { amount: amountValue } : {}),
      });
      setDescription("");
      setNotes("");
      setAmount("");
      list.refetch();
      onChanged();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "The resolution could not be proposed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {list.loading ? <Skeleton height={80}/> : offers.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: 0 }}>
            Proposed resolutions
          </p>
          {offers.map(o => (
            <div key={o.id} style={{ padding: 12, borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)" }}>
                  {RESOLUTION_LABELS[o.resolution_type] ?? o.resolution_type.replace(/_/g, " ")}
                  {o.amount ? ` · ₹${Number(o.amount).toLocaleString("en-IN")}` : ""}
                </span>
                <Badge
                  variant={o.status === "customer_accepted" ? "success" : o.status === "customer_rejected" ? "danger" : "warning"}
                  size="sm"
                >
                  {statusLabel(o.status)}
                </Badge>
              </div>
              <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0, lineHeight: 1.5 }}>{o.description}</p>
              {o.customer_visible_notes && (
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "6px 0 0" }}>{o.customer_visible_notes}</p>
              )}
              <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "6px 0 0" }}>{fmtDate(o.created_at)}</p>
            </div>
          ))}
        </div>
      )}

      {canOffer && selected ? (
        <div style={{ borderTop: offers.length ? "1px solid var(--border)" : "none", paddingTop: offers.length ? 14 : 0 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 10px" }}>
            Propose a resolution
          </p>
          <div style={{ display: "grid", gap: 10 }}>
            <label style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Resolution type</span>
              <select value={selected.value} onChange={e => setType(e.target.value)} style={fieldStyle}>
                {options.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </label>
            {selected.requires_amount && (
              <label style={{ display: "block" }}>
                <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
                  Refund amount (₹)
                </span>
                <input
                  type="number" min="1" step="0.01" inputMode="decimal" value={amount}
                  onChange={e => setAmount(e.target.value)} style={fieldStyle}
                  aria-describedby="cmp-refund-help"
                />
                <span id="cmp-refund-help" style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
                  If the customer accepts, this becomes an approved refund you record under Refunds &amp; Warranty.
                </span>
              </label>
            )}
            <label style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>What you will do</span>
              <textarea
                rows={3} value={description} onChange={e => setDescription(e.target.value.slice(0, 2000))}
                placeholder="Describe the remedy you are offering…"
                style={{ ...fieldStyle, height: "auto", padding: 10, resize: "vertical" }}
              />
            </label>
            <label style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Note to the customer (optional)</span>
              <textarea
                rows={2} value={notes} onChange={e => setNotes(e.target.value.slice(0, 1000))}
                style={{ ...fieldStyle, height: "auto", padding: 10, resize: "vertical" }}
              />
            </label>
          </div>
          {error && <p role="alert" style={{ fontSize: 12, color: "var(--danger-text)", margin: "8px 0 0" }}>{error}</p>}
          <Btn
            variant="primary" size="sm" icon={<ShieldCheck size={12}/>} loading={saving}
            disabled={!description.trim() || !amountValid} onClick={submit} style={{ marginTop: 10 }}
          >
            Propose resolution
          </Btn>
        </div>
      ) : blockedReason ? (
        <div style={{
          display: "flex", gap: 8, padding: "12px 14px", borderRadius: 8,
          background: "var(--surface-sunken)", border: "1px solid var(--border)",
        }}>
          <Info size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }}/>
          <span style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>{blockedReason}</span>
        </div>
      ) : null}
    </div>
  );
}
