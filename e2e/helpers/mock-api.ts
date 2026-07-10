/**
 * mock-api.ts — shared Playwright route mocks for ServiceOS API.
 * Every handler returns the { success: true, data: ... } shape the portals expect.
 * Import and call setupMockApi(page) in beforeEach.
 */
import type { Page, Route } from "@playwright/test";

function ok<T>(data: T) {
  return { success: true, data, request_id: "test-req-001", engine_id: "mock" };
}

// ── Shared fixtures ──────────────────────────────────────────────────────────
export const TENANT_FIXTURE = {
  id: "t_test01", name: "Rahul AC Services", vertical: "home_services",
  city: "Mumbai", plan_type: "growth", status: "active", health_score: 82,
  created_at: "2024-01-15T10:00:00Z",
};

export const JOB_FIXTURE = {
  id: "j_001", job_number: "JOB-001", tenant_id: "t_test01",
  customer_name: "Priya Sharma", customer_phone: "+91-9876543210",
  status: "in_progress", service_type: "AC Repair", city: "Mumbai",
  created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  sla_minutes: 240, minutes_in_status: 30, job_value: 1500,
  assigned_staff: "Amit Kumar", assigned_staff_id: "s_001",
};

export const STAFF_FIXTURE = {
  id: "s_001", full_name: "Amit Kumar", phone: "+91-9876500001",
  specialisations: ["AC Repair", "Plumbing"], status: "active",
  rating: 4.6, jobs_today: 3, performance_score: 88,
  working_hours: {
    monday: { start:"09:00", end:"18:00", is_working:true },
    tuesday: { start:"09:00", end:"18:00", is_working:true },
    wednesday: { start:"09:00", end:"18:00", is_working:true },
    thursday: { start:"09:00", end:"18:00", is_working:true },
    friday: { start:"09:00", end:"18:00", is_working:true },
    saturday: { start:"10:00", end:"15:00", is_working:true },
    sunday: { start:"09:00", end:"18:00", is_working:false },
  },
};

export const CUSTOMER_FIXTURE = {
  id: "c_001", name: "Priya Sharma", phone: "+91-9876543210",
  email: "priya@example.com", health_band: "gold", health_score: 78,
  total_jobs: 12, total_spend: 18500, ltv_band: "high",
  last_job_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  created_at: "2023-06-01T10:00:00Z",
};

export const BOOKING_FIXTURE = {
  id: "b_001", booking_number: "BK-001", tenant_id: "t_test01",
  customer_name: "Ravi Mehta", customer_phone: "+91-9876500002",
  service_type: "Plumbing", scheduled_at: new Date(Date.now()+86400000).toISOString(),
  status: "pending_confirmation", price_snapshot: { final_price: 800 },
  reschedule_count: 0, created_at: new Date().toISOString(),
};

export const REVIEW_FIXTURE = {
  id: "r_001", review_id: "r_001", job_id: "j_001", composite_score: 4.2,
  comment: "Good service, on time.", status: "published",
  signals: { punctuality: 4.5, quality: 4.0, behaviour: 4.2 },
  has_reply: false, created_at: new Date().toISOString(),
};

export const DOCUMENT_FIXTURE = {
  id: "doc_001", document_number: "DOC-001", title: "Service Agreement",
  status: "pending_signature", job_id: "j_001",
  signing_url: "https://sign.example.com/doc_001",
  signing_url_expires_at: new Date(Date.now()+86400000*3).toISOString(),
  created_at: new Date().toISOString(),
};

export const WALLET_FIXTURE = {
  balance: 15000, reserved: 2000, available: 13000, currency: "Rs",
  last_topup_at: new Date(Date.now()-86400000*7).toISOString(),
};

export const PRICING_TIER_FIXTURE = {
  tier_id: "tier_001", name: "Tier 3 — Small City", code: "tier_3", tier_type: "small_city",
  description: null, base_multiplier: 1.0, platform_fee_percent: 0, default_commission_percent: 10,
  default_sla_minutes: 240, is_active: true, created_at: new Date().toISOString(),
  linked_counts: { cities: 1, zipcodes: 1, zones: 0, rules_total: 1, rules_active: 1 },
};

export const TIER_LOCATION_FIXTURE = {
  location_id: "loc_001", tier_id: "tier_001", country: "India", state: "Punjab",
  district: "Fatehgarh Sahib", city: "bassi pathana", zipcode: "140412", zone_name: null,
  priority: 100, is_active: true, tier_name: "Tier 3 — Small City", tier_code: "tier_3",
  has_conflict: true, conflict_status: "Duplicate Zipcode",
};

export const FINANCE_DEPOSIT_FIXTURE = {
  deposit_id: "dep_001", tenant_id: "t_test01", tenant_name: "Rahul AC Services",
  vertical: "home_services", city: "Mumbai", state: "Maharashtra",
  required_amount: 5000, received_amount: 5000, pending_amount: 0,
  status: "paid", hold_state: "held", adjusted_amount: 0, refunded_amount: 0,
  current_balance: 5000, package_purchase_id: null,
  rejection_reason: null, clarification_notes: null,
  approved_by: "u_001", approved_at: new Date().toISOString(),
  paid_at: new Date().toISOString(), refunded_at: null, created_at: new Date().toISOString(),
};

