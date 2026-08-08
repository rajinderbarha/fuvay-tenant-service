import { useEffect, useRef, useState } from "react";
import * as reviewApi from "../../api/bookingReview/bookingReviewApi";
import { adaptServiceChecklist } from "../../api/adapters/serviceChecklist";
import { ServiceChecklist } from "../../domain/serviceChecklist";

/**
 * Loads the real checklist points for this booking's service.
 *
 * Deliberately NON-BLOCKING and silent on failure: this card is reassurance, not
 * a step the booking depends on. If the request fails, or the service has
 * nothing authored, the flow moves on rather than stopping a customer from
 * booking over a display-only extra. The error is kept for diagnostics but the
 * caller is expected to treat `checklist === null` as "skip this turn".
 */
export function useServiceChecklist(draftId: string) {
  const [checklist, setChecklist] = useState<ServiceChecklist | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // `parseApiSuccess` returns { data, requestId } -- the DTO is on .data.
        const res = await reviewApi.getServiceChecklist(draftId);
        if (!cancelled && mounted.current) setChecklist(adaptServiceChecklist(res.data));
      } catch {
        // Non-fatal by design -- see hook doc.
        if (!cancelled && mounted.current) setChecklist(null);
      } finally {
        if (!cancelled && mounted.current) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [draftId]);

  return { checklist, loading };
}
