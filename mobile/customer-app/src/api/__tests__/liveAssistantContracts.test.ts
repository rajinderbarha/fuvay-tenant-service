import live from "../__fixtures__/liveAssistantPayloads.json";
import { parseCustomerHomeDto } from "../adapters/customerHome";
import { parseAssistantSessionDto } from "../adapters/assistantSession";
import {
  assistantBootstrapResponseSchema, selectIssueResponseSchema,
} from "../contracts/assistantBootstrap";
import { questionFlowEnvelopeSchema } from "../contracts/questionFlow";

/**
 * The app's contracts, run against payloads captured from the RUNNING backend.
 *
 * Every other contract test in this repo uses hand-written fixtures, which pin what we
 * BELIEVE the backend sends. That cannot catch the failure mode where the backend is
 * healthy — every endpoint in the assistant flow answers 200, verified by walking the
 * whole flow for all seven categories — and the app rejects a valid response anyway.
 * A rejected parse becomes a DomainError, which is what the assistant's error card
 * shows.
 *
 * Regenerate with scratchpad/capture_assistant_payloads.py against a live API.
 */
describe("live assistant payloads still satisfy the app's contracts", () => {
  it("parses the Home aggregate", () => {
    expect(() => parseCustomerHomeDto(live.home)).not.toThrow();
  });

  it("parses the AI session the flow opens with", () => {
    expect(() => parseAssistantSessionDto(live.session)).not.toThrow();
  });

  it("parses the assistant bootstrap", () => {
    const result = assistantBootstrapResponseSchema.safeParse(live.bootstrap);
    expect(result.success ? null : result.error.issues).toBeNull();
  });

  it("parses the select-issue response, envelope included", () => {
    const result = selectIssueResponseSchema.safeParse(live.select_issue);
    expect(result.success ? null : result.error.issues).toBeNull();
  });

  it("parses the envelope returned after answering a question", () => {
    const result = questionFlowEnvelopeSchema.safeParse(live.answer);
    expect(result.success ? null : result.error.issues).toBeNull();
  });

  it("parses a re-fetched question flow", () => {
    const result = questionFlowEnvelopeSchema.safeParse(live.question_flow);
    expect(result.success ? null : result.error.issues).toBeNull();
  });
});
