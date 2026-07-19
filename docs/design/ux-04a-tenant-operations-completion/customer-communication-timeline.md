# Customer Communication Timeline (UX-04A)

No change to `CustomerCommunicationTimeline`/`CommunicationEventView` this
pass. New test coverage (`CustomerCommunicationTimeline.test.tsx`) asserts
a `customerVisible: false` event is marked "(internal only)" in the
rendered output, and a failed+retryable event shows the retry hint —
codifying the "internal notes never presented as customer-visible"
guarantee as an executable test.
