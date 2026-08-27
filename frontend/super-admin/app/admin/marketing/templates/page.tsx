"use client";
import { TableSurface } from "@serviceos/design-system";
import { useCallback, useState } from "react";
import { adminMarketingApi, MarketingTemplate } from "@/lib/api";
import {
  Card, Badge, Btn, Modal, Input, Select, Skeleton,
} from "@/components/shared/ui";
import { useApi, useAction } from "@/hooks/useApi";
import { Plus, Edit, ToggleLeft, ToggleRight } from "lucide-react";
import { PageHeader } from "@serviceos/design-system";

const TEMPLATE_TYPE_OPTIONS = [
  { value: "launch_banner", label: "Launch Banner" },
  { value: "service_banner", label: "Service Banner" },
  { value: "social_caption", label: "Social Caption" },
  { value: "whatsapp_message", label: "WhatsApp Message" },
  { value: "sms_message", label: "SMS Message" },
  { value: "email_message", label: "Email Message" },
  { value: "promotion_card", label: "Promotion Card" },
  { value: "ad_copy", label: "Ad Copy" },
];

const CHANNEL_OPTIONS_FORM = [
  { value: "internal", label: "Internal" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "sms", label: "SMS" },
  { value: "email", label: "Email" },
  { value: "website", label: "Website" },
];

const BLANK_FORM = {
  template_key: "",
  template_name: "",
  template_type: "launch_banner",
  channel: "website",
  language: "en",
  title_template: "",
  body_template: "",
};

