"use client";
/**
 * Legacy /reviews — superseded by /home-services/reviews.
 *
 * This page rendered the OLD review engine (`reviewsApi` -> the orphaned
 * legacy `reviews` table), which is a different table from the canonical
 * Sprint 24 `customer_reviews`/`review_replies`/`review_flags` system that
 * every current surface reads and writes. Nothing writes to the legacy table
 * any more (MODULE-L5-13 repointed customer ratings at the canonical engine),
 * so this page could only ever render an empty list -- and its reply box
 * posted into a table no provider, admin or aggregation dashboard reads.
 *
 * The live sidebar already points at /home-services/reviews, so the only way
 * here is a stale bookmark or a hand-typed URL. Redirecting preserves those
 * entry points instead of showing a permanently blank screen. Query params
 * are carried through so a deep link like ?review_id=… still lands correctly.
 */
import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function LegacyReviewsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const qs = searchParams.toString();
    router.replace(`/home-services/reviews${qs ? `?${qs}` : ""}`);
  }, [router, searchParams]);

  return null;
}

export default function LegacyReviewsPage() {
  // useSearchParams() must sit inside a Suspense boundary or static
  // prerendering fails the production build.
  return (
    <Suspense fallback={null}>
      <LegacyReviewsRedirect />
    </Suspense>
  );
}
