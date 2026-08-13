"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LegacyFinanceWalletsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/home-services/finance?tab=credits&credits_tab=accounts`);
  }, [router]);
  return null;
}
