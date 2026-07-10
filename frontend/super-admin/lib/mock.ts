/**
 * Mock data for Super Admin Portal development.
 * PROVEN: Every mock object matches the real API type exactly.
 * Replace API_BASE env to switch between mock and real backend.
 */
import type {
  Tenant, PlatformKpis, ChartData, SecuritySummary, ComplianceSummary,
  MarketingSummary, BudgetStatus, SocialAccount, Job, SlaAlert,
  ActivityLog, AuditLog, DeletionRequest, BillingProfile, BillingConfig,
  WalletBalance, ReviewAggregate,
} from "./api";

export const MOCK_TENANTS: Tenant[] = [
  { tenant_id:"t1", tenant_name:"Rahul AC Services",     vertical:"home_services",  city:"Mumbai",    state:"Maharashtra", status:"active",    health_score:92, health_band:"platinum", plan_type:"growth",     is_discoverable:true, created_at:"2026-01-15T10:00:00Z" },
  { tenant_id:"t2", tenant_name:"Delhi Fix Masters",      vertical:"home_services",  city:"Delhi",     state:"Delhi",       status:"active",    health_score:74, health_band:"gold",     plan_type:"starter",    is_discoverable:true, created_at:"2026-02-01T10:00:00Z" },
  { tenant_id:"t3", tenant_name:"Bangalore Home Care",    vertical:"home_services",  city:"Bangalore", state:"Karnataka",   status:"active",    health_score:58, health_band:"silver",   plan_type:"growth",     is_discoverable:true, created_at:"2026-01-20T10:00:00Z" },
  { tenant_id:"t4", tenant_name:"Smart Learning Hub",     vertical:"coaching_center",city:"Pune",      state:"Maharashtra", status:"active",    health_score:85, health_band:"gold",     plan_type:"growth",     is_discoverable:true, created_at:"2026-03-01T10:00:00Z" },
  { tenant_id:"t5", tenant_name:"Chennai Repair Pro",     vertical:"home_services",  city:"Chennai",   state:"Tamil Nadu",  status:"active",    health_score:41, health_band:"bronze",   plan_type:"starter",    is_discoverable:true, created_at:"2026-02-15T10:00:00Z" },
  { tenant_id:"t6", tenant_name:"Kolkata Quick Fix",      vertical:"home_services",  city:"Kolkata",   state:"West Bengal", status:"suspended", health_score:18, health_band:"critical", plan_type:"starter",    is_discoverable:false,created_at:"2026-01-10T10:00:00Z" },
  { tenant_id:"t7", tenant_name:"Hyderabad Pro Services", vertical:"home_services",  city:"Hyderabad", state:"Telangana",   status:"active",    health_score:87, health_band:"platinum", plan_type:"enterprise", is_discoverable:true, created_at:"2026-01-05T10:00:00Z" },
  { tenant_id:"t8", tenant_name:"Ahmedabad Elite Care",   vertical:"home_services",  city:"Ahmedabad", state:"Gujarat",     status:"active",    health_score:63, health_band:"silver",   plan_type:"growth",     is_discoverable:true, created_at:"2026-04-01T10:00:00Z" },
];

export const MOCK_KPIS: PlatformKpis = {
  active_tenants: 142, jobs_today: 847, commission_today: 84700,
  at_risk_tenants: 9,  open_security_threats: 3, pending_compliance: 2,
  total_revenue_mtd: 2400000, new_tenants_mtd: 18,
};

export const MOCK_REVENUE: ChartData[] = [
  {date:"Jun 19",value:78000},{date:"Jun 20",value:82000},{date:"Jun 21",value:71000},
  {date:"Jun 22",value:95000},{date:"Jun 23",value:88000},{date:"Jun 24",value:102000},
  {date:"Jun 25",value:84700},
];

export const MOCK_JOBS_CHART: ChartData[] = [
  {date:"Jun 19",value:710},{date:"Jun 20",value:756},{date:"Jun 21",value:698},
  {date:"Jun 22",value:821},{date:"Jun 23",value:779},{date:"Jun 24",value:903},
  {date:"Jun 25",value:847},
];

export const MOCK_SECURITY: SecuritySummary = {
  active_api_keys:14, blocked_ips:7, open_high_threats:3,
  active_sessions:89, generated_at: new Date().toISOString(),
};

export const MOCK_COMPLIANCE: ComplianceSummary = {
  pending_deletion_requests:2, sla_breached_deletions:0, pending_exports:1,
  total_consent_records:3847, compliance_status:"COMPLIANT",
  generated_at: new Date().toISOString(),
};

