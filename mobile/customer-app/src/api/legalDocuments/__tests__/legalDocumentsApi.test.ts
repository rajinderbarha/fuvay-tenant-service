import { authenticatedRequest } from "../../client/authenticatedClient";
import { acceptLegalDocuments, getLegalConsentStatus } from "../legalDocumentsApi";

jest.mock("../../client/authenticatedClient", () => ({
  authenticatedRequest: jest.fn(),
}));

const mockedAuthenticatedRequest = authenticatedRequest as jest.MockedFunction<typeof authenticatedRequest>;

const documentId = "11111111-1111-4111-8111-111111111111";

const response = {
  status: 200,
  requestId: "request-1",
  json: {
    success: true,
    meta: { request_id: "request-1" },
    data: {
      requires_acceptance: false,
      documents: [],
      document_ids: [],
      message: "Current",
    },
  },
};

describe("legal consent API", () => {
  beforeEach(() => {
    mockedAuthenticatedRequest.mockReset();
    mockedAuthenticatedRequest.mockResolvedValue(response);
  });

  it("allows the post-login consent gate enough time to survive a cold API start", async () => {
    await getLegalConsentStatus();

    expect(mockedAuthenticatedRequest).toHaveBeenCalledWith(expect.objectContaining({
      method: "GET",
      path: "/v1/legal/consent-status",
      timeoutMs: 30_000,
    }));
  });

  it("uses the same resilient timeout when accepting mandatory documents", async () => {
    await acceptLegalDocuments([documentId]);

    expect(mockedAuthenticatedRequest).toHaveBeenCalledWith(expect.objectContaining({
      method: "POST",
      path: "/v1/legal/accept",
      body: { accepted: true, document_ids: [documentId] },
      timeoutMs: 30_000,
    }));
  });
});
