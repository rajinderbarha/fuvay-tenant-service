# Customer App — Customer Profile

## Model

There is no dedicated "customer profile" backend model — customer accounts
are rows in the shared `User` table (`role: "customer"`), so
`CustomerSession` (see `authentication-architecture.md`) doubles as the
profile model. See `CUSTOMER-L5-02-backend-contract-audit.md` for the exact
field list.

## Screen

`features/auth/screens/ProfileScreen.tsx`:

- Avatar (initials fallback via `customerInitials()` — no fake photo).
- Editable full name (`AppTextField`, min length 2, matches the backend's
  own `Field(min_length=2, max_length=255)`), saved via
  `PUT /v1/auth/me`.
- Read-only phone display (changing phone requires re-verification on the
  backend — no UI for that this sprint, since it needs a second OTP flow
  not yet built).
- Sign-out action (`useLogout`).

## Mutation

`features/auth/queries/profile-queries.ts#useUpdateProfile` — a TanStack
Query mutation (CUSTOMER-L5-00's query-client) that, on success, patches
the in-memory session (`updateSessionProfile`) rather than re-fetching
`/v1/auth/me`, since the mutation response already contains the updated
profile.

## Not Implemented This Sprint

- Avatar upload (`avatar_url` field exists on the backend and in
  `CustomerSession`, but no image-picker-backed upload flow was built —
  `AppAvatar`'s `imageUrl` prop is wired but nothing sets it yet).
- Phone number change (requires OTP re-verification — no product
  requirement given this sprint).
- Email field is read from the backend but not editable (customer accounts
  are provisioned with a synthetic `customer_<uuid>@serviceos.internal`
  email when no real email is given at registration — editing it isn't
  meaningful without a verification flow).
- Language/timezone display exists in the model but no UI reads/writes it
  yet (locale preference is currently driven by CUSTOMER-L5-00's device-
  detected/persisted locale, not the backend profile's `language` field —
  reconciling the two is deferred).
