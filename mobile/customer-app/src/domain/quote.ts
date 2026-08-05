import { QuoteId, ServiceJobId } from "./ids";
import { QuoteStatus } from "./status";
import { Money } from "./money";
import { ServerTimestamp } from "./dates";

export interface Quote {
  id: QuoteId;
  jobId: ServiceJobId;
  status: QuoteStatus;
  amount: Money | null;
  visitFee: Money | null;
  notes: string | null;
  expiresAt: ServerTimestamp | null;
  createdAt: ServerTimestamp | null;
}
