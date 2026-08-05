/**
 * PARTS-APPROVAL phase -- presentation for a single parts request. Real
 * backend statuses confirmed via `execution/constants.py`:
 * "requested", "business_approved", "business_rejected",
 * "customer_approval_pending", "customer_approved", "customer_rejected",
 * "installed". Only the last five are ever customer-visible at all (see
 * `_CUSTOMER_VISIBLE_PARTS_STATUSES` server-side) -- "requested" and
 * "business_rejected" never reach this mapper in practice, but it still
 * fails safe for them (and any future status) rather than crashing.
 */
export type PartsPresentationKind = "actionable" | "informational" | "approved" | "declined" | "unavailable";

const KIND_MAP: Record<string, PartsPresentationKind> = {
  customer_approval_pending: "actionable",
  business_approved: "informational",
  installed: "informational",
  customer_approved: "approved",
  customer_rejected: "declined",
};

export function resolvePartsPresentationKind(rawStatus: string | null | undefined): PartsPresentationKind {
  if (rawStatus && rawStatus in KIND_MAP) return KIND_MAP[rawStatus];
  return "unavailable";
}

export interface PartsPresentation {
  title: string;
  explanation: string;
}

const PRESENTATION: Record<PartsPresentationKind, PartsPresentation> = {
  actionable: {
    title: "Part review needed",
    explanation: "A part was requested for your repair. Review the additional cost.",
  },
  informational: {
    title: "Part added to your repair",
    explanation: "Your provider approved a part for this repair. Here's what it adds to your estimate.",
  },
  approved: {
    title: "Additional cost approved",
    explanation: "You approved this additional cost.",
  },
  declined: {
    title: "Additional cost declined",
    explanation: "You declined this additional cost.",
  },
  unavailable: {
    title: "Status updating",
    explanation: "",
  },
};

export function resolvePartsPresentation(kind: PartsPresentationKind): PartsPresentation {
  return PRESENTATION[kind];
}