export const MOCK_MARKETING: MarketingSummary = {
  total_posts_published:142, posts_pending:5, total_assets_generated:67,
  total_dalle_cost_inr:536,
  daily_budget:{ date:new Date().toISOString().slice(0,10), spent_inr:48, budget_inr:500, remaining_inr:452, budget_pct_used:9.6 },
  generated_at: new Date().toISOString(),
};

export const MOCK_SOCIAL_ACCOUNTS: SocialAccount[] = [
  { account_id:"sa1", platform:"instagram", page_name:"@serviceos.in",    status:"active", follower_count:12400, post_count:142, days_until_token_expiry:45, token_needs_refresh:false },
  { account_id:"sa2", platform:"facebook",  page_name:"ServiceOS India",  status:"active", follower_count:8900,  post_count:118, days_until_token_expiry:45, token_needs_refresh:false },
];

export const MOCK_JOBS: Job[] = [
  { id:"j1", job_number:"JOB-20240001", tenant_id:"t1", tenant_name:"Rahul AC Services",    customer_name:"Priya Sharma",   status:"in_progress",    service_type:"AC Service",      city:"Mumbai",    assigned_staff:"Ramesh K",  created_at:"2026-06-25T08:00:00Z", updated_at:"2026-06-25T09:30:00Z", commission_amount:210, minutes_in_status:90  },
  { id:"j2", job_number:"JOB-20240002", tenant_id:"t2", tenant_name:"Delhi Fix Masters",    customer_name:"Anjali Verma",   status:"en_route",       service_type:"Plumbing",        city:"Delhi",     assigned_staff:"Sunil M",   created_at:"2026-06-25T09:00:00Z", updated_at:"2026-06-25T10:10:00Z", commission_amount:140, minutes_in_status:25  },
  { id:"j3", job_number:"JOB-20240003", tenant_id:"t7", tenant_name:"Hyderabad Pro",        customer_name:"Kumar Reddy",    status:"quality_check",  service_type:"Electrical",      city:"Hyderabad", assigned_staff:"Venkat P",  created_at:"2026-06-25T07:30:00Z", updated_at:"2026-06-25T11:00:00Z", commission_amount:350, minutes_in_status:60  },
  { id:"j4", job_number:"JOB-20240004", tenant_id:"t3", tenant_name:"Bangalore Home Care",  customer_name:"Meera Patel",    status:"parts_required", service_type:"AC Service",      city:"Bangalore", assigned_staff:"Rajan S",   created_at:"2026-06-25T08:30:00Z", updated_at:"2026-06-25T09:45:00Z", commission_amount:420, minutes_in_status:135 },
  { id:"j5", job_number:"JOB-20240005", tenant_id:"t1", tenant_name:"Rahul AC Services",    customer_name:"Arun Singh",     status:"accepted",       service_type:"Deep Clean",      city:"Mumbai",    assigned_staff:"Mohan D",   created_at:"2026-06-25T10:00:00Z", updated_at:"2026-06-25T10:05:00Z", commission_amount:180, minutes_in_status:5   },
  { id:"j6", job_number:"JOB-20240006", tenant_id:"t5", tenant_name:"Chennai Repair Pro",   customer_name:"Divya Kumar",    status:"disputed",       service_type:"Carpentry",       city:"Chennai",   assigned_staff:"Arjun T",   created_at:"2026-06-24T14:00:00Z", updated_at:"2026-06-25T08:00:00Z", commission_amount:280, minutes_in_status:1080},
];

export const MOCK_SLA_ALERTS: SlaAlert[] = [
  { job_id:"j4", job_number:"JOB-20240004", tenant_name:"Bangalore Home Care", status:"parts_required", minutes_overdue:75,  severity:"medium" },
  { job_id:"j6", job_number:"JOB-20240006", tenant_name:"Chennai Repair Pro",  status:"disputed",       minutes_overdue:240, severity:"high"   },
];

export const MOCK_ACTIVITIES: ActivityLog[] = [
  { log_id:"al1", activity_type:"failed_login",        threat_level:"medium",   entity_id:"user_xyz", description:"10 failed logins in 15 min from 103.21.45.67", ip_address:"103.21.45.67", detected_value:10, threshold:10, status:"open",         created_at:"2026-06-25T09:15:00Z" },
  { log_id:"al2", activity_type:"api_key_brute_force", threat_level:"high",     entity_id:"sk_live_",  description:"5 invalid API key attempts in 5 min",           ip_address:"45.33.102.88", detected_value:5,  threshold:5,  status:"open",         created_at:"2026-06-25T08:45:00Z" },
  { log_id:"al3", activity_type:"excessive_requests",  threat_level:"critical",  entity_id:"t6",       description:"847 requests in 60 seconds from tenant t6",     ip_address:"89.45.12.34",  detected_value:847,threshold:500,status:"acknowledged", created_at:"2026-06-24T22:00:00Z" },
];

