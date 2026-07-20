/** Mirrors app/engines/customer_flow/service.py#_customer_cat_summary — see CUSTOMER-L5-03-backend-contract-audit.md. */
export interface CategorySummaryDto {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  category_type: string;
  icon_url: string | null;
  banner_url: string | null;
  customer_flow_type: string;
  frontend_component_key: string | null;
  primary_engine_key: string | null;
  available_offering_count: number;
  display_order: number;
}

export interface CategoryListResponse {
  items: CategorySummaryDto[];
  total: number;
  page: number;
  page_size: number;
}
