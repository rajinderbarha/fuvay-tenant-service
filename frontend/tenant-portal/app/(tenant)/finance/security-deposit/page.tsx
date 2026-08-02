import { redirect } from "next/navigation";

// Consolidated into /packages ("Security Deposit" tab) alongside package
// selection, top-up, and the credit ledger -- one Billing page instead of
// four separate sidebar entries showing overlapping account data.
export default function SecurityDepositPage() {
  redirect("/packages");
}
