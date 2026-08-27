import { z } from "zod";
import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";

const eventResponseSchema = z.object({ recorded: z.boolean() });
const eventBatchResponseSchema = z.object({ recorded: z.number().int().nonnegative() });

export type HomeCampaignEventType = "delivered" | "opened" | "clicked";

export async function recordHomeCampaignEvent(input: {
  campaignId: string;
  eventType: HomeCampaignEventType;
  placement?: string | null;
  sessionId?: string | null;
}) {
  const response = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/home/campaigns/${encodeURIComponent(input.campaignId)}/events`,
    body: {
      event_type: input.eventType,
      placement: input.placement ?? null,
      session_id: input.sessionId ?? null,
    },
  });
  return parseApiSuccess(response.json, eventResponseSchema);
}

export async function recordHomeCampaignEvents(inputs: Array<{
  campaignId: string;
  eventType: HomeCampaignEventType;
  placement?: string | null;
  sessionId?: string | null;
}>) {
  if (inputs.length === 0) return { recorded: 0 };
  const response = await authenticatedRequest({
    method: "POST",
    path: "/v1/customer/home/campaigns/events/batch",
    body: {
      events: inputs.map(input => ({
        campaign_id: input.campaignId,
        event_type: input.eventType,
        placement: input.placement ?? null,
        session_id: input.sessionId ?? null,
      })),
    },
  });
  return parseApiSuccess(response.json, eventBatchResponseSchema);
}
