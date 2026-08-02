"use client";
import { useCallback, useRef, useState } from "react";
import { providerChatApi, mediaAssetApi, friendlyMediaError, type ProviderChatThread, type ProviderChatMessage, type ServiceOSError } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Paperclip, X, Loader2 } from "lucide-react";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  open:     { background: "var(--success-bg)",     color: "var(--success-text)" },
  closed:   { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  archived: { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
};

export default function ProviderChatPage() {
  const [selectedThread, setSelectedThread] = useState<ProviderChatThread | null>(null);
  const [messages, setMessages] = useState<ProviderChatMessage[]>([]);
  const [newMsg,         setNewMsg]         = useState("");
  const [pendingFile,    setPendingFile]    = useState<File | null>(null);
  const [uploading,      setUploading]      = useState(false);
  const [attachError,    setAttachError]    = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const threads = useApi(useCallback(() => providerChatApi.listThreads({ limit: 50 }), []));

  const sendAction = useAction(
    useCallback(
      (threadId: string, text: string, mediaIds?: string[]) => providerChatApi.sendMessage(threadId, text, mediaIds),
      []
    )
  );

  async function openThread(thread: ProviderChatThread) {
    setSelectedThread(thread);
    loadMessages(thread.id);
    await providerChatApi.markThreadRead(thread.id).catch(() => {});
  }

  async function loadMessages(threadId: string) {
    const res = await providerChatApi.listMessages(threadId, { limit: 100 });
    setMessages(res.items ?? []);
  }

  async function handleSend() {
    if (!selectedThread) return;
    setAttachError("");
    let mediaIds: string[] | undefined;

    if (pendingFile) {
      setUploading(true);
      try {
        const asset = await mediaAssetApi.upload(
          "chat_attachment", "user", selectedThread.id, pendingFile
        );
        mediaIds = [asset.id];
      } catch (e) {
        const code = (e as ServiceOSError).code ?? "";
        setAttachError(friendlyMediaError(code) || "File upload failed. Please try again.");
        setUploading(false);
        return;
      } finally {
        setUploading(false);
      }
    }

    const text = newMsg.trim() || (pendingFile ? `📎 ${pendingFile.name}` : "");
    await sendAction.execute(selectedThread.id, text, mediaIds).then(() => {
      setNewMsg("");
      setPendingFile(null);
      loadMessages(selectedThread.id);
    });
  }

  const items: ProviderChatThread[] = threads.data?.items ?? [];

  return (
    <div style={{ display: "flex", height: "calc(100vh - 64px)" }}>
      {/* Thread list */}
      <div style={{ width: 288, borderRight: "1px solid var(--border)", background: "var(--surface)", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: 16, borderBottom: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>Chat Threads</h2>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{items.length} threads</p>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {threads.loading ? (
            <div style={{ padding: 16, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
          ) : items.length === 0 ? (
            <div style={{ padding: 16, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No threads yet</div>
          ) : (
            items.map(t => (
              <button key={t.id} onClick={() => openThread(t)} style={{
                width: "100%", textAlign: "left", padding: "12px 16px",
                borderBottom: "1px solid var(--border)", background: selectedThread?.id === t.id ? "var(--info-bg)" : "transparent",
                borderLeft: selectedThread?.id === t.id ? "2px solid var(--brand)" : "2px solid transparent",
                cursor: "pointer", fontFamily: "inherit",
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, color: "var(--text-primary)" }}>
                    {t.thread_number}
                  </span>
                  <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, fontWeight: 600,
                    ...(STATUS_STYLE[t.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                    {t.status}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{t.record_type}</div>
                <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2 }}>
                  {t.last_message_at ? t.last_message_at.replace("T", " ").slice(0, 16) : "No messages"}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Message panel */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "var(--bg)" }}>
        {!selectedThread ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-tertiary)" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>💬</div>
              <p style={{ fontSize: 13 }}>Select a thread to view messages</p>
            </div>
          </div>
        ) : (
          <>
            <div style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", padding: "12px 16px" }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{selectedThread.thread_number}</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                {selectedThread.record_type} · {selectedThread.record_id.slice(0, 8)}…
                <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, fontWeight: 600,
                  ...(STATUS_STYLE[selectedThread.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                  {selectedThread.status}
                </span>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
              {messages.length === 0 ? (
                <div style={{ textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, padding: "32px 0" }}>No messages yet</div>
              ) : (
                messages.map(msg => {
                  const isOwn = msg.sender_type === "provider" || msg.sender_type === "staff";
                  const isSystem = msg.sender_type === "system";
                  return (
                    <div key={msg.id} style={{ display: "flex", justifyContent: isOwn ? "flex-end" : isSystem ? "center" : "flex-start" }}>
                      <div style={{
                        maxWidth: 280, borderRadius: 10, padding: "8px 12px", fontSize: 13,
                        background: isSystem ? "var(--surface-sunken)" : isOwn ? "var(--brand)" : "var(--surface)",
                        color: isSystem ? "var(--text-tertiary)" : isOwn ? "white" : "var(--text-primary)",
                        border: isSystem || isOwn ? "none" : "1px solid var(--border)",
                      }}>
                        {!isSystem && (
                          <div style={{ fontSize: 10, marginBottom: 4, textTransform: "capitalize",
                            color: isOwn ? "rgba(255,255,255,0.7)" : "var(--text-tertiary)" }}>
                            {msg.sender_type}
                          </div>
                        )}
                        {msg.message_text && <span>{msg.message_text}</span>}
                        {msg.media_urls?.media_ids?.map(mid => (
                          <a key={mid} href={mediaAssetApi.viewUrl(mid)} target="_blank" rel="noopener noreferrer"
                            style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 4,
                              fontSize: 12, color: isOwn ? "rgba(255,255,255,0.85)" : "var(--accent)",
                              textDecoration: "none" }}>
                            <Paperclip size={11}/> View attachment
                          </a>
                        ))}
                        <div style={{ fontSize: 10, marginTop: 4,
                          color: isOwn ? "rgba(255,255,255,0.6)" : "var(--text-tertiary)" }}>
                          {msg.created_at.replace("T", " ").slice(11, 16)}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            {selectedThread.status === "open" ? (
              <div style={{ background: "var(--surface)", borderTop: "1px solid var(--border)", padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                {/* Pending attachment preview */}
                {pendingFile && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px",
                    background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius:"var(--radius-md)", fontSize: 12 }}>
                    <Paperclip size={13} style={{ color: "var(--info-text)", flexShrink: 0 }}/>
                    <span style={{ flex: 1, color: "var(--info-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {pendingFile.name}
                    </span>
                    <button onClick={() => { setPendingFile(null); setAttachError(""); }}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: 0, color: "var(--info-text)", display: "flex" }}>
                      <X size={13}/>
                    </button>
                  </div>
                )}
                {attachError && (
                  <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{attachError}</p>
                )}

                <div style={{ display: "flex", gap: 8 }}>
                  {/* Attachment button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    title="Attach file"
                    style={{ width: 36, height: 36, borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
                      background: pendingFile ? "var(--info-bg)" : "var(--surface)",
                      cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                      color: pendingFile ? "var(--info-text)" : "var(--text-secondary)", flexShrink: 0 }}>
                    <Paperclip size={15}/>
                  </button>
                  <input ref={fileInputRef} type="file"
                    accept="image/*,application/pdf,.doc,.docx,.txt"
                    style={{ display: "none" }}
                    onChange={e => {
                      const f = e.target.files?.[0];
                      if (f) { setPendingFile(f); setAttachError(""); }
                      e.target.value = "";
                    }}/>

                  <input
                    style={{ flex: 1, height: 36, padding: "0 12px", fontSize: 13, borderRadius:"var(--radius-md)",
                      border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit" }}
                    placeholder={pendingFile ? "Add a caption (optional)…" : "Type a message…"}
                    value={newMsg}
                    onChange={e => setNewMsg(e.target.value)}
                    onKeyDown={async e => {
                      if (e.key === "Enter" && !e.shiftKey && (newMsg.trim() || pendingFile)) {
                        e.preventDefault();
                        await handleSend();
                      }
                    }}
                  />
                  <button
                    onClick={handleSend}
                    disabled={(!newMsg.trim() && !pendingFile) || sendAction.loading || uploading}
                    style={{ padding: "0 16px", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)",
                      border: "none", background: "var(--brand)", color: "white",
                      cursor: (!newMsg.trim() && !pendingFile) || sendAction.loading || uploading ? "not-allowed" : "pointer",
                      opacity: (!newMsg.trim() && !pendingFile) || sendAction.loading || uploading ? 0.5 : 1,
                      fontFamily: "inherit", display: "flex", alignItems: "center", gap: 6 }}>
                    {(sendAction.loading || uploading) && <Loader2 size={13} style={{ animation: "spin 1s linear infinite" }}/>}
                    Send
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ background: "var(--surface-sunken)", borderTop: "1px solid var(--border)",
                padding: "12px 16px", fontSize: 13, color: "var(--text-tertiary)", textAlign: "center" }}>
                Thread is {selectedThread.status} — no new messages can be sent.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
