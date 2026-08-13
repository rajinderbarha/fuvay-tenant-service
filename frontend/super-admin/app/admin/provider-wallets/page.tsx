"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Legacy URL retained for bookmarks; usage credits now have one workspace. */
export default function LegacyProviderWalletsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/home-services/finance?tab=credits&credits_tab=accounts`);
  }, [router]);
  return null;
}
