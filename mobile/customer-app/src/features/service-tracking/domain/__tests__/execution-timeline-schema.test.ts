import { parseExecutionTracking } from "../execution-timeline-schema";

describe("parseExecutionTracking", () => {
  it("accepts a real, in-progress execution timeline", () => {
    const result = parseExecutionTracking({
      job: { id: "j-1", status: "on_the_way" },
      notes: [],
      media: [],
      timeline: [
        {
          id: "e-1",
          job_id: "j-1",
          event_type: "job_scheduled",
          old_status: "accepted",
          new_status: "scheduled",
          notes: null,
          actor_role: "staff",
          created_at: "2026-07-13T09:00:00Z",
        },
        {
          id: "e-2",
          job_id: "j-1",
          event_type: "technician_on_the_way",
          old_status: "scheduled",
          new_status: "on_the_way",
          notes: "internal note",
          actor_role: "staff",
          created_at: "2026-07-13T10:00:00Z",
        },
      ],
    });
    expect(result?.status).toBe("on_the_way");
    expect(result?.timeline).toHaveLength(2);
  });

  it("structurally strips internal fields (notes, actor_role, id, job_id) from each timeline event", () => {
    const result = parseExecutionTracking({
      job: { id: "j-1", status: "on_the_way" },
      timeline: [
        {
          id: "e-1",
          job_id: "j-1",
          event_type: "technician_on_the_way",
          notes: "internal staff note",
          actor_role: "staff",
          created_at: "2026-07-13T10:00:00Z",
        },
      ],
    });
    expect(Object.keys(result?.timeline[0] as object).sort()).toEqual(["created_at", "event_type"]);
  });

  it("accepts an empty timeline (a real, valid shape before any execution event occurs)", () => {
    const result = parseExecutionTracking({ job: { status: "scheduled" }, timeline: [] });
    expect(result?.timeline).toEqual([]);
  });

  it("drops individually-invalid timeline rows rather than failing the whole screen", () => {
    const result = parseExecutionTracking({
      job: { status: "on_the_way" },
      timeline: [{ event_type: "technician_on_the_way" }, { created_at: "2026-07-13T10:00:00Z" }],
    });
    expect(result?.timeline).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });

  it("rejects a malformed envelope without throwing", () => {
    expect(parseExecutionTracking(null)).toBeNull();
    expect(parseExecutionTracking({})).toBeNull();
    expect(parseExecutionTracking({ job: {} })).toBeNull();
  });
});
