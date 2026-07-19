# Customer / Complaint Pattern

`/dev/ux-03/customers-complaints`. Customer contact info is masked by
default (`maskedPhone`/`maskedEmail` in `CustomerFixture`). Complaints
render `providerCanRespond` as the ceiling of provider authority — no
"resolve"/"reject dispute" action is ever implied; final adjudication
belongs to the platform (see task brief's product-rule constraint).
