# Environment Blocker Report

Identical blocker to UX-01, reproduced once (not looped) in this phase's Step 0:

1. **Node/OpenSSL bug**: `ERR_SSL_CIPHER_OPERATION_FAILED` /
   `ossl_gcm_stream_update:cipher operation failed` during large package downloads/extraction
   over TLS. This is a known class of Node.js OpenSSL provider bug on some Windows builds.
2. **Antivirus file-lock bug**: real-time scanning locks files mid-extraction, causing npm's own
   cleanup step to fail with `EPERM`/`ENOTEMPTY` on `node_modules/@next/swc-win32-x64-msvc` and
   `node_modules/next/**`.

Both were previously hit 35+ times across two UX-01 sessions with no successful install. Per this
phase's explicit instruction, it was NOT retried in a loop — one attempt was made, it failed
identically, and the task fell back to source-only work (MODE B) immediately.

## Suggested remediations for a future session (not attempted here, out of scope)
- Run the install on a machine/VM without the AV real-time scanner, or with an exclusion added for
  the repo's `node_modules` paths (requires the user's/IT's action, not something this phase can
  configure).
- Try an older/newer Node.js version where the OpenSSL provider bug is not present.
- Use `npm config set fetch-retries` / a proxy-less registry mirror if the SSL failure is
  network-intermediary related rather than purely local OpenSSL.
