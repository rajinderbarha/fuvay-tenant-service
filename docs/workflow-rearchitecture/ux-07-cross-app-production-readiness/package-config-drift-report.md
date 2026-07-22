# Package/Config Drift Report — UX-07 Pass 3d

Per this pass's explicit drift-guard instruction (a prior real incident in
this exact repo: Expo dev tooling auto-downgraded SDK 56→54 and
react/react-native versions), `app.json` and `package.json` were diffed
against `git HEAD` before AND after every install/typecheck/test command
run this pass.

## Result: guard held, zero drift

```
$ git diff --stat mobile/customer-app/app.json mobile/customer-app/package.json
(empty — no output, no changes)
```

Confirmed at the start of this pass (pre-flight) and re-confirmed after the
final WSL `npm install`, after every `npx tsc --noEmit` run, and after
every `npx jest` run (13 total test invocations across this pass) against
the real worktree file — the WSL copy used for install/typecheck/test is a
disposable `rsync` copy at `~/work/customer-app`, never the source of
truth; only the real worktree's `git diff` result was used to judge drift.

## Untracked files left alone

`mobile/customer-app/.expo/` and `mobile/customer-app/package-lock.json`
were the two expected pre-existing untracked entries named in this task's
brief. Neither was added, modified, or committed this pass — confirmed via
`git status --short mobile/customer-app` after every commit, which shows
only those two entries as untracked throughout.

## What was committed

Exactly 8 source/test files across 3 commits (`13c818f`, `be43db2`,
`b3a0fa0`) — see `customer-source-change-report.md` for the full list. No
`package.json`, `package-lock.json`, `app.json`, or `eas.json` change is
part of any commit this pass.

## Pass 3f addendum

Verified before AND after this pass's install/build/typecheck/export
commands: `mobile/customer-app/app.json` and
`mobile/customer-app/package.json` show **zero diff** against git HEAD
(`git diff --stat` empty for both). Drift guard held throughout —
Expo SDK / react / react-native / react-test-renewer versions were
never altered by any command run this pass (fresh WSL npm install, jest
runs, tsc, expo export).
