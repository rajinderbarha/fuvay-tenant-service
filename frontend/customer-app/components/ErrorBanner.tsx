"use client";
import { CustomerApiError } from "../lib/api/client";

/** Renders the generic friendly-error + request_id copy required by spec.
 *  Never renders stack traces or raw backend JSON. */
export default function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  let message: string;
  let requestId: string | undefined;
  if (error instanceof CustomerApiError) {
    message = error.message;
    requestId = error.requestId;
  } else if (error instanceof Error) {
    message = error.message;
  } else {
    message = "We couldn't complete this action. Please try again or contact support.";
  }
  return (
    <div className="co-error-banner" role="alert">
      {message}
      {requestId && !message.includes(requestId) ? ` (Request ID: ${requestId})` : ""}
    </div>
  );
}
