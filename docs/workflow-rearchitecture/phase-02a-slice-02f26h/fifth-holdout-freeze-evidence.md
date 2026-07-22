# Fifth Holdout Freeze Evidence — Slice 2F-26H

| Artifact | Hash |
|---|---|
| Eligible population (27) | `2d206d745cadb84b` |
| Holdout manifest (24) | `d968bad8957a7159` |
| Reserve set (3) | `9c73ee22f54d71ac` |
| Manual verdicts | `3efb58958c74aae8` |
| Evidence review | `9d7707a11ec0ee66` |
| Action model | `920e6b4c3e912673` |
| Authority model 26H | `a4543c70ceb198c9` |
| Canonical | `45244cd9540456db` |
| Matrix | `4c7c3bce02096a43` |

Ordering: eligible population and manifest frozen, then manual verdicts +
evidence review frozen, then — and only then — the classifier was run. Manifest
and manual hashes are asserted in tests, so the ordering is falsifiable. No
route was replaced after disagreement. Holdout disjoint from all four burned
corpora (96 union, 0 overlap).
