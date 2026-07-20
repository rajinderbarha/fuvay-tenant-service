# Job Media Pattern

`MediaCaptureGrid` (new this session) enforces the two hard constraints from the brief:
1. **Never renders storage keys / signed URLs / bucket names / credentials** -- `JobMediaView` (typed in the
   previous session) carries none of those fields at all; there is nothing for the component to leak even by
   accident.
2. **Never marks an item "Uploaded" before backend confirmation** -- the displayed label checks
   `confirmedByBackend`, not just `uploadState === "confirmed"`. An item can be optimistically in `uploadState:
   "confirmed"` (client believes the network call succeeded) while `confirmedByBackend` is still `false`; the
   component always renders the more conservative of the two.

No camera/gallery picker library is wired in (`expo-image-picker` is not a current dependency) -- "Add" appends a
placeholder draft item to local state. This is `MOCK_DESIGN_ONLY`/`API_CONTRACT_REQUIRED` end-to-end (no live
media endpoint exists), consistent with the honesty pattern established by the Parts Request showcase.
