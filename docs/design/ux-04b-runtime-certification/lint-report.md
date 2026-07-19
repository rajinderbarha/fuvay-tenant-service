# Lint Report (UX-04B)

Re-verified: `next lint` still does not exist as a subcommand in
Next.js 16.2.9 (`npx next --help` lists no `lint` command; running `npm
run lint` fails with "Invalid project directory provided, no such
directory: .../lint"). **NOT_CONFIGURED**, confirmed again this pass, not
fabricated. No lint tooling was added this pass — a real ESLint setup
compatible with Next 16 (flat config + `eslint-config-next`) remains a
deferred item (`deferred-items.md`), out of scope for this narrow
correction pass.