export const FINANCE_TOPUP_FIXTURE = {
  topup_id: "topup_001", tenant_id: "t_test01", tenant_name: "Rahul AC Services",
  credit_package_id: "pkg_001", order_ref: "TOPUP-0000000001",
  credits_purchased: 5000, bonus_credits: 250, amount_paid: 5000, currency: "INR",
  payment_method: "razorpay", payment_status: "credited", wallet_credit_status: "credited",
  wallet_transaction_id: "wt_001", gateway_order_id: "order_001", gateway_payment_id: "pay_001",
  failure_reason: null, refunded_amount: null,
  created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
};

export const FINANCE_CLAIM_FIXTURE = {
  claim_id: "claim_001", tenant_id: "t_test01", tenant_name: "Rahul AC Services",
  customer_id: "c_001", job_id: "j_001", claim_type: "service_quality",
  description: "AC stopped cooling within a week of repair.", amount_requested: 1500,
  amount_approved: null, status: "pending", assigned_reviewer_id: null,
  admin_notes: null, rejection_reason: null,
  settled_at: null, settled_amount: null,
  documents_requested_at: null, documents_requested_notes: null,
  resolved_at: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
};

export const FINANCE_PAYOUT_FIXTURE = {
  payout_id: "payout_001", payout_number: "PO-00000001", tenant_id: "t_test01", tenant_name: "Rahul AC Services",
  payout_type: "tenant_settlement", requested_amount: 5000, approved_amount: null,
  status: "pending", gateway: "razorpay", method: "razorpay", gateway_transfer_id: null,
  approved_by: null, approved_at: null, rejection_reason: null, failure_reason: null,
  requested_on: new Date().toISOString(), processed_on: null,
};

export const FINANCE_WALLET_FIXTURE = {
  wallet_id: "wallet_001", tenant_id: "t_test01", tenant_name: "Rahul AC Services",
  available_balance: 320, reserved_balance: 0, low_balance_threshold: 500,
  last_transaction_at: new Date().toISOString(), health_band: "at_risk", is_active: true,
};

export const PRICING_RULE_FIXTURE = {
  rule_id: "rule_001", master_service_id: "svc_001", category_id: "cat_001", job_type: "installation",
  tier_id: "tier_001", service_type_id: "type_001", service_option_id: null, brand_id: null,
  city: null, zipcode: "140412", district: null, state: null, zone: null,
  pricing_model: "range", base_price: 300, min_price: 300, max_price: 700, visit_fee: 0,
  platform_fee_percent: 0, commission_percent: 0, tax_percent: 0, bargain_floor: 330,
  rule_name: "AC Installation Split Tier 3", rule_code: "PR-ACINST-A1B2C3", source: "admin",
  effective_from: null, effective_to: null, priority: 10, is_active: true,
  has_conflict: false, validity_status: "always_active",
};

