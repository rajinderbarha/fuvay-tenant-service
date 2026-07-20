# Schedule Specification

`ScheduleScreen` (new, `src/screens/ux05/ScheduleScreen.tsx`) is real and wired to `jobsApi.myJobs()` -- no
mock data. It groups client-side into **Today** and **Upcoming** by `scheduled_date` (the only date field the
real `Job` shape carries).

## Not built this pass
- Day/Agenda toggle views (brief workstream 7 mentions Today/Day/Agenda/Upcoming) -- only Today/Upcoming exist.
- Conflict detection: `ScheduleItemView.hasConflict` is typed and rendered by `ScheduleCard` (a red "⚠ Conflict"
  chip) but always computed as `false` today -- no overlap-detection logic was implemented (would need comparing
  `scheduled_time_window` strings across jobs, deferred).
- No route optimization / travel-time calculation was built or implied (explicitly out of scope per the brief).
- No device-calendar integration was built or implied (same).

Shared by both Technician and Staff tab sets (same screen, same real data source) -- both roles see their own
assigned jobs; there is no tenant-wide schedule view for staff (would require the not-yet-existing work-queue
endpoint).
