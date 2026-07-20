# CUSTOMER-L5-13 — Location Event Contract

## No Real Location-Event Model Exists for This Pipeline

Per `baseline-verification.md`'s Central Findings #4 and
`contract-matrix.md`: no live-location/GPS coordinate event model is
reachable from the real `home_service_booking`/`home_service_assignment`/
`execution` pipeline. The real, orphaned `geo.StaffLocation` table (upsert,
not append-only — `latitude`, `longitude`, `accuracy_m`, `last_ping_at`)
exists but is never written to for any technician assigned through this
app's real booking flow.

## Consequence

Every requirement in the spec's §24 (Location Update Model), §25
(Coordinate Precision), §29 (Stale Location Detection), and §30 (Location
Update Ordering) is `NOT_APPLICABLE` for this sprint — there is no real
location payload of any kind to validate, order, deduplicate, or apply
precision rules to. This sprint's code contains no coordinate parsing,
no latitude/longitude validation, and no staleness-threshold logic, since
building any of it would be speculative code against a data source that
does not exist for real customers today.

## What This Sprint Uses Instead: The Real Execution-Event Timeline

The one real, structurally analogous data source is
`ServiceJobExecutionEvent` (discrete, timestamped milestone events, not
continuous coordinates) — see `timeline-contract.md` for its full,
real contract. This is a fundamentally different data shape (discrete
status milestones vs. continuous position updates) and this sprint does
not conflate the two or attempt to simulate continuous tracking from
discrete events (e.g., no fake "technician is X% of the way there"
interpolation).

## Privacy (Still Applicable, Even Without Coordinates)

Per §46's location-privacy requirements: even though no coordinates
exist, this sprint still applies the same discipline to the real data it
does handle — the execution timeline's own `notes` field (which could
theoretically contain free-text location-adjacent staff commentary) is
never rendered or logged (`contract-matrix.md`'s disclosed mitigation for
the unfiltered `notes` field). No coordinate-shaped data appears in any
`logger.*` call, analytics event, or route param anywhere in
`features/service-tracking/` — verified by grep (there is none to leak in
the first place).
