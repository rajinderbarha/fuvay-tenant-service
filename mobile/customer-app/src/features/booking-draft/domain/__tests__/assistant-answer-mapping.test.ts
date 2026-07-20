import { mapAssistantAnswersToDraftUpdate } from "../assistant-answer-mapping";
import type { AnswerRecord } from "../../../booking-assistant/domain/assistant-session";

function answer(stepId: string, canonicalAnswer: string | string[]): AnswerRecord {
  return { stepId: stepId as AnswerRecord["stepId"], questionType: "SINGLE_SELECT", canonicalAnswer, displaySummary: "x", submittedAt: "2026-01-01T00:00:00Z" };
}

describe("mapAssistantAnswersToDraftUpdate", () => {
  it("maps a brand answer to brand_id", () => {
    expect(mapAssistantAnswersToDraftUpdate([answer("brand", "brand-1")])).toEqual({ brand_id: "brand-1" });
  });

  it("maps a service_type answer to offering_type_id (documented naming assumption carried from CUSTOMER-L5-05)", () => {
    expect(mapAssistantAnswersToDraftUpdate([answer("service_type", "type-1")])).toEqual({ offering_type_id: "type-1" });
  });

  it("joins issue_description and customer_note into issue_summary", () => {
    const result = mapAssistantAnswersToDraftUpdate([answer("issue_description", "AC not cooling"), answer("customer_note", "Please call before arriving")]);
    expect(result.issue_summary).toBe("AC not cooling — Please call before arriving");
  });

  it("never includes issue_type_id or service_option — the backend PUT endpoint does not accept them", () => {
    const result = mapAssistantAnswersToDraftUpdate([answer("issue_type", "it-1"), answer("service_option", ["so-1"])]);
    expect(result).toEqual({});
  });

  it("returns an empty payload for an empty answer list", () => {
    expect(mapAssistantAnswersToDraftUpdate([])).toEqual({});
  });

  it("combines brand, service type, and issue summary together", () => {
    const result = mapAssistantAnswersToDraftUpdate([answer("brand", "brand-1"), answer("service_type", "type-1"), answer("issue_description", "Leaking")]);
    expect(result).toEqual({ brand_id: "brand-1", offering_type_id: "type-1", issue_summary: "Leaking" });
  });
});
