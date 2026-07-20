import {
  createAssistantSession,
  submitAnswer,
  goToPreviousStep,
  reviseAnswer,
  completeSession,
  currentStepId,
  currentQuestionType,
  canGoBack,
  assistantProgress,
  isAtCompletion,
  orderedAnswerHistory,
} from "../assistant-session";
import { normalizeSingleSelectAnswer, normalizeMultiSelectAnswer } from "../answer-normalization";
import type { StepGates } from "../assistant-steps";
import type { ValidatedIssueType } from "../diagnostic-catalog-schema";

const fullGates: StepGates = {
  hasIssueTypes: true,
  hasServiceOptions: true,
  hasBrands: true,
  hasServiceTypes: false,
  requiresBrand: true,
  requiresType: false,
  requiresCustomerNotes: false,
  requiresPhotoUpload: false,
};

function issueType(overrides: Partial<ValidatedIssueType> = {}): ValidatedIssueType {
  return {
    issue_type_id: "it-1",
    name: "Not cooling",
    code: "NOT_COOLING",
    severity: "high",
    is_common: true,
    requires_photo: false,
    requires_description: false,
    display_order: 1,
    ...overrides,
  };
}

describe("createAssistantSession", () => {
  it("starts READY at step 0 with an empty answer history", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    expect(session.status).toBe("READY");
    expect(session.currentStepIndex).toBe(0);
    expect(currentStepId(session)).toBe("issue_type");
    expect(orderedAnswerHistory(session)).toEqual([]);
  });
});

describe("submitAnswer", () => {
  it("advances to the next step on a valid submission", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    const next = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType());
    expect(currentStepId(next)).toBe("service_option");
    expect(next.answers.issue_type?.canonicalAnswer).toBe("it-1");
  });

  it("fails closed with an ERROR status when the answer's stepId does not match the current step", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    const result = submitAnswer(session, normalizeSingleSelectAnswer("brand", "b-1", "LG"));
    expect(result.status).toBe("ERROR");
    expect(result.error?.message).toBe("question_not_current");
  });

  it("grows the effective step plan when the issue type requires a description", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    const next = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType({ requires_description: true }));
    expect(currentStepId(next)).toBe("issue_description");
  });

  it("does not submit while status is not READY", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    const errored = submitAnswer(session, normalizeSingleSelectAnswer("brand", "b-1", "LG")); // wrong step -> ERROR
    const attemptWhileErrored = submitAnswer(errored, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType());
    expect(attemptWhileErrored).toBe(errored);
  });
});

describe("goToPreviousStep", () => {
  it("moves back one step", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    const advanced = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType());
    const back = goToPreviousStep(advanced);
    expect(currentStepId(back)).toBe("issue_type");
  });

  it("is a no-op at step 0", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    expect(goToPreviousStep(session)).toBe(session);
  });

  it("reports canGoBack correctly", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    expect(canGoBack(session)).toBe(false);
    const advanced = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType());
    expect(canGoBack(advanced)).toBe(true);
  });
});

describe("reviseAnswer", () => {
  it("jumps back to the target step and clears its own and downstream answers", () => {
    let session = createAssistantSession("svc-1", "cat-1", fullGates);
    session = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType());
    session = submitAnswer(session, normalizeMultiSelectAnswer("service_option", ["so-1"], ["Gas refill"]));
    session = submitAnswer(session, normalizeSingleSelectAnswer("brand", "b-1", "LG"));

    const revised = reviseAnswer(session, "service_option");
    expect(currentStepId(revised)).toBe("service_option");
    expect(revised.answers.issue_type).toBeDefined();
    expect(revised.answers.service_option).toBeUndefined();
    expect(revised.answers.brand).toBeUndefined();
  });

  it("clears selectedIssueType when revising issue_type itself, allowing the branch to recompute", () => {
    let session = createAssistantSession("svc-1", "cat-1", fullGates);
    session = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType({ requires_description: true }));
    expect(currentStepId(session)).toBe("issue_description");

    const revised = reviseAnswer(session, "issue_type");
    expect(revised.selectedIssueType).toBeNull();
    expect(currentStepId(revised)).toBe("issue_type");
  });

  it("is a no-op when the target step is not in the effective plan", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    expect(reviseAnswer(session, "customer_note")).toBe(session);
  });
});

describe("assistantProgress", () => {
  it("reports honest current/total that grows when the plan grows", () => {
    let session = createAssistantSession("svc-1", "cat-1", { ...fullGates, hasServiceOptions: false, requiresBrand: false, hasBrands: false });
    expect(assistantProgress(session)).toEqual({ current: 1, total: 2 }); // issue_type, completion

    session = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType({ requires_description: true }));
    expect(assistantProgress(session)).toEqual({ current: 2, total: 3 }); // issue_description inserted, now at it
  });
});

describe("isAtCompletion / completeSession", () => {
  it("reaches completion once every gated step is answered", () => {
    let session = createAssistantSession("svc-1", "cat-1", {
      ...fullGates,
      hasIssueTypes: false,
      hasServiceOptions: false,
      requiresBrand: false,
      hasBrands: false,
    });
    expect(isAtCompletion(session)).toBe(true);
    session = completeSession(session);
    expect(session.status).toBe("COMPLETED");
  });

  it("completeSession is a no-op when not at the completion step", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    expect(completeSession(session)).toBe(session);
  });
});

describe("currentQuestionType", () => {
  it("returns null at the completion step", () => {
    const session = createAssistantSession("svc-1", "cat-1", {
      ...fullGates,
      hasIssueTypes: false,
      hasServiceOptions: false,
      requiresBrand: false,
      hasBrands: false,
    });
    expect(currentQuestionType(session)).toBeNull();
  });

  it("returns SINGLE_SELECT for issue_type", () => {
    const session = createAssistantSession("svc-1", "cat-1", fullGates);
    expect(currentQuestionType(session)).toBe("SINGLE_SELECT");
  });
});

describe("orderedAnswerHistory", () => {
  it("returns answers in effective step order, not insertion order", () => {
    let session = createAssistantSession("svc-1", "cat-1", fullGates);
    session = submitAnswer(session, normalizeSingleSelectAnswer("issue_type", "it-1", "Not cooling"), issueType());
    session = submitAnswer(session, normalizeMultiSelectAnswer("service_option", ["so-1"], ["Gas refill"]));
    const history = orderedAnswerHistory(session);
    expect(history.map((a) => a.stepId)).toEqual(["issue_type", "service_option"]);
  });
});
