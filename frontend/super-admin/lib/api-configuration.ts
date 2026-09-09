// ═══════════════════════════════════════════════════════════════════════════
// Platform Configuration + Vertical Monetization (admin)
//   /v1/admin/configuration
//   /v1/admin/monetization/verticals
//
// Real bug fixed here: app/admin/configuration/page.tsx,
// app/admin/finance/vertical-monetization/page.tsx and
// app/admin/home-services/finance/page.tsx have always imported these
// clients, but none of them was ever implemented -- so those pages could not
// compile and the whole super-admin production build failed. Both backing
// ENGINES were also never mounted (every route 404'd) until this session;
// see the include_router block in app/main.py.
//
// Routes matched against app/engines/settings_engine/configuration_router.py
// and app/engines/vertical_monetization/admin_router.py.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

// ── Platform Configuration ──────────────────────────────────────────────────

/** Mirrors the row shape built by `list_configuration` in
 * app/engines/settings_engine/configuration_router.py. Deliberately has NO
 * index signature -- one would make every property resolve to `unknown`. */
export interface ConfigurationListItem {
  key: string;
  label: string;
  owner_module: string;
  data_type: string;
  allowed_scopes: string[];
  risk_level: string;
  locked: boolean;
  admin_mutable: boolean;
  effective_value: unknown;
  source: string;
  status: string;
  version: number | null;
  has_real_consumer: boolean;

  /** These admin payloads carry more backend-shaped fields than are
   * enumerated above; the calling page asserts what it needs. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

export interface ConfigurationSummary {
  registered_settings: number;
  active: number;
  pending_approval: number;
  needs_review: number;
  vertical_overrides: number;
  invalid: number;
  rollback_available: number;

  /** These admin payloads carry more backend-shaped fields than are
   * enumerated above; the calling page asserts what it needs. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

export interface ConfigurationValueVersion {
  id: string;
  setting_key: string;
  scope_type: string;
  scope_id: string;
  version_number: number;
  status: string;
  value: unknown;
  effective_from: string | null;
  effective_to: string | null;
  change_reason: string | null;
  rollback_reason: string | null;
  activated_at: string | null;
  created_at: string | null;
  updated_at: string | null;

  /** These admin payloads carry more backend-shaped fields than are
   * enumerated above; the calling page asserts what it needs. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

export interface ConfigurationDetail extends ConfigurationListItem {
  current?: ConfigurationValueVersion | null;
  draft?: ConfigurationValueVersion | null;
  versions?: ConfigurationValueVersion[];
  history?: ConfigurationValueVersion[];
  validation?: Record<string, unknown> | null;
  consumers?: unknown[];

  /** These admin payloads carry more backend-shaped fields than are
   * enumerated above; the calling page asserts what it needs. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

export const configurationApi = {
  list: (params?: {
    owner_module?: string; risk_level?: string; scope?: string; search?: string;
  }) => {
    const qs = params
      ? `?${new URLSearchParams(
          Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== "")) as Record<string, string>,
        )}`
      : "";
    return apiFetch<{ items: ConfigurationListItem[]; summary: ConfigurationSummary }>(
      `/v1/admin/configuration${qs}`,
    );
  },

  getDetail: (key: string) =>
    apiFetch<ConfigurationDetail>(`/v1/admin/configuration/${encodeURIComponent(key)}/detail`),

  getHistory: (key: string) =>
    apiFetch<{ items: ConfigurationValueVersion[] }>(
      `/v1/admin/configuration/${encodeURIComponent(key)}/history`,
    ),

  listChangeRequests: () =>
    apiFetch<{ items: ConfigurationValueVersion[] }>("/v1/admin/configuration/change-requests"),

  listVersionHistory: () =>
    apiFetch<{ items: ConfigurationValueVersion[] }>("/v1/admin/configuration/version-history"),

  getAudit: () =>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    apiFetch<{ items: Record<string, any>[] }>("/v1/admin/configuration/audit/log"),

  /** Validates a candidate value WITHOUT saving. `key` travels in the body
   * (ValidateIn), not the path. */
  validate: (key: string, scopeType: string, value: unknown) =>
    apiFetch<{ valid: boolean; errors?: string[]; warnings?: string[] }>(
      "/v1/admin/configuration/validate",
      { method: "POST", body: JSON.stringify({ key, scope_type: scopeType, value }) },
    ),

  createChangeRequest: (key: string, body: {
    scope_type?: string; scope_id?: string | null; value: unknown; reason: string;
  }) => apiFetch<ConfigurationValueVersion>(
    `/v1/admin/configuration/${encodeURIComponent(key)}/change-request`,
    { method: "POST", body: JSON.stringify(body) },
  ),

