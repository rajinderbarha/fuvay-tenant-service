/**
 * Shared typed contracts for workflow/presentation components (Phase D).
 * These are UI view models only -- the backend remains authoritative for
 * every transition, permission and computed value. Components receive
 * these, they never derive them from raw backend payloads themselves.
 */

export interface WorkflowStepModel {
  key: string;
  label: string;
  state: "completed" | "current" | "upcoming" | "blocked" | "skipped";
  completedAtLabel?: string;
}

export interface ActionPresentationModel {
  code: string;
  label: string;
  enabled: boolean;
  loading?: boolean;
  disabledReason?: string;
  tone: "primary" | "secondary" | "danger";
}

export interface BlockerPresentationModel {
  code: string;
  title: string;
  message: string;
  severity: "info" | "warning" | "danger";
  permittedNextActionLabel?: string;
}

export interface CurrentJobCardModel {
  jobId: string;
  jobNumber: string;
  serviceName: string;
  jobTypeLabel: string;
  customerAlias: string;
  scheduleLabel: string;
  locationLabel?: string;
  typeLabel?: string;
  brandLabel?: string;
  statusCode: string;
  statusLabel: string;
  workflowSteps: WorkflowStepModel[];
  requiredAction?: ActionPresentationModel;
  blocker?: BlockerPresentationModel;
}

export type SemanticTone = "neutral" | "info" | "success" | "warning" | "danger";
