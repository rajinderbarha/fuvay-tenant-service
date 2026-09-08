"use client";
import { Btn } from "../shared/ui";
import { WEEK_DAYS, dayError, type DayDraft } from "../../lib/coverage-schedule";
import { allocateDailySlots, twoHourWindows } from "../../lib/booking-capacity";

export function WeeklyScheduleEditor({ days, capacity, buffer, timezone, saving, onChange }: {
  days: DayDraft[]; capacity: number; buffer: number; timezone: string; saving: boolean;
  onChange: (day: number, values: Partial<DayDraft>) => void;
}) {
  return <>
    <p className="cov-hint">Timezone: {timezone}. All technicians inherit these business hours, breaks and holidays, including future schedule changes.</p>
    <p className="cov-hint">Two-hour jobs · {capacity} active, funded technicians · up to {capacity} simultaneous bookings. Staff and managers do not add booking capacity.</p>
    {capacity === 0 && <p role="status" className="cov-day-error">No funded, active technicians yet. You can save hours, but customer slots stay unavailable until technicians are ready.</p>}
    {days.map(day => {
      const name = WEEK_DAYS[day.day_of_week];
      const invalid = dayError(day, capacity, buffer);
      const windows = twoHourWindows(day.start_time, day.end_time, day.break_start_time, day.break_end_time, buffer);
      const maximum = windows.length * capacity;
      const allocations = allocateDailySlots(windows, capacity, day.max_jobs_per_day === "" ? null : Number(day.max_jobs_per_day));
      return <section key={day.day_of_week} id={`schedule-day-${day.day_of_week}`} className="cov-day-row" aria-label={`${name} schedule`}>
        <div className="cov-day-head"><strong style={{fontSize:13}}>{name}</strong>
          <label><input type="checkbox" aria-label={`${name} open`} disabled={saving} checked={day.is_active}
            onChange={e => onChange(day.day_of_week, { is_active: e.target.checked })}/>{day.is_active ? "Open" : "Closed"}</label>
        </div>
        {day.is_active ? <>
          <div className="cov-fields">
            <label className="cov-field">Opening time<input type="time" step={60} aria-label={`${name} opening time`} disabled={saving}
              value={day.start_time} onChange={e => onChange(day.day_of_week, { start_time: e.target.value })}/></label>
            <label className="cov-field">Closing time<input type="time" step={60} aria-label={`${name} closing time`} disabled={saving}
              value={day.end_time} onChange={e => onChange(day.day_of_week, { end_time: e.target.value })}/></label>
            <label className="cov-field">Daily job limit<input type="number" min={1} aria-label={`${name} daily job limit`} disabled={saving}
              value={day.max_jobs_per_day} placeholder={`Automatic (${maximum})`} onChange={e => onChange(day.day_of_week, { max_jobs_per_day: e.target.value })}/></label>
          </div>
          <div className="cov-fields">
            <label className="cov-field">Break starts (optional)<input type="time" step={60} aria-label={`${name} break start`} disabled={saving}
              value={day.break_start_time} onChange={e => onChange(day.day_of_week, { break_start_time: e.target.value })}/></label>
            <label className="cov-field">Break ends (optional)<input type="time" step={60} aria-label={`${name} break end`} disabled={saving}
              value={day.break_end_time} onChange={e => onChange(day.day_of_week, { break_end_time: e.target.value })}/></label>
            {(day.break_start_time || day.break_end_time) && <Btn variant="secondary" disabled={saving}
              onClick={() => onChange(day.day_of_week, { break_start_time: "", break_end_time: "" })}>Remove break</Btn>}
          </div>
          {invalid ? <p role="alert" className="cov-day-error">{invalid}</p> : <>
            <p className="cov-hint">{windows.length} two-hour windows per technician × {capacity} technicians = up to {maximum} jobs/day.
              {buffer > 0 ? ` Includes ${buffer} minutes travel buffer between jobs.` : " No travel buffer."} Leave the daily limit blank for Automatic.</p>
            <div className="cov-chips" aria-label={`${name} draft slot capacities`}>{allocations.map(slot => <span key={slot.window}>{slot.window} · {slot.capacity} {slot.capacity === 1 ? "place" : "places"}</span>)}</div>
          </>}
        </> : <><p className="cov-hint" style={{marginBottom:0}}>No bookings on {name}. Reopening keeps your saved hours.</p>
          {invalid && <p role="alert" className="cov-day-error">{invalid} Reopen this day to correct its hours.</p>}</>}
      </section>;
    })}
  </>;
}
