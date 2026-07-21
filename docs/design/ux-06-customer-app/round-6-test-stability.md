# Round 6 Test Stability — 4-Run Sweep

| Run | Install | Mode | Result | Duration |
|---|---|---|---|---|
| 1 | `rm -rf node_modules`, clean `npm install --legacy-peer-deps` | `--runInBand` | 46/46 | 3.07s |
| 2 | (same) | `--runInBand` | 46/46 | 2.74s |
| 3 | (same) | `--runInBand` | 46/46 | 2.76s |
| 4 | (same) | default (parallel workers) | 46/46 | 4.61s |

**Zero failures across all 4 runs, including run 4 under default parallel
workers** — the exact mode that produced a one-time transient timeout back
in Round 2.

## Explicit transient-risk classification (per the brief's instruction)

That Round 2 timeout has **not reproduced in any run across Rounds 3, 4, 5,
or this round's 4-run sweep** (now well over a dozen total independent runs
across sessions). It was never root-caused to a specific line of code — the
defensive fix applied at the time (`testTimeout: 10000` in `package.json`'s
jest config) is the only change made in response to it, and no further
investigation was possible without reproducing it. Per the explicit
instruction not to claim more than the evidence supports: this is classified
as an **observed transient timing risk under parallel test-worker execution,
not fully root-caused, and not reproduced since** — not "fixed" (no
root cause was isolated) and not "never existed" (it did happen once,
genuinely, in Round 2). The current defensive timeout increase is a
reasonable mitigation, not a proven fix.
