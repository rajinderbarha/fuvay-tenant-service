# Regression Report - Slice 2F-27A

Before: baseline suite green at 214/257. Edit added 2 canonical rows + 2 matrix
rows. 19 test assertions across the current suite pinned the old 257/43/hash;
all were rebaselined to 259/45/new-hash (current executable assertions;
historical slice DOCS unchanged).

Final: full phase-2F suite 2136 passed, 0 failed, 0 errors.
- New failures: none (all rebaselined)
- Resolved failures: 19 (the intended count/hash moves) + 4 residual arithmetic
- Unchanged failures: none
- New errors: none
No application behaviour changed.
