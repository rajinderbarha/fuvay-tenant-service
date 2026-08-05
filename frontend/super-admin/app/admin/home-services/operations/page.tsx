"use client";
// Old URL kept as a redirect after the route was renamed to
// /admin/home-services/bookings-jobs (2026-08-04, self-descriptive URL per
// explicit user request) -- avoids breaking any bookmarked/external link.
import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LegacyOperationsRedirect() {
  return (
    <Suspense fallback={null}>
      <Redirector />
    </Suspense>
  );
}

function Redirector() {
  const router = useRouter();
  const params = useSearchParams();
  useEffect(() => {
    router.replace(`/admin/home-services/bookings-jobs?${params.toString()}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}
