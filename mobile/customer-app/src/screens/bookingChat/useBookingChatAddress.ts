import { useCallback, useState, useEffect } from "react";
import { listMyAddresses, createMyAddress } from "../../api/customerAddresses/customerAddressesApi";
import { adaptCustomerSavedAddress } from "../../api/adapters/customerAddresses";
import { setDraftAddress } from "../../api/bookingReview/bookingReviewApi";
import { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { AddressCreatePayload } from "../../domain/addressForm";
import { DomainError } from "../../domain/errors";

/**
 * The address step of the merged booking chat -- kept as its own small
 * hook (not folded into the big controller) since it is genuinely a
 * separate concern with its own loading/submitting/error states.
 *
 * Zipcode enforcement lives here, at the one place addresses are actually
 * offered/created for this draft: every list/create call is scoped to
 * `zipcode`, matching the entry zipcode the provider was already matched
 * against. See setDraftAddress's own doc for why this must never be
 * relaxed without also hardening the backend.
 */
export function useBookingChatAddress(draftId: string | null, zipcode: string) {
  const [addresses, setAddresses] = useState<CustomerSavedAddress[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolvedAddressId, setResolvedAddressId] = useState<string | null>(null);

  /**
   * A NEW draft has no address yet, so every piece of this state must be dropped
   * when `draftId` changes.
   *
   * Real bug this fixes: after a completed booking, starting a fresh request kept
   * the previous draft's `resolvedAddressId`. BookingChatScreen mounts the review
   * phase as soon as that is truthy, so the review controller began loading
   * against a brand-new draft that had no address and no answered questions --
   * its serviceability check failed and the customer saw "Something went wrong
   * while preparing your booking" sitting under the very first question.
   *
   * Keyed on draftId rather than reset by the caller so any future screen gets
   * the same guarantee without having to remember.
   */
  useEffect(() => {
    setResolvedAddressId(null);
    setAddresses(null);
    setError(null);
    setSubmitting(false);
  }, [draftId]);

  const loadAddresses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listMyAddresses();
      setAddresses(res.data.addresses.map(adaptCustomerSavedAddress));
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't load your saved addresses.");
    } finally {
      setLoading(false);
    }
  }, []);

  const pickExisting = useCallback(async (addressId: string) => {
    if (!draftId) return;
    setSubmitting(true);
    setError(null);
    try {
      await setDraftAddress(draftId, addressId);
      setResolvedAddressId(addressId);
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't use that address. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }, [draftId]);

  const createNew = useCallback(async (payload: AddressCreatePayload) => {
    if (!draftId) return;
    // Belt-and-braces: even though AddressTurn locks the zip field, this
    // is the last real gate before a mismatched zip could ever reach the
    // draft (see setDraftAddress's doc -- the backend does not itself
    // reject one).
    if (payload.zipcode !== zipcode) {
      setError("This address must be in the same ZIP this request was matched for.");
      return;
    }
    const normalizedLabel = /work|office/i.test(payload.label) ? "Work" : payload.label;
    const duplicateLabel = (addresses ?? []).some(address => {
      const existingLabel = /work|office/i.test(address.label ?? "") ? "Work" : address.label;
      return existingLabel === normalizedLabel;
    });
    if (duplicateLabel) {
      const displayLabel = normalizedLabel === "Work" ? "Office" : normalizedLabel;
      setError(`Only one ${displayLabel} address can be saved.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createMyAddress(payload);
      await setDraftAddress(draftId, created.data.id);
      setAddresses(current => [adaptCustomerSavedAddress(created.data), ...(current ?? [])]);
      setResolvedAddressId(created.data.id);
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't save that address. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }, [addresses, draftId, zipcode]);

  return { addresses, loading, submitting, error, resolvedAddressId, loadAddresses, pickExisting, createNew };
}
