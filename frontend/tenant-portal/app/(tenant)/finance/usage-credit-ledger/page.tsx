import { redirect } from "next/navigation";

// Consolidated into the Home Services Finance Hub's "Usage Credits" tab —
// the canonical usage-credit wallet and ledger. Previously redirected to
// /packages, a page the sidebar never links.
export default function UsageCreditLedgerPage() {
  redirect("/home-services/finance?tab=usage-credits");
}
