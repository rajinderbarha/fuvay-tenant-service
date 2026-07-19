# Unverified Frontend Gates

No route in this phase was verified against a running dev server or
browser (Mode B). Every "READ_ONLY_READY" claim in
readiness-state-registry.csv is based on the existence of a matching
backend engine/router in `app/engines/**`, not a confirmed live response
shape. Treat all readiness states as engineering estimates pending a real
integration pass.
