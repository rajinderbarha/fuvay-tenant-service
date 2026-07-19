# Customer Communication Timeline

Built: `components/ux04/CustomerCommunicationTimeline.tsx`, used in Job
Detail Workspace, type `CommunicationEventView`.

Every event carries `kind`, `at`, `actorName`, `channel`, `deliveryState`,
`customerVisible`, `failureCanRetry`. The component explicitly marks
`customerVisible === false` events with an "(internal only)" tag so a
staff viewer never mistakes an internal note for something the customer
actually saw — this was called out as a specific hard requirement in the
brief and is enforced in the component, not just documented. Failed
deliveries render a "Retry available" hint only when
`failureCanRetry` is true; no outbound send action is wired (typed
contract only, `Ux04OperationsAdapter.listCommunication` has no `send`
method by design this pass).
