import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../../services/maskedCalling/maskedCallingApi";
import type { MaskedContactDTO } from "../../services/maskedCalling/maskedCallingApi";
import type { AppError } from "../../services/api/types";

/**
 * Drives the "Call customer" affordance on a job.
 *
 * Calling capability is decided ENTIRELY by the backend (`can_call` /
 * `cannot_call_reason`) -- this hook never infers it from job status or from a
 * phone number being present, because there is no phone number to inspect. If
 * the backend says a call cannot be placed, the reason is surfaced verbatim
 * rather than the UI inventing a fallback contact route.
 *
 * `placeCall` is guarded against double-tap: each press dials a real phone, so
 * a duplicate is a customer's phone ringing twice, not a harmless retry.
 */
export function useMaskedCall(jobId: string) {
  const [contact, setContact] = useState<MaskedContactDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [calling, setCalling] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const mounted = useRef(true);
  // Synchronous double-tap guard. State cannot do this job: two presses in the
  // same tick both close over `calling === false` and both would dial, which
  // means the customer's phone rings twice. A ref updates immediately.
  const inFlight = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    // `authenticatedRequest` RETURNS a discriminated result rather than
    // throwing, so failures must be branched on -- a try/catch here would
    // treat every error as a success carrying undefined data.
    const res = await api.getContact(jobId, signal);
    if (!mounted.current) return;
    if (res.ok) setContact(res.data);
    else setError(res.error);
    setLoading(false);
  }, [jobId]);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  const placeCall = useCallback(async () => {
    if (inFlight.current) return null;
    inFlight.current = true;
    setCalling(true);
    setError(null);
    let res;
    try {
      res = await api.callCustomer(jobId);
    } finally {
      inFlight.current = false;
    }
    if (!mounted.current) return null;
    if (!res.ok) {
      setError(res.error);
      setCalling(false);
      return null;
    }
    // The platform now rings the technician first, then joins the customer.
    // Re-read contact so `connected_before` / `last_call` reflect the new
    // session rather than a stale snapshot.
    await refresh();
    if (mounted.current) setCalling(false);
    return res.data;
  }, [jobId, refresh]);

  return { contact, loading, calling, error, placeCall, refresh };
}
