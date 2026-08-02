import { JobExecutionStackParamList } from "../../navigation/routeTypes";

/**
 * Maps a backend `next_required_action.key` (the real action-type vocabulary
 * from `_NEXT_ACTION_MAP` in app/engines/home_service_assignment/service.py)
 * to how the mobile app handles it. Never invents an action the backend
 * didn't return; unmapped/unknown keys fall through to "unhandled" so the
 * button safely disables rather than routing somewhere wrong.
 */
export type ActionHandling =
  | { kind: "mutation"; mutation: "accept" | "on_the_way" | "reached_site" }
  | { kind: "navigate"; screen: keyof JobExecutionStackParamList }
  | { kind: "blocked" }
  | { kind: "unhandled" };

const MUTATION_FOR_ACTION: Record<string, "accept" | "on_the_way" | "reached_site"> = {
  accept: "accept",
  on_the_way: "on_the_way",
  reached_site: "reached_site",
};

const SCREEN_FOR_ACTION: Record<string, keyof JobExecutionStackParamList> = {
  start_inspection: "Inspection",
  complete_inspection: "Inspection",
  create_estimate: "Estimate",
  // Same screen as create -- the Estimate Builder derives create/view/revise
  // mode from the backend-projected quote state, never a second screen.
  revise_estimate: "Estimate",
  start_service: "Checklist",
  mark_work_done: "CompletionProof",
  complete_job: "DirectPaymentConfirmation",
};

const BLOCKED_ACTIONS = new Set(["await_approval", "estimate_rejected", "blocked"]);

export function resolveActionHandling(actionKey: string | null): ActionHandling {
  if (!actionKey) return { kind: "unhandled" };
  if (BLOCKED_ACTIONS.has(actionKey)) return { kind: "blocked" };
  if (MUTATION_FOR_ACTION[actionKey]) return { kind: "mutation", mutation: MUTATION_FOR_ACTION[actionKey] };
  if (SCREEN_FOR_ACTION[actionKey]) return { kind: "navigate", screen: SCREEN_FOR_ACTION[actionKey] };
  return { kind: "unhandled" };
}
