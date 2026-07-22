# Route Enumeration Method

Same method as Slice 2F-39A: `list_routes.py` / `inventory_mutation_routes.py`
re-run fresh, then manual source inspection (`grep` for `Depends(` patterns
per router file, cross-referenced against each endpoint's actual guard) for
the 4 target modules named in this slice's mission
(`field_ops.router`, `platform_commerce.router`, `pricing.router`,
`security.router`). Where a guard's behavior was ambiguous or looked
wrong, the corresponding service method was read directly (not assumed)
— this is how the `create_api_key` defect and the 2 read-path privacy
observations were found: by tracing actual service-layer code, not by
trusting the router decorator alone.
