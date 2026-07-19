# Shared Package Regression Report

`@serviceos/design-system` source unchanged this pass except the
already-recorded Tooltip fix from UX-04A (unchanged, not reopened). Its
own test suite re-ran and still passes 18/18 (`ux01-forward-certification.md`).
No shared-package regression introduced by this pass's tenant-portal-local
react version fix — `@serviceos/design-system`'s peerDependency
(`"react": ">=19.0.0"`) already accepted 19.2.7 before this fix; the fix
only changed which version *tenant-portal's own* `package.json` requests,
converging it onto the version design-system's consumers already used.
