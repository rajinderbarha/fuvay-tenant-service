"use client";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { FIXTURE_FINANCE_TRANSACTIONS } from "../../../../lib/ux03/fixtures";
import type { FinanceTransactionFixture } from "../../../../lib/ux03/types";

export default function FinanceHistory() {
  return (
    <TenantListPage<FinanceTransactionFixture>
      title="Finance History"
      description="Transaction table with filters (export presentation only — no invented mutation actions)."
      rows={FIXTURE_FINANCE_TRANSACTIONS}
      rowKey={(t) => t.id}
      columns={[
        { key: "kind", header: "Type", accessor: (t) => t.kind },
        { key: "amount", header: "Amount", render: (t) => `₹${t.amount.toLocaleString()}` },
        { key: "at", header: "Date", render: (t) => new Date(t.at).toLocaleDateString() },
        { key: "note", header: "Note", accessor: (t) => t.note },
      ]}
    />
  );
}
