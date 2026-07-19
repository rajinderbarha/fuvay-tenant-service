# UX-02 Execution Mode

## Mode: MODE B (build-blocked)

## Evidence

Command run:
```
cd frontend/super-admin && npm install --no-audit --no-fund
```

Output (tail):
```
npm warn cleanup Failed to remove some directories [...]
npm warn cleanup   [Error: ENOTEMPTY: directory not empty, rmdir '...\node_modules\@next\swc-win32-x64-msvc']
npm warn cleanup   [Error: EPERM: operation not permitted, unlink '...\node_modules\next\dist\esm\server\app-render\collect-segment-data.js']
npm error code ERR_SSL_CIPHER_OPERATION_FAILED
npm error 98110000:error:1C800066:Provider routines:ossl_gcm_stream_update:cipher operation failed:c:\ws\deps\openssl\openssl\providers\implementations\ciphers\ciphercommon_gcm.c:325:
```

This reproduces exactly the same two compounding failure modes documented in UX-01
(`docs/design/ux-01-foundation/`): (1) Node/OpenSSL `ERR_SSL_CIPHER_OPERATION_FAILED` during
large package extraction, and (2) antivirus real-time-scanning file locks causing
EPERM/ENOTEMPTY during npm's own cleanup of partially-extracted packages
(`@next/swc-win32-x64-msvc`, `next`).

Per task instructions, this was attempted exactly ONCE (not looped) and the fallback to
MODE B was taken immediately per the "don't retry 35 more times" instruction.

## Consequence

- No `npm install`, `tsc`, `vitest`, or `next build` will be run for this phase.
- All work is done at the source level (TypeScript/TSX files, fixtures, docs) with careful
  manual review for type/import correctness.
- `frontend-test-report.md` and `build-report.md` will explicitly say NOT EXECUTED and list
  the exact commands a future engineer (on a machine without this AV/OpenSSL issue) should run.