const th: React.CSSProperties = {
  padding: "8px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

export default function AdminMarketingTemplatesPage() {
  const [includeInactive, setIncludeInactive] = useState(false);
  const { data, loading, refetch } = useApi(
    useCallback(
      () => adminMarketingApi.listTemplates({ include_inactive: includeInactive }),
      [includeInactive]
    )
  );

  const templates: MarketingTemplate[] = data?.templates ?? [];

  const [createModal, setCreateModal] = useState(false);
  const [editModal, setEditModal] = useState<{ open: boolean; template: MarketingTemplate | null }>({ open: false, template: null });
  const [form, setForm] = useState(BLANK_FORM);

  const createTemplateAction  = useAction(useCallback((payload: Parameters<typeof adminMarketingApi.createTemplate>[0]) => adminMarketingApi.createTemplate(payload), []));
  const updateTemplateAction  = useAction(useCallback((args: { id: string; payload: Partial<MarketingTemplate> }) => adminMarketingApi.updateTemplate(args.id, args.payload), []));
  const activateTemplateAction   = useAction(useCallback((id: string) => adminMarketingApi.activateTemplate(id), []));
  const deactivateTemplateAction = useAction(useCallback((id: string) => adminMarketingApi.deactivateTemplate(id), []));

  const openEdit = (tmpl: MarketingTemplate) => {
    setForm({
      template_key: tmpl.template_key,
      template_name: tmpl.template_name,
      template_type: tmpl.template_type,
      channel: tmpl.channel,
      language: tmpl.language,
      title_template: tmpl.title_template ?? "",
      body_template: tmpl.body_template,
    });
    setEditModal({ open: true, template: tmpl });
  };

  const FormFields = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: 16 }}>
      <Input placeholder="Template key (snake_case)" value={form.template_key} onChange={(v) => setForm(s => ({ ...s, template_key: v }))} />
      <Input placeholder="Template name" value={form.template_name} onChange={(v) => setForm(s => ({ ...s, template_name: v }))} />
      <Select value={form.template_type} onChange={(v) => setForm(s => ({ ...s, template_type: v }))} options={TEMPLATE_TYPE_OPTIONS} />
      <Select value={form.channel} onChange={(v) => setForm(s => ({ ...s, channel: v }))} options={CHANNEL_OPTIONS_FORM} />
      <Input placeholder="Language (en/hi/pa)" value={form.language} onChange={(v) => setForm(s => ({ ...s, language: v }))} />
      <Input placeholder="Title template (optional, use {{variable}})" value={form.title_template} onChange={(v) => setForm(s => ({ ...s, title_template: v }))} />
      <Input placeholder="Body template (use {{variable}} for placeholders)" value={form.body_template} onChange={(v) => setForm(s => ({ ...s, body_template: v }))} />
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* MODULE-L5-44: investigated (same audit that found L5-39..43) whether
          /v1/admin/marketing/templates* could be repointed to a real
          endpoint. MarketingTemplate's fields (template_key, channel,
          title_template, body_template, variables, is_ai_enabled,
          requires_admin_approval) don't match the real
          marketing_content_templates table (vertical_key, post_type,
          prompt_template, caption_structure, hashtag_set_json, cta) exposed
          at /v1/admin/marketing/content-templates -- a genuinely different
          template concept, not a rename. Rather than fabricate a fix, this
          page says so honestly instead of a silently-broken CRUD UI. */}
      <div style={{ padding: "10px 16px", borderRadius: 10, background: "rgba(217,119,6,0.08)",
        border: "1px solid rgba(217,119,6,0.25)", fontSize: 13, color: "#b45309" }}>
        This page is not available in this build. The template concept it
        assumes (channel/title/body placeholders) does not match the real
        content-templates system (prompt/caption/hashtag based); no backing
        endpoint for this exact shape remains.
      </div>

      <PageHeader
        title="Marketing Templates"
        description="Category-aware templates for campaign asset generation."
        eyebrow="Marketing"
        actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)" }}>
          <Btn variant="ghost" onClick={() => setIncludeInactive(v => !v)}>
            {includeInactive ? "Hide Inactive" : "Show Inactive"}
          </Btn>
          <Btn onClick={() => { setForm(BLANK_FORM); setCreateModal(true); }} disabled>
            <Plus size={14} /> New Template
          </Btn>
        </div>}
      />

      <Card>
        {loading ? (
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 10 }}>
            {[...Array(6)].map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        ) : templates.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No templates found.</div>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                {["Name", "Type", "Channel", "Language", "AI Enabled", "Requires Approval", "Active", ""].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 14px", fontWeight: 500 }}>{t.template_name}</td>
                  <td style={{ padding: "10px 14px" }}><Badge variant="default">{t.template_type}</Badge></td>
                  <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>{t.channel}</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>{t.language}</td>
                  <td style={{ padding: "10px 14px" }}><Badge variant={t.is_ai_enabled ? "info" : "default"}>{t.is_ai_enabled ? "Yes" : "No"}</Badge></td>
                  <td style={{ padding: "10px 14px" }}><Badge variant={t.requires_admin_approval ? "warning" : "default"}>{t.requires_admin_approval ? "Yes" : "No"}</Badge></td>
                  <td style={{ padding: "10px 14px" }}><Badge variant={t.is_active ? "success" : "default"}>{t.is_active ? "Active" : "Inactive"}</Badge></td>
                  <td style={{ padding: "10px 14px" }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <Btn size="sm" variant="ghost" onClick={() => openEdit(t)}>
                        <Edit size={12} /> Edit
                      </Btn>
                      {t.is_active ? (
                        <Btn size="sm" variant="ghost" onClick={() => deactivateTemplateAction.execute(t.id).then(() => refetch())} loading={deactivateTemplateAction.loading}>
                          <ToggleLeft size={12} /> Deactivate
                        </Btn>
                      ) : (
                        <Btn size="sm" variant="ghost" onClick={() => activateTemplateAction.execute(t.id).then(() => refetch())} loading={activateTemplateAction.loading}>
                          <ToggleRight size={12} /> Activate
                        </Btn>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
      </Card>

      <Modal open={createModal} onClose={() => setCreateModal(false)} title="Create Marketing Template">
        <FormFields />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", padding: "0 16px 16px" }}>
          <Btn variant="ghost" onClick={() => setCreateModal(false)}>Cancel</Btn>
          <Btn onClick={() => createTemplateAction.execute(form as any).then(() => { setCreateModal(false); setForm(BLANK_FORM); refetch(); })} loading={createTemplateAction.loading} disabled={!form.template_key || !form.body_template}>Create</Btn>
        </div>
      </Modal>

      <Modal open={editModal.open} onClose={() => setEditModal({ open: false, template: null })} title="Edit Marketing Template">
        <FormFields />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", padding: "0 16px 16px" }}>
          <Btn variant="ghost" onClick={() => setEditModal({ open: false, template: null })}>Cancel</Btn>
          <Btn onClick={() => updateTemplateAction.execute({ id: editModal.template!.id, payload: form }).then(() => { setEditModal({ open: false, template: null }); refetch(); })} loading={updateTemplateAction.loading}>Save</Btn>
        </div>
      </Modal>
    </div>
  );
}
