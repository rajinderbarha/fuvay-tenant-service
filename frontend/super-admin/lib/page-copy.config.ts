/**
 * Sprint 34A — Centralized page copy configuration.
 * All user-facing page titles, subtitles, and empty state messages live here.
 *
 * Usage:
 *   import { PAGE_COPY } from "@/lib/page-copy.config";
 *   const copy = PAGE_COPY.admin.tenants;
 *   // → { title, description, primaryAction, emptyTitle, emptyDescription }
 */

export interface PageCopy {
  title: string;
  description: string;
  primaryAction?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: string;
}

export const PAGE_COPY = {
  admin: {
    dashboard: {
      title: "Platform Overview",
      description: "Monitor platform health, pending actions, and key metrics.",
    },
    tenants: {
      title: "Businesses",
      description: "Manage businesses and service providers registered on the platform.",
      primaryAction: "Add Business",
      emptyTitle: "No businesses yet",
      emptyDescription: "Start onboarding your first service provider or business.",
      emptyAction: "Add Business",
    },
    tenantDetail: {
      title: "Business Profile",
      description: "Manage this business's settings, services, staff, and verification.",
    },
    users: {
      title: "Platform Users",
      description: "Manage administrator accounts and platform-level user access.",
      primaryAction: "Invite User",
      emptyTitle: "No users found",
      emptyDescription: "Invite the first administrator to get started.",
      emptyAction: "Invite User",
    },
    bookings: {
      title: "Bookings",
      description: "View and manage all customer bookings across the platform.",
      emptyTitle: "No bookings found",
      emptyDescription: "Bookings from customers will appear here. Try adjusting your filters.",
    },
    operations: {
      title: "Operations",
      description: "Active jobs, field assignments, and operational status.",
      emptyTitle: "No active jobs",
      emptyDescription: "All jobs have been completed or no new jobs have been created.",
    },
    finance: {
      title: "Finance",
      description: "Invoices, payments, commissions, and wallet transactions.",
    },
    reviews: {
      title: "Reviews",
      description: "Customer reviews and ratings across all providers.",
      emptyTitle: "No reviews yet",
      emptyDescription: "Customer reviews will appear here once jobs are completed.",
    },
    complaints: {
      title: "Complaints",
      description: "Manage customer complaints, disputes, and escalations.",
      emptyTitle: "No open complaints",
      emptyDescription: "All complaints have been resolved or no complaints have been filed.",
    },
    categories: {
      title: "Service Categories",
      description: "Configure the service categories available on the platform.",
      primaryAction: "Add Category",
      emptyTitle: "No categories configured",
      emptyDescription: "Add service categories to get started with provider onboarding.",
      emptyAction: "Add Category",
    },
    packages: {
      title: "Credit Packages",
      description: "Manage credit packages that businesses can purchase.",
      primaryAction: "Add Package",
      emptyTitle: "No packages created",
      emptyDescription: "Create credit packages for businesses to purchase wallet credits.",
    },
    settings: {
      title: "Platform Settings",
      description: "Global configuration for the ServiceOS platform.",
    },
    marketing: {
      title: "Marketing",
      description: "Platform-wide marketing campaigns and content management.",
    },
    notifications: {
      title: "Notifications",
      description: "Notification history and outbox for platform communications.",
    },
    auditLogs: {
      title: "Audit Log",
      description: "Complete audit trail of all platform actions and changes.",
      emptyTitle: "No audit events",
      emptyDescription: "Platform activity will be recorded here.",
    },
    security: {
      title: "Security",
      description: "Platform security monitoring and access controls.",
    },
    engines: {
      title: "System Engines",
      description: "Manage and monitor the platform's core service engines.",
    },
    media: {
      title: "Media Library",
      description: "Manage uploaded files, images, and documents.",
    },
    analytics: {
      title: "Analytics",
      description: "Platform-wide performance metrics and business intelligence.",
    },
    pricing: {
      title: "Pricing Rules",
      description: "Configure service catalog structure, brands, and provider-owned service setup.",
    },
    staff: {
      title: "Field Staff",
      description: "View and manage field staff across all businesses.",
    },
    customers: {
      title: "Customers",
      description: "View all customers registered on the platform.",
    },
    onboarding: {
      title: "Onboarding Requests",
      description: "New business applications awaiting review and verification.",
      emptyTitle: "No pending applications",
      emptyDescription: "All onboarding requests have been processed.",
    },
    compliance: {
      title: "Compliance",
      description: "Regulatory compliance monitoring and documentation.",
    },
    intelligence: {
      title: "Business Intelligence",
      description: "Advanced analytics and predictive insights.",
    },
    profile: {
      title: "My Profile",
      description: "Manage your administrator profile and preferences.",
    },
  },

  provider: {
    dashboard: {
      title: "Dashboard",
      description: "Today's activity, pending tasks, and your business at a glance.",
    },
    jobs: {
      title: "Jobs",
      description: "Active and recent service jobs assigned to your business.",
      emptyTitle: "No jobs yet",
      emptyDescription: "Customer jobs will appear here once bookings are confirmed.",
    },
    bookings: {
      title: "Bookings",
      description: "Customer booking requests that need your confirmation.",
      emptyTitle: "No bookings",
      emptyDescription: "New customer bookings will appear here.",
    },
    staff: {
      title: "Staff",
      description: "Manage your field staff, schedules, and performance.",
      primaryAction: "Add Staff Member",
      emptyTitle: "No staff added",
      emptyDescription: "Add staff members so they can be assigned to jobs.",
      emptyAction: "Add Staff Member",
    },
    profile: {
      title: "Business Profile",
      description: "Your business information, branding, and contact details.",
    },
    settings: {
      title: "Settings",
      description: "Configure your business preferences and operational settings.",
    },
    wallet: {
      title: "Wallet & Credits",
      description: "Your credit balance, transactions, and subscription status.",
    },
    finance: {
      title: "Finance",
      description: "Invoices, payments, and commission records.",
    },
    analytics: {
      title: "Reports",
      description: "Performance reports, earnings, and service analytics.",
    },
    reviews: {
      title: "Reviews",
      description: "Customer reviews and ratings for your business.",
      emptyTitle: "No reviews yet",
      emptyDescription: "Customer reviews will appear here once your first jobs are completed.",
    },
    complaints: {
      title: "Complaints",
      description: "Customer complaints and dispute resolutions.",
      emptyTitle: "No complaints",
      emptyDescription: "Any customer complaints will appear here.",
    },
    marketing: {
      title: "Marketing",
      description: "Campaigns, promotions, and your visibility on the platform.",
    },
    notifications: {
      title: "Notifications",
      description: "Recent alerts and activity from your business.",
    },
    serviceSetup: {
      title: "Service Setup",
      description: "Configure which services you offer and their pricing.",
    },
    onboardingStatus: {
      title: "Onboarding Status",
      description: "Track your progress through the platform onboarding checklist.",
    },
    status: {
      title: "Bookability Status",
      description: "Your current status on the platform and any items blocking you from receiving bookings.",
    },
    serviceAreas: {
      title: "Service Areas",
      description: "Pincodes and districts where you provide services.",
    },
    availability: {
      title: "Availability",
      description: "Your operating hours and time-off schedule.",
    },
    documents: {
      title: "Documents",
      description: "Business documents required for verification.",
    },
    media: {
      title: "Media",
      description: "Photos, documents, and files for your business profile.",
    },
    chat: {
      title: "Chat",
      description: "Messages from customers and platform support.",
    },
    account: {
      title: "My Account",
      description: "Account preferences and security settings.",
    },
  },

  staff: {
    dashboard: {
      title: "My Dashboard",
      description: "Today's jobs, schedule, and pending tasks.",
    },
    jobs: {
      title: "My Jobs",
      description: "Jobs assigned to you.",
      emptyTitle: "No jobs assigned",
      emptyDescription: "Jobs assigned to you will appear here.",
    },
    profile: {
      title: "My Profile",
      description: "Your personal details and work preferences.",
    },
  },
} as const;

/** Helper to get page copy safely. */
export function getPageCopy(section: keyof typeof PAGE_COPY, page: string): PageCopy | null {
  const sec = PAGE_COPY[section] as Record<string, PageCopy>;
  return sec?.[page] ?? null;
}
