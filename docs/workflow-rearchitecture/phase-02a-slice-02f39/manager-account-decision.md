# manager@demo-ac-services.local — Decision Packet

| Field | Value |
|---|---|
| Current invalid role | `tenant_manager` |
| Tenant | demo-ac-services (`5209ef33-a53e-4fc0-b3f6-006335b8d712`) |
| Existing purpose (from evidence) | Only `full_name`="Tenant Manager" and email local-part "manager" — both explicitly disallowed as sufficient evidence per the governing rule against name-similarity inference |
| Login documentation | None — zero logins ever |
| UI expectations | None — never successfully authenticated |
| Test expectations | None reference this account's role by name |
| Current permissions | **Zero** — `tenant_manager` absent from `ROLE_PERMISSIONS` |
| Current access scope | N/A |
| Usage | Zero logins, zero sessions, zero audit records, zero team-member profile, zero assigned work — an entirely inert demo-seed artifact |
| Candidate canonical roles | `staff` — plausible given `full_name`, no elevated risk |
| Privilege comparison | `staff`: tenant-scoped operational permissions, lowest-privilege tenant role |
| Risk of mapping to `staff` | Low — matches apparent intent; zero real users affected since the account has never been used |
| Recommended choice | `staff`, **contingent on human confirmation** this demo account is intended as a non-owner tenant staff user |
| Exact human decision required | "Confirm `manager@demo-ac-services.local` is intended as a `staff`-role demo account for tenant demo-ac-services, or specify it should be deactivated instead." |

**Outcome: `MANUAL_ROLE_CONFIRMATION_REQUIRED`.** A plausible recommendation
exists (unlike readonly@), but confirmation must come from a human with
actual knowledge of this demo tenant's intended setup.
