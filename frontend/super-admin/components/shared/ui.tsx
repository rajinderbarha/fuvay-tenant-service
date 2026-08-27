"use client";
/**
 * Re-exports of the shared PortalKit component set from
 * @serviceos/design-system, under the names super-admin pages already use.
 *
 * This file used to contain the full implementation of every component
 * below -- byte-for-byte near-duplicated in tenant-portal's own
 * components/shared/ui.tsx, and the two had genuinely drifted (button
 * corner radius, IconBtn hover colors, a DataTable dropdown-clipping fix
 * present here but not there). There is now exactly one real
 * implementation, in the shared package; this file only maps its names
 * back to the ones every admin page already imports, so no call site in
 * this app had to change.
 */
export {
  Btn, IconBtn, AddBtn, EditBtn, DeleteBtn, ViewBtn, MoreBtn, RowActions,
  PkBadge as Badge,
  SurfaceCard as Card,
  CardHeader,
  PkInput as Input,
  PkSelect as Select,
  LoadingSpinner as Spinner,
  TextSkeleton as Skeleton,
  InitialsAvatar as Avatar,
  Dialog as Modal,
  PkToaster as Toaster,
  MetricCard as StatCard,
  SummaryCard,
  SummaryCardsRow,
  KpiGrid,
  PkSectionHeader as SectionHeader,
  SimpleTable as DataTable,
  EmptyState,
  HealthMeter,
  JobStatusBadge,
  Pagination,
  PkTextarea as Textarea,
} from "@serviceos/design-system";
export type {
  PkBtnVariant as BtnVariant,
  PkBtnSize as BtnSize,
  PkToastItem as ToastItem,
} from "@serviceos/design-system";
