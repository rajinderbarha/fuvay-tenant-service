import { redirect } from "next/navigation";

/** Retained only so old bookmarks cannot reopen the retired tenant AI chat. */
export default function RetiredTenantAiChatPage() {
  redirect("/dashboard");
}
