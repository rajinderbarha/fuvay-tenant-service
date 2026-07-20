# Availability / Work Status

Checked `src/lib/api.ts`: `StaffUser.status` is a real **account status** field (e.g. `"active"`), and `Job.status`
is a real **job status**. Neither is a dedicated `available/busy/on_job/off_duty` work-status concept — no such
endpoint exists.

`AvailabilityControl` (new component) renders all four options as selectable chips (local state only, calls
`onChange`) and explicitly displays `accountStatus` and `currentJobStatus` as two **separate, clearly labeled**
fields alongside it — proving the three concepts (work status / account status / job status) are never merged
into one value, per the hard constraint. Wired into the extended `ProfileScreen`.

No leave-approval, attendance, payroll, timesheet, or GPS-tracking concept was built or implied — none was asked
for and none has any backend evidence.
