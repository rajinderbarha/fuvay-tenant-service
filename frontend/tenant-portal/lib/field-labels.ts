/**
 * Sprint 34A — Human-readable field label mappings.
 * Converts technical/snake_case field names to user-facing labels.
 *
 * Usage:
 *   import { FIELD_LABELS, fieldLabel } from "@/lib/field-labels";
 *   const label = fieldLabel("tenant_id");  // → "Business ID"
 */

export const FIELD_LABELS: Record<string, string> = {
  // Identity
  id:                              "ID",
  tenant_id:                       "Business ID",
  user_id:                         "User ID",
  staff_id:                        "Staff ID",
  customer_id:                     "Customer ID",
  job_id:                          "Job ID",
  booking_id:                      "Booking ID",
  invoice_id:                      "Invoice ID",
  session_id:                      "Session ID",

  // User fields
  full_name:                       "Full Name",
  email:                           "Email Address",
  phone:                           "Phone Number",
  role:                            "Role",
  is_active:                       "Active",
  is_verified:                     "Verified",
  mfa_enabled:                     "Two-Factor Auth",
  force_password_change:           "Password Change Required",
  password_reset_required:         "Password Change Required",
  temporary_password_active:       "Using Temporary Password",
  account_status:                  "Account Status",
  last_login_at:                   "Last Login",
  created_at:                      "Created",
  updated_at:                      "Last Updated",

  // Tenant fields
  business_name:                   "Business Name",
  registration_number:             "Registration Number",
  tax_id:                          "Tax ID",
  vertical:                        "Service Category",
  category:                        "Service Category",
  provider_verification_status:    "Verification Status",
  verification_status:             "Verification Status",
  onboarding_complete:             "Onboarding Complete",
  wallet_balance:                  "Usage Credit Balance",
  credit_balance:                  "Credit Balance",

  // Media / Files
  media_assets:                    "Uploaded Files",
  avatar_url:                      "Profile Photo",
  logo_url:                        "Logo",
  shop_photo_url:                  "Shop Photo",

  // Jobs
  job_number:                      "Job Number",
  service_type:                    "Service Type",
  job_type:                        "Job Type",
  scheduled_at:                    "Scheduled Date",
  completed_at:                    "Completed",
  assigned_staff_id:               "Assigned To",

  // Finance
  amount:                          "Amount",
  total_amount:                    "Total",
  commission_rate:                 "Commission Rate",
  commission_amount:               "Commission Amount",
  commission_deduction_event:      "Commission Deduction",
  payout_amount:                   "Payout Amount",
  transaction_id:                  "Transaction ID",

  // Events / logs
  event_type:                      "Event",
  failure_reason:                  "Failure Reason",
  ip_address:                      "IP Address",
  user_agent:                      "Browser / Device",
  request_id:                      "Request ID",
  revocation_reason:               "Revoked Reason",
  lock_reason:                     "Lock Reason",
  deactivation_reason:             "Deactivation Reason",

  // Settings
  max_staff_count:                 "Max Staff Allowed",
  subscription_plan:               "Subscription Plan",
  feature_flags:                   "Feature Flags",

  // Trust, quality and provider health. Keep persisted/API names internal.
  trust_score:                     "Provider Health",
  health_score:                    "Health Score",
  provider_health:                 "Provider Health",
  job_completion:                 "Job Completion",
  job_completion_rate:            "Job Completion Rate",
  completed_jobs_count:            "Completed Jobs",
  terminal_jobs_count:            "Completed or Cancelled Jobs",
  cancellation_rate:              "Cancellation Rate",
  average_rating:                 "Average Customer Rating",
  avg_customer_rating:            "Average Customer Rating",
  avg_rating:                     "Average Customer Rating",
  rating_score:                   "Customer Rating Score",
  review_count:                   "Customer Reviews",
  complaint_rate:                 "Unresolved Complaint Rate",
  complaint_dispute_score:        "Unresolved Complaints & Disputes",
  response_sla_score:             "Complaint Response Performance",
  sla_success_rate:               "SLA Success Rate",
  response_time_minutes:          "Average Response Time",
  document_verified:              "Documents Verified",
  owner_verified:                 "Owner Verified",
  document_verification_score:    "Document Verification",
  provider_reschedule_score:      "Schedule Reliability",
  provider_reschedule_count:      "Provider Reschedules",
  provider_reschedule_limit:      "Maximum Provider Reschedules per Job",
  provider_reschedules_over_grace:"Reschedules Above Allowance",
  on_time_arrival_rate:           "On-Time Arrival Rate",
  sla_adherence_rate:             "On-Time Service Rate",
  avg_job_duration_min:           "Average Job Duration",
  composite_score:                "Overall Performance",
  account_verified:               "Account Verified",
  account_verification_score:     "Account Verification",
  profile_completion_percent:     "Profile Completion",
  usage_credit_score:             "Usage Credit Readiness",
  staff_availability_score:       "Team Availability",
  tenant_status:                  "Provider Status",
  payment_reliability:            "Payment Reliability",
  customer_behavior:              "Customer Behaviour",

  // Generic
  status:                          "Status",
  notes:                           "Notes",
  reason:                          "Reason",
  description:                     "Description",
  priority:                        "Priority",
  category_id:                     "Category",
  district:                        "District",
  city:                            "City",
  pincode:                         "Pincode",
  address:                         "Address",
};

/** Returns the human-readable label for a field key, or a formatted fallback. */
export function fieldLabel(key: string): string {
  const normalized = String(key ?? "").trim();
  if (!normalized) return "Field";
  if (FIELD_LABELS[normalized]) return FIELD_LABELS[normalized];
  return normalized
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_.-]+/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\bSla\b/g, "SLA")
    .replace(/\bId\b/g, "ID")
    .replace(/\bApi\b/g, "API")
    .replace(/\bGps\b/g, "GPS");
}
