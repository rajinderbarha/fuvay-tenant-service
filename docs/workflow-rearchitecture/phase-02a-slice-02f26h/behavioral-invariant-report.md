# Behavioral Invariant Report — Slice 2F-26H

Verified: job-close still creates a review request; legacy reviews POST still
returns 410; StaffPermission grant admits, explicit deny overrides, unrelated
grant does not widen, unknown role fails closed. All in the 26H test suite.
No authorization behaviour changed this slice.