// ── Route definitions ────────────────────────────────────────────────────────
const ROUTES: { pattern: RegExp; handler: (method: string) => unknown }[] = [
  // Auth
  { pattern: /\/v1\/auth\/login/,   handler: () => ok({ access_token:"test-token",
      refresh_token:"rt-test", user:{ id:"u_001", email:"admin@serviceos.com",
        full_name:"Admin User", role:"super_admin", tenant_id:"" }, tenant:TENANT_FIXTURE }) },
  { pattern: /\/v1\/auth\/me/,      handler: () => ok({ id:"u_001",
      email:"admin@serviceos.com", full_name:"Admin User", role:"super_admin", tenant_id:"" }) },
  { pattern: /\/v1\/auth\/logout/,  handler: () => ok({}) },
  // Tenants
  { pattern: /\/v1\/tenants\/t_test01$/, handler: () => ok({ ...TENANT_FIXTURE, engines_active:18 }) },
  { pattern: /\/v1\/tenants/,        handler: () => ok({ tenants:[TENANT_FIXTURE], total:1, has_next:false }) },
  // Jobs
  { pattern: /\/v1\/jobs\/j_001\/history/, handler: () => ok({ history:[
      { status:"created",     changed_at:new Date(Date.now()-3600000*3).toISOString() },
      { status:"in_progress", changed_at:new Date(Date.now()-3600000).toISOString()   },
  ]})},
  { pattern: /\/v1\/jobs\/j_001\/status/, handler: () => ok({ ...JOB_FIXTURE, status:"quality_check" }) },
  { pattern: /\/v1\/jobs\/j_001\/close/,  handler: () => ok({ ...JOB_FIXTURE, status:"closed" }) },
  { pattern: /\/v1\/jobs\/j_001$/,  handler: () => ok(JOB_FIXTURE) },
  { pattern: /\/v1\/jobs\/sla-alerts/, handler: () => ok([
      { job_id:"j_001", job_number:"JOB-001", tenant_name:"Rahul AC Services",
        status:"in_progress", minutes_overdue:45, severity:"warning" },
  ])},
  { pattern: /\/v1\/jobs/,           handler: () => ok({ jobs:[JOB_FIXTURE], total:1, has_next:false }) },
  // Staff
  { pattern: /\/v1\/ds\/staff\/s_001\/performance/, handler: () => ok({
      staff_id:"s_001", composite_score:88,
      signals:{ punctuality:92, quality:87, customer_rating:90, on_time:85 },
      job_count:247, avg_rating:4.6, dispute_rate:0.02, on_time_rate:0.91,
  })},
  { pattern: /\/v1\/staff\/s_001\/schedule/, handler: () => ok(STAFF_FIXTURE) },
  { pattern: /\/v1\/staff\/s_001/,  handler: () => ok(STAFF_FIXTURE) },
  { pattern: /\/v1\/tenants\/t_test01\/staff/, handler: () => ok({ staff:[STAFF_FIXTURE], total:1 }) },
  { pattern: /\/v1\/ds\/staff-scores/, handler: () => ok({ scores:[{ staff_id:"s_001", name:"Amit Kumar", composite_score:88 }] }) },
  // Customers
  { pattern: /\/v1\/commerce\/customers\/c_001\/health/, handler: () => ok({
      customer_id:"c_001", health_band:"gold", health_score:78,
      signals:{ frequency:80, spend:75, recency:70, satisfaction:88 }, risk_flags:[],
  })},
  { pattern: /\/v1\/commerce\/customers\/c_001/, handler: () => ok(CUSTOMER_FIXTURE) },
  { pattern: /\/v1\/commerce\/tenants\/t_test01\/customers/, handler: () => ok({ customers:[CUSTOMER_FIXTURE], total:1, has_next:false }) },
  // Finance
  { pattern: /\/v1\/commerce\/tenants\/t_test01\/wallet/, handler: () => ok(WALLET_FIXTURE) },
  { pattern: /\/v1\/commerce\/tenants\/t_test01\/commission/, handler: () => ok({
      records:[{ id:"com_001", job_id:"j_001", job_number:"JOB-001", amount:300, rate:0.20, job_value:1500, deducted_at:new Date().toISOString() }],
      total_deducted:300, has_next:false,
  })},
  { pattern: /\/v1\/payments\/payout-requests/, handler: () => ok({ id:"po_001", amount:5000, status:"pending", created_at:new Date().toISOString() }) },
  { pattern: /\/v1\/payments\/invoices/, handler: () => ok({ invoices:[], has_next:false }) },
  { pattern: /\/v1\/payments/,        handler: () => ok({ records:[], has_next:false }) },
  { pattern: /\/v1\/subscriptions/,   handler: () => ok({ plan_type:"growth", status:"active", jobs_used:245, jobs_included:500 }) },
  // Bookings
  { pattern: /\/v1\/bookings\/b_001\/confirm/,      handler: () => ok({ ...BOOKING_FIXTURE, status:"confirmed" }) },
  { pattern: /\/v1\/bookings\/b_001\/reject/,       handler: () => ok({ ...BOOKING_FIXTURE, status:"cancelled" }) },
  { pattern: /\/v1\/bookings\/b_001\/convert-to-job/, handler: () => ok(JOB_FIXTURE) },
  { pattern: /\/v1\/bookings/,        handler: () => ok({ bookings:[BOOKING_FIXTURE], total:1, has_next:false }) },
  // Reviews
  { pattern: /\/v1\/reviews\/aggregates\/tenant\/t_test01/, handler: () => ok({
      entity_type:"tenant", entity_id:"t_test01", review_count:48, avg_composite:4.3,
      reply_rate:0.75, signal_averages:{ punctuality:4.4, quality:4.2, behaviour:4.5 },
  })},
  { pattern: /\/v1\/reviews\/r_001\/reply/, handler: () => ok({ ...REVIEW_FIXTURE, has_reply:true, reply_text:"Thank you!" }) },
  { pattern: /\/v1\/reviews\/r_001\/flag/,  handler: () => ok({ ...REVIEW_FIXTURE, status:"flagged" }) },
  { pattern: /\/v1\/reviews/,         handler: () => ok({ reviews:[REVIEW_FIXTURE], has_next:false }) },
  // Chat
  { pattern: /\/v1\/chat\/rooms\/room_001\/messages/, handler: (method) => method==="POST"
      ? ok({ message_id:"msg_new", room_id:"room_001", sender_id:"u_001",
               content:"Test message", message_type:"text", sent_at:new Date().toISOString(), is_read:false })
      : ok({ messages:[
            { message_id:"msg_001", room_id:"room_001", sender_id:"c_001", sender_name:"Priya",
              content:"Is the technician on the way?", message_type:"text",
              sent_at:new Date(Date.now()-600000).toISOString(), is_read:true },
          ], has_next:false })},
  { pattern: /\/v1\/chat\/rooms\/room_001\/read/, handler: () => ok({}) },
  { pattern: /\/v1\/chat\/rooms/,    handler: () => ok({ rooms:[
      { room_id:"room_001", job_id:"j_001", job_number:"JOB-001",
        participant_name:"Priya Sharma", last_message:"Is the technician on the way?",
        last_message_at:new Date().toISOString(), unread_count:0 }
  ], has_next:false })},
  // Documents
  { pattern: /\/v1\/documents\/doc_001\/signing-url/, handler: () => ok({
      signing_url:"https://sign.example.com/doc_001?token=abc",
      expires_at:new Date(Date.now()+86400000*3).toISOString(),
  })},
  { pattern: /\/v1\/documents\/generate/, handler: () => ok(DOCUMENT_FIXTURE) },
  { pattern: /\/v1\/documents\/doc_001/,  handler: () => ok(DOCUMENT_FIXTURE) },
  { pattern: /\/v1\/documents/,        handler: () => ok({ documents:[DOCUMENT_FIXTURE], has_next:false }) },
  // Settings
  { pattern: /\/v1\/settings\/t_test01\/[^/]+$/, handler: () => ok({ key:"commission_rate", value:0.18, source:"tenant", is_override:true }) },
  { pattern: /\/v1\/settings\/t_test01/,  handler: () => ok({ settings:[
      { key:"commission_rate", value:0.20, source:"tenant",   is_override:true  },
      { key:"sla_minutes",     value:240,  source:"plan",     is_override:false },
      { key:"auto_assign",     value:true, source:"platform", is_override:false },
  ]})},
  { pattern: /\/v1\/webhooks/,         handler: () => ok({ webhooks:[
      { id:"wh_001", url:"https://hooks.example.com/sos", events:["job.completed"],
        status:"active", consecutive_failures:0, created_at:new Date().toISOString() }
  ]})},
  // Analytics
  { pattern: /\/v1\/analytics\/tenants\/t_test01\/kpis/, handler: () => ok({
      jobs_today:12, bookings_pending:3, revenue_today:18000, commission_today:3600,
      wallet_balance:15000, staff_active:5, avg_rating:4.3, pending_reviews:2,
  })},
  { pattern: /\/v1\/analytics\/tenants\/t_test01\/jobs/,    handler: () => ok([{ date:"2024-01-20", value:8 }]) },
  { pattern: /\/v1\/analytics\/tenants\/t_test01\/revenue/, handler: () => ok([{ date:"2024-01-20", value:12000 }]) },
  { pattern: /\/v1\/analytics\/platform/, handler: () => ok({
      total_tenants:142, active_tenants:128, total_jobs_today:1847,
      platform_gmv_today:2750000, platform_commission_today:550000, sla_breach_rate:0.032,
  })},
  { pattern: /\/v1\/ds\/forecast/,    handler: () => ok({ forecasts:[] }) },
  // Security
  { pattern: /\/v1\/security\/summary/,    handler: () => ok({ active_sessions:48, blocked_ips:3, failed_logins_24h:12, security_alerts:2 }) },
  { pattern: /\/v1\/security\/activity/,   handler: () => ok({ activities:[
      { id:"act_001", type:"login_failed", ip:"1.2.3.4", severity:"medium", acknowledged:false, created_at:new Date().toISOString() }
  ], has_next:false })},
  { pattern: /\/v1\/security\/blocklist/,  handler: () => ok({ blocked:[{ ip:"1.2.3.4", reason:"brute_force", blocked_at:new Date().toISOString() }] }) },
  { pattern: /\/v1\/security\/block-ip/,   handler: () => ok({ ip:"5.6.7.8", blocked:true }) },
  { pattern: /\/v1\/security\/activity\/act_001\/acknowledge/, handler: () => ok({}) },
  { pattern: /\/v1\/audit/,                 handler: () => ok({ logs:[], has_next:false }) },
  // Security SOC (Security Enterprise Upgrade)
  { pattern: /\/v1\/admin\/security\/overview/, handler: () => ok({
      summary_cards: { open_threats: 2, critical_threats: 1, active_sessions: 5, blocked_ips: 3,
        active_api_keys: 4, expiring_api_keys: 1, failed_logins_24h: 12, high_risk_audit_events_24h: 3 },
      recent_threats: [{ threat_id: "thr_001", threat_number: "THR-abcd1234", activity_type: "failed_login",
        threat_level: "high", risk_score: 70, source: null, entity_id: "u_1", entity_type: "user",
        target_user_id: null, assigned_to_admin_id: null, description: "Repeated failed logins detected",
        ip_address: "1.2.3.4", detected_value: 12, threshold: 5, status: "open", context: null,
        last_seen_at: new Date().toISOString(), resolved_at: null, created_at: new Date().toISOString() }],
      recent_high_risk_audit: [{ log_id: "al_001", operation: "ip.block", engine_id: "security",
        entity_type: "ip_blocklist_entry", entity_id: "1.2.3.4", tenant_id: null, actor_id: "admin_1",
        actor_role: "super_admin", actor_ip: "9.9.9.9", is_high_risk: true, before_state: null,
        after_state: null, created_at: new Date().toISOString() }],
      top_blocked_ips: [{ entry_id: "ip_001", ip_or_cidr: "1.2.3.4", entry_type: "ip", threat_level: "high",
        reason: "brute_force", scope: "all", status: "active", is_global: true, tenant_id: null,
        hit_count: 9, last_hit_at: new Date().toISOString(), expires_at: null, revoked_at: null,
        created_at: new Date().toISOString() }],
      generated_at: new Date().toISOString(),
  })},
  { pattern: /\/v1\/admin\/security\/threats\/thr_001/, handler: () => ok({
      threat_id: "thr_001", threat_number: "THR-abcd1234", activity_type: "failed_login",
      threat_level: "high", risk_score: 70, source: null, entity_id: "u_1", entity_type: "user",
      target_user_id: null, assigned_to_admin_id: null, description: "Repeated failed logins detected",
      ip_address: "1.2.3.4", detected_value: 12, threshold: 5, status: "open", context: null,
      last_seen_at: new Date().toISOString(), resolved_at: null, created_at: new Date().toISOString(),
      actions_taken: [],
  })},
  { pattern: /\/v1\/admin\/security\/threats/, handler: () => ok({
      threats: [{ threat_id: "thr_001", threat_number: "THR-abcd1234", activity_type: "failed_login",
        threat_level: "high", risk_score: 70, source: null, entity_id: "u_1", entity_type: "user",
        target_user_id: null, assigned_to_admin_id: null, description: "Repeated failed logins detected",
        ip_address: "1.2.3.4", detected_value: 12, threshold: 5, status: "open", context: null,
        last_seen_at: new Date().toISOString(), resolved_at: null, created_at: new Date().toISOString() }],
      has_next: false, next_cursor: null,
  })},
  { pattern: /\/v1\/admin\/security\/sessions/, handler: () => ok({
      sessions: [{ session_id: "sess_001", user_id: "u_1", user_email: "provider@serviceos.in",
        user_name: "Test Provider", user_role: "tenant_owner", tenant_id: null, device_id: "dev_1",
        device_name: "Chrome on Windows", device_type: "desktop", ip_address: "1.2.3.4",
        is_trusted: true, is_approved: true, status: "active", last_active_at: new Date().toISOString(),
        expires_at: null, revoked_at: null, revocation_reason: null }],
      has_next: false, next_cursor: null,
  })},
  { pattern: /\/v1\/admin\/security\/ip-blocklist/, handler: () => ok({
      entries: [{ entry_id: "ip_001", ip_or_cidr: "1.2.3.4", entry_type: "ip", threat_level: "high",
        reason: "brute_force", scope: "all", status: "active", is_global: true, tenant_id: null,
        hit_count: 9, last_hit_at: new Date().toISOString(), expires_at: null, revoked_at: null,
        created_at: new Date().toISOString() }],
      has_next: false, next_cursor: null,
  })},
  { pattern: /\/v1\/admin\/security\/api-keys/, handler: (method) => {
      if (method === "POST") {
        return ok({ key_id: "key_001", raw_key: "sk_live_MOCKEDRAWKEYFORTESTINGONLY123456", key_prefix: "abcd1234",
          name: "Test Key", scopes: ["read:jobs"], environment: "live", expires_at: null,
          warning: "Store this key securely. It will NOT be shown again." });
      }
      return ok({ api_keys: [{ key_id: "key_001", tenant_id: "t_test01", name: "Test Key",
        description: null, key_prefix: "sk_live_abcd1234...", environment: "live", scopes: ["read:jobs"],
        owner_type: "tenant", rate_limit_per_minute: null, permissions: [], status: "active",
        expires_at: null, last_used_at: null, use_count: 0, created_at: new Date().toISOString() }],
        has_next: false, next_cursor: null });
  }},
  { pattern: /\/v1\/admin\/security\/audit-logs-export/, handler: () => ok("log_id,operation\n") },
  { pattern: /\/v1\/admin\/security\/audit-logs/, handler: () => ok({
      audit_logs: [{ log_id: "al_001", operation: "ip.block", engine_id: "security",
        entity_type: "ip_blocklist_entry", entity_id: "1.2.3.4", tenant_id: null, actor_id: "admin_1",
        actor_role: "super_admin", actor_ip: "9.9.9.9", is_high_risk: true, before_state: null,
        after_state: null, created_at: new Date().toISOString() }],
      has_next: false, next_cursor: null,
      note: "Audit log is append-only. No entries can be modified or deleted.",
  })},
  { pattern: /\/v1\/admin\/security\/policies/, handler: () => ok({
      policies: [{ id: "pol_001", policy_key: "mfa_required_super_admin", policy_value: true,
        description: "Require MFA for Super Admin accounts", updated_by_user_id: null,
        updated_reason: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
  })},
  // Compliance
  { pattern: /\/v1\/compliance\/summary/,  handler: () => ok({ pending_deletions:2, overdue_deletions:1, active_retention_policies:5 }) },
  { pattern: /\/v1\/compliance\/deletion-requests\/dr_001\/process/, handler: () => ok({ id:"dr_001", status:"completed", tables_erased:["users","bookings"], tables_exempted:["invoices"] }) },
  { pattern: /\/v1\/compliance\/deletion-requests/, handler: () => ok({ requests:[
      { id:"dr_001", user_id:"u_del_01", status:"pending",
        sla_deadline:new Date(Date.now()+86400000*2).toISOString(), hours_until_sla:48,
        tables_erased:[], tables_exempted:[], created_at:new Date().toISOString() }
  ], has_next:false })},
  { pattern: /\/v1\/compliance\/retention-policies/, handler: () => ok({ policies:[], has_next:false }) },
  // Marketing
  { pattern: /\/v1\/marketing\/summary/,        handler: () => ok({ accounts_connected:2, posts_this_month:8, budget_remaining_inr:12000, ai_images_generated:5 }) },
  { pattern: /\/v1\/marketing\/accounts/,        handler: () => ok({ accounts:[], has_next:false }) },
  { pattern: /\/v1\/marketing\/posts/,           handler: () => ok({ posts:[], has_next:false }) },
  { pattern: /\/v1\/marketing\/generate-image/,  handler: () => ok({ image_url:"https://example.com/img.jpg" }) },
  { pattern: /\/v1\/marketing\/schedule/,        handler: () => ok({ id:"post_001", status:"scheduled" }) },
  // Billing
  { pattern: /\/v1\/billing/,                    handler: () => ok({ configs:[], has_next:false }) },
  { pattern: /\/v1\/commerce\/platform/,        handler: () => ok({ total_gmv:2750000, total_commission:550000, active_wallets:128 }) },
  { pattern: /\/v1\/commerce\/wallets\/t_test01\/topup/, handler: () => ok({ balance:20000 }) },

  // Pricing — Enterprise Pricing Module (P0)
  { pattern: /\/v1\/admin\/tiers\/summary/, handler: () => ok({
      total_tiers:2, active_tiers:2, inactive_tiers:0, mapped_cities:1, mapped_zipcodes:1,
      rules_using_tiers:1, unmapped_tiers:0 }) },
  { pattern: /\/v1\/admin\/tiers\/tier_001\/detail/, handler: () => ok({
      tier: PRICING_TIER_FIXTURE,
      mapped_cities:["mumbai"], mapped_zipcodes:["400001"], zones:[],
      pricing_rules:[PRICING_RULE_FIXTURE],
      audit_log:[{ id:"a_001", entity_type:"pricing_tier", entity_id:"tier_001", action:"create",
        actor_role:"super_admin", change_summary:"Created tier 'Tier 3 — Small City'", created_at:new Date().toISOString() }] }) },
  { pattern: /\/v1\/admin\/tiers\/export/, handler: () => ok({ rows:[PRICING_TIER_FIXTURE], count:1, format:"json" }) },
  { pattern: /\/v1\/admin\/tiers\/resolve-location/, handler: () => ok({
      matched_by:"zipcode", tier:PRICING_TIER_FIXTURE,
      resolution_path:["Checked zipcode '140412' for an active mapping.",
        "Found active zipcode mapping — applied tier 'Tier 3 — Small City' (priority 100)."] }) },
  { pattern: /\/v1\/admin\/tiers\/[^/?]+(\?|$)/, handler: (method) => method === "POST"
      ? ok(PRICING_TIER_FIXTURE) : ok(PRICING_TIER_FIXTURE) },
  { pattern: /\/v1\/admin\/tiers(\?|$)/, handler: (method) => method === "POST"
      ? ok(PRICING_TIER_FIXTURE) : ok({ tiers:[PRICING_TIER_FIXTURE] }) },

  { pattern: /\/v1\/admin\/tier-locations\/summary/, handler: () => ok({
      total_mappings:1, mapped_cities:1, mapped_zipcodes:1, mapped_districts:1, mapped_states:1,
      duplicate_zipcodes:1, inactive_mappings:0, recently_imported:0 }) },
  { pattern: /\/v1\/admin\/tier-locations\/import\/preview/, handler: () => ok({
      batch_id:"batch_001", total_rows:2, valid_rows:1, invalid_rows:0, conflict_rows:1,
      sample_rows:[
        { row_no:1, country:"India", state:"Punjab", district:"Fatehgarh Sahib", city:"bassi pathana",
          zipcode:"140412", tier_code:"tier_3", zone_code:null, status:"active", errors:[], conflict:true },
        { row_no:2, country:"India", state:"Maharashtra", district:"Mumbai", city:"mumbai",
          zipcode:"400002", tier_code:"tier_1", zone_code:null, status:"active", errors:[], conflict:false },
      ] }) },
  { pattern: /\/v1\/admin\/tier-locations\/import\/confirm/, handler: () => ok({
      id:"batch_001", status:"completed", file_name:"import.csv", total_rows:2, valid_rows:1,
      invalid_rows:0, conflict_rows:1, created_rows:1, updated_rows:0, skipped_rows:1,
      report_payload:{ rows:[
        { row_no:1, city:"bassi pathana", zipcode:"140412", action:"skipped", reason:"zipcode_conflict" },
        { row_no:2, city:"mumbai", zipcode:"400002", action:"created" },
      ] }, conflict_resolution:"skip", created_at:new Date().toISOString() }) },
  { pattern: /\/v1\/admin\/tier-locations\/imports\/batch_001/, handler: () => ok({
      id:"batch_001", status:"completed", total_rows:2, valid_rows:1, invalid_rows:0, conflict_rows:1,
      created_rows:1, updated_rows:0, skipped_rows:1, report_payload:{ rows:[] } }) },
  { pattern: /\/v1\/admin\/tier-locations/, handler: (method) => method === "POST"
      ? ok({ location_id:"loc_001", ...TIER_LOCATION_FIXTURE })
      : ok({ items:[TIER_LOCATION_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  { pattern: /\/v1\/admin\/pricing-rules\/summary/, handler: () => ok({
      total_rules:1, active_rules:1, inactive_rules:0, service_rules:0, brand_rules:0,
      type_option_rules:1, zipcode_rules:1, tier_rules:1, conflicting_rules:0, expiring_soon:0, expired_rules:0 }) },
  { pattern: /\/v1\/admin\/pricing-rules\/export/, handler: () => ok({ rows:[PRICING_RULE_FIXTURE], count:1, format:"json" }) },
  { pattern: /\/v1\/admin\/pricing-rules\/preview/, handler: () => ok({
      master_service_id:"svc_001", service_name:"AC Installation", job_type:"installation",
      pricing_model:"range", tier:{ tier_id:"tier_001", name:"Tier 3 — Small City" },
      selected_type:"Split", selected_brand:null, matched_rule_id:"rule_001",
      matched_rule_name:"AC Installation Split Tier 3", source:"pricing_rule",
      base_price:300, visit_fee:0, min_price:300, max_price:700, platform_fee_percent:0,
      commission_percent:0, tax_percent:0, bargain_floor:330,
      final_customer_estimate:300, message:"Starting from ₹300.",
      tier_matched:{ matched_by:"zipcode", tier:{ tier_id:"tier_001", name:"Tier 3 — Small City" } },
      resolution_path:["Checked zipcode '140412' for an active mapping.",
        "Found active zipcode mapping — applied tier 'Tier 3 — Small City' (priority 100).",
        "Matched rule at specificity level 'zipcode+type' (priority 10)."],
      warnings:[] }) },
  { pattern: /\/v1\/admin\/pricing-rules\/[^/?]+(\?|$)/, handler: (method) => method === "POST"
      ? ok(PRICING_RULE_FIXTURE) : ok(PRICING_RULE_FIXTURE) },
  { pattern: /\/v1\/admin\/pricing-rules/, handler: (method) => method === "POST"
      ? ok(PRICING_RULE_FIXTURE)
      : ok({ items:[PRICING_RULE_FIXTURE], rules:[PRICING_RULE_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  // Finance Hub — P0 Enterprise Finance Upgrade
  { pattern: /\/v1\/admin\/finance\/summary/, handler: () => ok({
      active_wallets:12, low_balance_wallets:3, credits_issued:250000, commission_earned:48500,
      deposit_held:60000, deposit_pending:2, pending_warranty_claims:1, pending_payouts:1,
      at_risk_tenants:2, recovered_refunded_deposits:1, pending_deposit_actions:1 }) },
  { pattern: /\/v1\/admin\/finance\/overview/, handler: () => ok({
      wallet_health_distribution:{ gold:8, silver:2, at_risk:2 },
      top_low_balance_tenants:[{ tenant_id:"t_test01", tenant_name:"Rahul AC Services", wallet_balance:320, health_band:"at_risk" }],
      deposit_status_breakdown:{ paid:9, unpaid:2, refunded:1 },
      top_commission_contributors:[{ tenant_id:"t_test01", tenant_name:"Rahul AC Services", commission_total:12500 }],
      recent_finance_activity:[
        { type:"payout", label:"Payout completed — ₹5000", tenant_id:"t_test01", created_at:new Date().toISOString() },
        { type:"warranty_claim", label:"Claim approved — ₹1500", tenant_id:"t_test01", created_at:new Date(Date.now()-3600000).toISOString() },
      ],
      pending_actions_queue:{ deposit_verification_pending:1, payout_pending_approval:1, warranty_claim_pending_review:1, failed_topup_payment:1 },
      at_risk_tenants:[{ tenant_id:"t_test01", tenant_name:"Rahul AC Services", health_band:"at_risk", health_score:32 }] }) },

  { pattern: /\/v1\/admin\/finance\/deposits\/summary/, handler: () => ok({
      total_deposit_accounts:11, active_held_deposits:9, pending_deposits:2, refund_pending:0, refunded:1, deposit_risk_cases:0 }) },
  { pattern: /\/v1\/admin\/finance\/deposits\/export/, handler: () => ok({ rows:[FINANCE_DEPOSIT_FIXTURE], count:1, format:"json" }) },
  { pattern: /\/v1\/admin\/finance\/deposits\/dep_001/, handler: () => ok({
      deposit: FINANCE_DEPOSIT_FIXTURE,
      ledger:[{ txn_id:"sdt_001", txn_type:"initial_payment", amount:5000, balance_after:5000, notes:null, created_at:new Date().toISOString() }],
      audit_log:[{ id:"a_001", operation:"deposit.approve", engine_id:"finance_hub", actor_role:"super_admin", created_at:new Date().toISOString() }] }) },
  { pattern: /\/v1\/admin\/finance\/deposits/, handler: (method) => method === "POST"
      ? ok(FINANCE_DEPOSIT_FIXTURE)
      : ok({ items:[FINANCE_DEPOSIT_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  { pattern: /\/v1\/admin\/finance\/topups\/summary/, handler: () => ok({
      total_topups:5, total_topup_value:25000, pending_topups:1, failed_topups:1, refunded_topups:0, topup_value_this_month:8000 }) },
  { pattern: /\/v1\/admin\/finance\/topups\/export/, handler: () => ok({ rows:[FINANCE_TOPUP_FIXTURE], count:1, format:"json" }) },
  { pattern: /\/v1\/admin\/finance\/topups\/topup_001/, handler: () => ok({
      topup: FINANCE_TOPUP_FIXTURE, package:{ package_id:"pkg_001", name:"Growth Pack" },
      ledger_entry:{ txn_id:"wt_001", amount:5000, balance_after:5000 },
      audit_log:[] }) },
  { pattern: /\/v1\/admin\/finance\/topups/, handler: (method) => method === "POST"
      ? ok(FINANCE_TOPUP_FIXTURE)
      : ok({ items:[FINANCE_TOPUP_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  { pattern: /\/v1\/admin\/finance\/warranty-claims\/summary/, handler: () => ok({
      total_claims:4, pending_review:1, investigation_ongoing:1, approved_claims:1, rejected_claims:1, settled_value:1500 }) },
  { pattern: /\/v1\/admin\/finance\/warranty-claims\/export/, handler: () => ok({ rows:[FINANCE_CLAIM_FIXTURE], count:1, format:"json" }) },
  { pattern: /\/v1\/admin\/finance\/warranty-claims\/claim_001/, handler: () => ok({
      claim: FINANCE_CLAIM_FIXTURE, audit_log:[] }) },
  { pattern: /\/v1\/admin\/finance\/warranty-claims/, handler: (method) => method === "POST"
      ? ok(FINANCE_CLAIM_FIXTURE)
      : ok({ items:[FINANCE_CLAIM_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  { pattern: /\/v1\/admin\/finance\/payouts\/summary/, handler: () => ok({
      pending_payouts:1, approved_payouts:1, processing:1, failed_payouts:0, completed_payouts:2, total_payout_value:32000 }) },
  { pattern: /\/v1\/admin\/finance\/payouts\/export/, handler: () => ok({ rows:[FINANCE_PAYOUT_FIXTURE], count:1, format:"json" }) },
  { pattern: /\/v1\/admin\/finance\/payouts\/payout_001\/approve/, handler: () => ok({ ...FINANCE_PAYOUT_FIXTURE, status:"approved", approved_amount:5000 }) },
  { pattern: /\/v1\/admin\/finance\/payouts\/payout_001\/mark-processing/, handler: () => ok({ ...FINANCE_PAYOUT_FIXTURE, status:"processing" }) },
  { pattern: /\/v1\/admin\/finance\/payouts\/payout_001\/mark-completed/, handler: () => ok({ ...FINANCE_PAYOUT_FIXTURE, status:"completed" }) },
  { pattern: /\/v1\/admin\/finance\/payouts\/payout_001/, handler: () => ok({
      payout: FINANCE_PAYOUT_FIXTURE, bank_account:{ account_number:"XXXX1234", ifsc:"HDFC0000123" }, audit_log:[] }) },
  { pattern: /\/v1\/admin\/finance\/payouts/, handler: (method) => method === "POST"
      ? ok(FINANCE_PAYOUT_FIXTURE)
      : ok({ items:[FINANCE_PAYOUT_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  { pattern: /\/v1\/admin\/finance\/wallets\/wallet_001\/ledger/, handler: () => ok({
      wallet:{ ...FINANCE_WALLET_FIXTURE, lifetime_purchased:50000, lifetime_consumed:20000 },
      ledger:[{ txn_id:"wt_001", txn_type:"purchase", amount:5000, balance_before:0, balance_after:5000,
        reference_id:null, reference_type:null, description:"Purchase: Growth Pack", created_at:new Date().toISOString() }],
      pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },
  { pattern: /\/v1\/admin\/finance\/wallets/, handler: () => ok({
      items:[FINANCE_WALLET_FIXTURE], pagination:{ page:1, page_size:50, total:1, total_pages:1 } }) },

  { pattern: /\/v1\/admin\/finance\/audit-logs/, handler: () => ok({ audit_log:[] }) },
];

// ── Setup function ───────────────────────────────────────────────────────────
export async function setupMockApi(page: Page): Promise<void> {
  await page.route("**/v1/**", async (route: Route) => {
    const url    = route.request().url();
    const method = route.request().method();
    for (const { pattern, handler } of ROUTES) {
      if (pattern.test(url)) {
        await route.fulfill({ status:200, contentType:"application/json",
          body: JSON.stringify(handler(method)) });
        return;
      }
    }
    await route.fulfill({ status:404, contentType:"application/json",
      body: JSON.stringify({ success:false, error_code:"NOT_MOCKED", message:`No mock for ${url}` }) });
  });
}

export async function setAdminAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.setItem("serviceos_admin_token",   "test-token-super");
    localStorage.setItem("serviceos_admin_user_id", "u_001");
  });
}

export async function setTenantAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.setItem("serviceos_tenant_token",  "test-token-tenant");
    localStorage.setItem("serviceos_tenant_id",     "t_test01");
    localStorage.setItem("serviceos_tenant_name",   "Rahul AC Services");
    localStorage.setItem("serviceos_vertical",      "home_services");
    localStorage.setItem("serviceos_plan_type",     "growth");
    localStorage.setItem("serviceos_health_score",  "82");
    localStorage.setItem("serviceos_user_id",       "u_001");
  });
}

export async function clearAuth(page: Page): Promise<void> {
  await page.evaluate(() => localStorage.clear());
}
