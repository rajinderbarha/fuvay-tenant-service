# Booking-to-Job Transition Contract

Type: `BookingToJobTransitionView` (`lib/ux04/types.ts`) —
`sourcePipeline`, `sourceBookingId`, `condition`
(`"not_yet_transitioned" | "transitioned" | "duplicate_prevented" |
"validation_failed"`), `resultingModel` (`"field_ops.Job" | "ServiceJob" |
null`), `resultingJobId`, `existingJobLink` (`EntityLinkView | null`),
`validationNotes: string[]`.

This is a **read-only presentation of an already-decided transition**, not
an active resolution engine — no UI action mutates the transition state.
Duplicate-prevention is presented (`condition === "duplicate_prevented"`)
as an explanatory state, never as something the user resolves in-app.

No showcase route renders this type standalone this pass; it is embedded
in `BookingDetailView.jobTransition` for future wiring into the deferred
booking-detail route.
