"use client";
/**
 * Provider wallet — folded into the Home Services Finance Hub.
 *
 * This page was an orphan: nothing in the sidebar, the dashboard or any other
 * page linked to `/provider/wallet`, so the only way to reach it was to type
 * the URL. It rendered a second view of the SAME account the Finance Hub
 * owns — `/v1/provider/wallet` returns the usage-credit balance
 * (current/reserved/purchased/deducted), and its Ledger and Commissions tabs
 * duplicate the Hub's "Usage Credits" ledger and its commission-rate panel.
 *
 * Two unlinked views of one balance is exactly the duplication this codebase
 * already resolved for `/wallet` and the four `/finance/*` routes, so this
 * follows the same precedent: redirect to the canonical surface rather than
 * maintain a diverging copy. The `/v1/provider/wallet` endpoints are left
 * untouched — they are still read by other callers.
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProviderWalletPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/home-services/finance?tab=usage-credits");
  }, [router]);
  return null;
}