export const MOCK_AUDIT_LOGS: AuditLog[] = [
  { log_id:"pal1", operation:"api_key.create",   engine_id:"security",   entity_type:"api_key",   entity_id:"ak_001", actor_role:"super_admin", actor_ip:"192.168.1.1", is_high_risk:true,  created_at:"2026-06-25T10:30:00Z" },
  { log_id:"pal2", operation:"tenant.suspend",   engine_id:"tenant",     entity_type:"tenant",    entity_id:"t6",     actor_role:"super_admin", actor_ip:"192.168.1.1", is_high_risk:true,  created_at:"2026-06-25T09:00:00Z" },
  { log_id:"pal3", operation:"wallet.topup",     engine_id:"commerce",   entity_type:"wallet",    entity_id:"w_t1",   actor_role:"super_admin", actor_ip:"192.168.1.1", is_high_risk:false, created_at:"2026-06-25T08:30:00Z" },
  { log_id:"pal4", operation:"ip.block",         engine_id:"security",   entity_type:"ip",        entity_id:"45.33.102.88", actor_role:"super_admin", actor_ip:"192.168.1.1", is_high_risk:true,  created_at:"2026-06-25T08:45:00Z" },
];

export const MOCK_DELETION_REQUESTS: DeletionRequest[] = [
  { request_id:"dr1", user_id:"u_123", status:"pending",   sla_deadline:new Date(Date.now()+20*3600000).toISOString(), hours_until_sla:20.5, sla_breached:false, tables_erased:[], tables_exempted:[], exemption_reasons:{}, created_at:"2026-06-25T02:00:00Z" },
  { request_id:"dr2", user_id:"u_456", status:"completed", sla_deadline:new Date(Date.now()-2*3600000).toISOString(),  hours_until_sla:0,    sla_breached:false, tables_erased:["users","bookings","messages","reviews"], tables_exempted:["payment_records","invoice_records"], exemption_reasons:{"payment_records":"GST Act — 7 year retention required","invoice_records":"GST Act — 7 year retention required"}, created_at:"2026-06-24T10:00:00Z" },
];

export const MOCK_BILLING_PROFILES: Record<string, BillingProfile> = {
  t1:{ profile_id:"bp1", tenant_id:"t1", billing_mode:"credit_commission", vertical:"home_services", commission_rate:0.07, plan_type:"growth",     is_active:true, activated_at:"2026-01-15T10:00:00Z" },
  t4:{ profile_id:"bp4", tenant_id:"t4", billing_mode:"subscription_leads",vertical:"coaching_center",commission_rate:0.00,plan_type:"growth",     is_active:true, activated_at:"2026-03-01T10:00:00Z" },
  t7:{ profile_id:"bp7", tenant_id:"t7", billing_mode:"credit_commission", vertical:"home_services", commission_rate:0.05, plan_type:"enterprise", is_active:true, activated_at:"2026-01-05T10:00:00Z" },
};

export const MOCK_BILLING_CONFIGS: BillingConfig[] = [
  { vertical:"home_services",   plan_type:"starter",    commission_rate:0.10, valid_from:"2026-01-01T00:00:00Z" },
  { vertical:"home_services",   plan_type:"growth",     commission_rate:0.07, valid_from:"2026-01-01T00:00:00Z" },
  { vertical:"home_services",   plan_type:"enterprise", commission_rate:0.05, valid_from:"2026-01-01T00:00:00Z" },
  { vertical:"coaching_center", plan_type:"starter",    commission_rate:0.00, valid_from:"2026-01-01T00:00:00Z" },
  { vertical:"coaching_center", plan_type:"growth",     commission_rate:0.00, valid_from:"2026-01-01T00:00:00Z" },
];

export const MOCK_WALLET: WalletBalance = {
  credit_balance:24500, lifetime_purchased:50000, lifetime_consumed:25500,
  burn_rate_daily:150, low_balance_alert:false, reconciliation_ok:true,
  balance:24500, reserved:2000, available:22500, currency:"INR",
};

export const MOCK_REVIEW_AGG: ReviewAggregate = {
  entity_type:"tenant", entity_id:"t1", review_count:48,
  avg_composite:4.3, reply_rate:87.5, last_computed_at:"2026-06-25T06:00:00Z",
};
