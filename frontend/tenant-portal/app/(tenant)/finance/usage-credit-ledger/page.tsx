import { redirect } from "next/navigation";

// Consolidated into /packages ("Credit Ledger" tab) alongside package
// selection, top-up, and security deposit -- one Billing page instead of
// four separate sidebar entries showing overlapping account data.
export default function UsageCreditLedgerPage() {
  redirect("/packages");
}