  approve: (versionId: string) =>
    apiFetch<ConfigurationValueVersion>(
      `/v1/admin/configuration/change-requests/${versionId}/approve`, { method: "POST" },
    ),

  activate: (versionId: string) =>
    apiFetch<ConfigurationValueVersion>(
      `/v1/admin/configuration/change-requests/${versionId}/activate`, { method: "POST" },
    ),

  rollback: (versionId: string, reason: string) =>
    apiFetch<ConfigurationValueVersion>(
      `/v1/admin/configuration/change-requests/${versionId}/rollback`,
      { method: "POST", body: JSON.stringify({ reason }) },
    ),
};

// ── Vertical Monetization ───────────────────────────────────────────────────

export interface MonetizationPolicy {
  id?: string;
  vertical_id?: string;
  vertical_key?: string;
  version_number?: number | null;
  status?: string;
  is_current?: boolean;

  provider_model: string;
  provider_percentage: string | null;
  provider_fixed_amount_minor: number | null;
  provider_credit_units: number | null;
  provider_subscription_plan_id: string | null;
  provider_chargeable_event: string | null;
  provider_min_charge_minor: number | null;
  provider_max_charge_minor: number | null;
  provider_health_adjustment_enabled?: boolean;
  provider_health_adjustments_json?: Record<string, number>;
  provider_health_score_max_age_days?: number;
  provider_health_max_effective_percentage?: string;

  customer_fee_model: string;
  customer_fee_percentage: string | null;
  customer_fee_fixed_amount_minor: number | null;
  customer_fee_min_minor: number | null;
  customer_fee_max_minor: number | null;
  customer_fee_basis: string;
  collection_stage: string;
  customer_fee_refund_policy: string;

  published_at?: string | null;

  /** These admin payloads carry more backend-shaped fields than are
   * enumerated above; the calling page asserts what it needs. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

export interface MonetizationPolicyRow {
  vertical_key: string;
  vertical_label?: string;
  status: string;
  version_number: number | null;
  provider_model: string;
  customer_fee_model: string;
  summary?: string;
  active_tenants?: number;
  published_at?: string | null;

  /** These admin payloads carry more backend-shaped fields than are
   * enumerated above; the calling page asserts what it needs. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

export interface MonetizationImpact {
  active_tenants?: number;
  affected_bookings?: number;
  [k: string]: unknown;
}

export const verticalMonetizationApi = {
  list: () =>
    apiFetch<{
      items: MonetizationPolicyRow[];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      summary?: Record<string, any>;
    }>("/v1/admin/monetization/verticals"),

  getDetail: (key: string) =>
    apiFetch<{ current: MonetizationPolicy | null; draft: MonetizationPolicy | null }>(
      `/v1/admin/monetization/verticals/${encodeURIComponent(key)}`,
    ),

  getImpact: (key: string) =>
    apiFetch<MonetizationImpact>(`/v1/admin/monetization/verticals/${encodeURIComponent(key)}/impact`),

  getHistory: (key: string) =>
    apiFetch<{ items: MonetizationPolicy[] }>(
      `/v1/admin/monetization/verticals/${encodeURIComponent(key)}/history`,
    ),

  getAudit: (key: string) =>
    apiFetch<{ items: Record<string, unknown>[] }>(
      `/v1/admin/monetization/verticals/${encodeURIComponent(key)}/audit`,
    ),

  saveDraft: (key: string, draft: Partial<MonetizationPolicy>) =>
    apiFetch<MonetizationPolicy>(
      `/v1/admin/monetization/verticals/${encodeURIComponent(key)}/draft`,
      { method: "POST", body: JSON.stringify(draft) },
    ),

  validate: (draft: Partial<MonetizationPolicy>) =>
    apiFetch<{ valid: boolean; errors: string[]; warnings?: string[] }>(
      "/v1/admin/monetization/validate",
      { method: "POST", body: JSON.stringify(draft) },
    ),

  /** `exampleServiceAmount` is sent as a STRING -- the backend parses it as
   * Decimal, and a JS float would lose precision on money. */
  preview: (draft: Partial<MonetizationPolicy>, exampleServiceAmount = "500") =>
    apiFetch<Record<string, unknown>>("/v1/admin/monetization/preview", {
      method: "POST",
      body: JSON.stringify({ draft, example_service_amount: exampleServiceAmount }),
    }),

  publish: (key: string, reason: string) =>
    apiFetch<MonetizationPolicy>(
      `/v1/admin/monetization/verticals/${encodeURIComponent(key)}/publish`,
      { method: "POST", body: JSON.stringify({ reason }) },
    ),
};
