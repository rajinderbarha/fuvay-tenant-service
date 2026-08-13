import { redirect } from "next/navigation";

type LegacyQuery = Record<string, string | string[] | undefined>;

export default async function LegacyUsageCreditsRedirect({
  searchParams,
}: {
  searchParams: Promise<LegacyQuery>;
}) {
  const incoming = await searchParams;
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(incoming)) {
    if (Array.isArray(value)) value.forEach(item => next.append(key, item));
    else if (value !== undefined) next.set(key, value);
  }
  next.set("tab", "credits");
  next.set("credits_tab", "ledger");
  redirect(`/admin/home-services/finance?${next.toString()}`);
}
