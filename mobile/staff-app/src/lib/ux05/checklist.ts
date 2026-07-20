/**
 * Checklist execution helpers (workstream 13). API_CONTRACT_REQUIRED -- no
 * live checklist-content endpoint exists (see backend-contract-blockers.md);
 * these operate purely on the typed view model so the progress/validation
 * rule is real and testable even though the data source is a design
 * fixture today.
 */
import type { ChecklistExecutionView, ChecklistItemView } from "../../types/ux05";

export function computeProgress(view: ChecklistExecutionView): number {
  const items = view.sections.flatMap(s => s.items);
  if (items.length === 0) return 0;
  const done = items.filter(isItemComplete).length;
  return Math.round((done / items.length) * 100);
}

export function isItemComplete(item: ChecklistItemView): boolean {
  if (item.responseType === "photo") return item.photoAttached;
  return item.value !== null && item.value !== "";
}

export function missingRequiredItems(view: ChecklistExecutionView): ChecklistItemView[] {
  return view.sections.flatMap(s => s.items).filter(i => i.required && !isItemComplete(i));
}

export function canComplete(view: ChecklistExecutionView): boolean {
  return missingRequiredItems(view).length === 0;
}
