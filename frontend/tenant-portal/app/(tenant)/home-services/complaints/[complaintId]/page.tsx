"use client";
/** Deep-link route for a single complaint case -- redirects into the queue
 * workspace with the case pre-selected, so /home-services/complaints/{id}
 * and /home-services/complaints/{id}?tab=job-context are both real,
 * refreshable, bookmarkable URLs. */
import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams, useParams } from "next/navigation";

function ComplaintCaseDeepLinkInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = useParams<{ complaintId: string }>();

  useEffect(() => {
    const tab = searchParams.get("tab");
    const qs = new URLSearchParams({ complaint: params.complaintId, ...(tab ? { tab } : {}) });
    router.replace(`/home-services/complaints?${qs.toString()}`);
  }, [params.complaintId, router, searchParams]);

  return null;
}

/**
 * Real build failure fixed here: this page calls `useSearchParams()`, which
 * Next.js requires to sit inside a Suspense boundary. Without one, static
 * prerendering threw "useSearchParams() should be wrapped in a suspense
 * boundary" and FAILED THE WHOLE PRODUCTION BUILD.
 *
 * The boundary is scoped to the page rather than the layout so the rest of
 * the tenant shell keeps prerendering normally.
 */
export default function ComplaintCaseDeepLink() {
  return (
    <Suspense fallback={null}>
      <ComplaintCaseDeepLinkInner />
    </Suspense>
  );
}
