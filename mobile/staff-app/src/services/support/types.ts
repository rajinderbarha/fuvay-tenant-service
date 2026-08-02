export interface ServiceStatusDTO {
  state: "operational" | "degraded" | "major_incident" | "maintenance" | "unavailable";
  message: string;
  last_checked_at: string | null;
  evidence_fresh: boolean;
  affected_components: string[];
  active_incident_count: number;
}

export interface QuickHelpCategoryDTO {
  key: string;
  label: string;
  icon: string;
  description: string;
  article_count: number;
  has_content: boolean;
}

export interface ArticleSummaryDTO {
  id: string;
  slug: string;
  title: string;
  summary: string | null;
  product_area: string;
  keywords: string[];
  is_featured: boolean;
  updated_at: string;
}

export interface ArticleDetailDTO extends ArticleSummaryDTO {
  body: string | null;
  helpful_count: number;
  not_helpful_count: number;
}

export interface TicketSummaryDTO {
  id: string;
  ticket_number: string;
  subject: string;
  category: string;
  category_label: string;
  status: string;
  status_label: string;
  impact: string;
  impact_label: string;
  sla_display: string;
  created_at: string;
  updated_at: string;
}

export interface TicketMessageDTO {
  id: string;
  author_name: string | null;
  author_type: "tenant" | "serviceos" | "system";
  author_role: string | null;
  body: string;
  created_at: string;
}

export interface TicketDetailDTO extends TicketSummaryDTO {
  description: string;
  conversation: TicketMessageDTO[];
  resolved_at: string | null;
  closed_at: string | null;
}

export interface HelpWorkspaceDTO {
  service_status: ServiceStatusDTO;
  summary: { open: number; awaiting_your_reply: number; resolved: number; total: number };
  requests: TicketSummaryDTO[];
  requests_total: number;
  quick_help: QuickHelpCategoryDTO[];
  recommended_articles: ArticleSummaryDTO[];
  knowledge_total: number;
  form_options: {
    categories: { key: string; label: string }[];
    impacts: { key: string; label: string }[];
  };
  permissions: { can_view: boolean; can_create: boolean; can_reply: boolean; can_reopen: boolean };
}

export interface ManagerContactDTO {
  display_name: string | null;
  designation: string | null;
}
