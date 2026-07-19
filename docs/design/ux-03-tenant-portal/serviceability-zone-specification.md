# Serviceability / Zone Specification

Entities: city, district, postal code, zone, service-area
(`ServiceAreaFixture`). Coverage overview shows `covered` / `partial` /
`not_covered` / `conflict` per row (see `/dev/ux-03/service-areas`).
Because geo authorization is only closed for a frozen slice, each row
carries its own `mutationReadiness` (`ReadinessState`) rather than a single
page-wide flag — some rows may be `READ_ONLY_READY` for viewing while their
edit action stays `PRODUCT_DECISION_REQUIRED`.
