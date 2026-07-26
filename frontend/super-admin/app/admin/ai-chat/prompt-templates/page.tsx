"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Skeleton, Input, Modal } from "../../../../components/shared/ui";
import { Bot, ChevronLeft, Plus, Edit2, CheckCircle, XCircle } from "lucide-react";
import { adminAIChatApi, AIPromptTemplate } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import Link from "next/link";

type TemplateCategory = "system" | "workflow" | "safety" | "context";

const CATEGORY_VARIANT: Record<TemplateCategory, "info" | "success" | "danger" | "warning"> = {
  system:   "info",
  workflow: "success",
  safety:   "danger",
  context:  "warning",
};

function TemplateModal({
  tmpl,
  onClose,
  onSaved,
}: {
  tmpl: AIPromptTemplate | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(tmpl);
  const [key,     setKey]     = useState(tmpl?.template_key ?? "");
  const [name,    setName]    = useState(tmpl?.name ?? "");
  const [desc,    setDesc]    = useState(tmpl?.description ?? "");
  const [cat,     setCat]     = useState<TemplateCategory>(tmpl?.category ?? "system");
  const [content, setContent] = useState(tmpl?.template_content ?? "");
  const [active,  setActive]  = useState(tmpl?.is_active ?? true);

  const saveAction = useAction(useCallback(
    (data: Partial<AIPromptTemplate>) =>
      isEdit
        ? adminAIChatApi.updateTemplate(tmpl!.template_key, data)
        : adminAIChatApi.createTemplate(data),
    [isEdit, tmpl]
  ));

  async function handleSave() {
    const payload: Partial<AIPromptTemplate> = {
      template_key:     key,
      name,
      description:      desc || undefined,
      category:         cat,
      template_content: content,
      is_active:        active,
    };
    await saveAction.execute(payload);
    if (!saveAction.error) {
      onSaved();
      onClose();
    }
  }

  return (
    <Modal open onClose={onClose} title={isEdit ? `Edit: ${tmpl!.template_key}` : "New Prompt Template"}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {saveAction.error && (
          <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", padding: 12, color: "var(--danger-text)", fontSize: 13 }}>
            {saveAction.error}
          </div>
        )}
        {!isEdit && (
          <div>
            <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
              Template Key (unique, snake_case)
            </label>
            <Input value={key} onChange={v => setKey(v)} placeholder="my_prompt_key" />
          </div>
        )}
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Name</label>
          <Input value={name} onChange={v => setName(v)} />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Description</label>
          <Input value={desc} onChange={v => setDesc(v)} />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Category</label>
          <select
            value={cat}
            onChange={e => setCat(e.target.value as TemplateCategory)}
            style={{
              width: "100%", border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
              padding: "8px 12px", fontSize: 13, background: "var(--surface-sunken)",
              color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
            }}
          >
            {(["system", "workflow", "safety", "context"] as TemplateCategory[]).map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Template Content</label>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            rows={10}
            style={{
              width: "100%", border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
              padding: "8px 12px", fontSize: 12, fontFamily: "monospace",
              background: "var(--surface-sunken)", color: "var(--text-primary)",
              outline: "none", resize: "vertical", boxSizing: "border-box",
            }}
          />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            id="active"
            checked={active}
            onChange={e => setActive(e.target.checked)}
            style={{ accentColor: "var(--brand)" }}
          />
          <label htmlFor="active" style={{ fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>Active</label>
        </div>
        <div style={{ display: "flex", gap: 12, paddingTop: 4 }}>
          <Btn onClick={handleSave} loading={saveAction.loading} style={{ flex: 1 }}>
            {isEdit ? "Save Changes" : "Create Template"}
          </Btn>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
        </div>
      </div>
    </Modal>
  );
}

export default function PromptTemplatesPage() {
  const [editTmpl,   setEditTmpl]   = useState<AIPromptTemplate | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [activeOnly, setActiveOnly] = useState(true);
  const [catFilter,  setCatFilter]  = useState("");

  const templates = useApi(useCallback(
    () => adminAIChatApi.listTemplates({ category: catFilter || undefined, active_only: activeOnly }),
    [catFilter, activeOnly]
  ));
  const tmpls: AIPromptTemplate[] = templates.data?.templates ?? [];

  const filterBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
    border: active ? "1px solid var(--brand)" : "1px solid var(--border)",
    background: active ? "var(--brand)" : "var(--surface)",
    color: active ? "#fff" : "var(--text-secondary)",
    transition: "all 0.12s", fontFamily: "inherit",
  });

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/admin/ai-chat">
            <button style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
              <ChevronLeft size={20} />
            </button>
          </Link>
          <SectionHeader
            title="Prompt Templates"
            subtitle={`${tmpls.length} templates`}
            icon={<Bot size={20} />}
          />
          <div style={{ marginLeft: "auto" }}>
            <Btn onClick={() => setShowCreate(true)} icon={<Plus size={14} />}>New Template</Btn>
          </div>
        </div>

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          {["", "system", "workflow", "safety", "context"].map(c => (
            <button key={c} onClick={() => setCatFilter(c)} style={filterBtnStyle(catFilter === c)}>
              {c || "All"}
            </button>
          ))}
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", marginLeft: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={activeOnly} onChange={e => setActiveOnly(e.target.checked)}
              style={{ accentColor: "var(--brand)" }} />
            Active only
          </label>
        </div>

        {templates.loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[...Array(4)].map((_, i) => <Skeleton key={i} height={96} />)}
          </div>
        ) : tmpls.length === 0 ? (
          <Card>
            <p style={{ textAlign: "center", color: "var(--text-tertiary)", padding: "32px 0" }}>No templates found.</p>
          </Card>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {tmpls.map(t => (
              <Card key={t.id}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{t.name}</span>
                      <Badge variant={CATEGORY_VARIANT[t.category as TemplateCategory] ?? "info"}>{t.category}</Badge>
                      {t.is_active
                        ? <CheckCircle size={14} style={{ color: "var(--success-text, #166534)" }} />
                        : <XCircle size={14} style={{ color: "var(--text-tertiary)" }} />}
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>v{t.version}</span>
                    </div>
                    <p style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-tertiary)", marginBottom: 4 }}>{t.template_key}</p>
                    {t.description && <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>{t.description}</p>}
                    <pre style={{
                      marginTop: 8, fontSize: 11, color: "var(--text-secondary)",
                      background: "var(--surface-sunken)", borderRadius: 6, padding: "8px 10px",
                      maxHeight: 80, overflowY: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word",
                    }}>
                      {t.template_content.slice(0, 300)}{t.template_content.length > 300 ? "…" : ""}
                    </pre>
                  </div>
                  <button onClick={() => setEditTmpl(t)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--brand)", flexShrink: 0 }}>
                    <Edit2 size={15} />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {showCreate && (
          <TemplateModal tmpl={null} onClose={() => setShowCreate(false)} onSaved={() => templates.refetch?.()} />
        )}
        {editTmpl && (
          <TemplateModal tmpl={editTmpl} onClose={() => setEditTmpl(null)} onSaved={() => templates.refetch?.()} />
        )}
      </div>
    </AdminLayout>
  );
}
