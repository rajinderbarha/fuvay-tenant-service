/**
 * What the technician will actually do on the visit -- authored catalog content,
 * narrowed server-side to the assigned provider's own selection and to
 * customer-visible points only.
 *
 * `totalPoints === 0` is a real state (nothing authored for the service yet).
 * The UI must show nothing then, never substitute generic reassurance.
 */
export interface ServiceChecklistPoint {
  id: string;
  label: string;
  helpText: string | null;
  requiresPhoto: boolean;
}

export interface ServiceChecklistSection {
  title: string;
  points: ServiceChecklistPoint[];
}

export interface ServiceChecklist {
  totalPoints: number;
  photoPoints: number;
  sections: ServiceChecklistSection[];
  /** True when these are the provider's own chosen points rather than the full
   * authored list, so the UI can word it accurately. */
  providerSelected: boolean;
}
