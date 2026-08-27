import { redirect } from "next/navigation";

export default function RetiredPrivacyPage() {
  redirect("/provider/compliance?tab=consents");
}
