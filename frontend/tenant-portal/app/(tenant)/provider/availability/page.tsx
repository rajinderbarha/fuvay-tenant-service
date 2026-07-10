"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AvailabilityRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/tenant/setup/availability"); }, [router]);
  return (
    <div style={{ padding:32, textAlign:"center", color:"var(--text-secondary)", fontSize:13 }}>
      Redirecting to Business Hours &amp; Availability…
    </div>
  );
}
