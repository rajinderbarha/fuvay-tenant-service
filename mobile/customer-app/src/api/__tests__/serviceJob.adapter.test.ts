import { parseServiceJobDto, adaptServiceJob } from "../adapters/serviceJob";
import { makeServiceJobDto } from "../../testing/fixtures";
import { UnknownStatusError, ContractValidationError } from "../../domain/errors";

describe("ServiceJob adapter", () => {
  it("parses and adapts a well-formed DTO into a domain ServiceJob", () => {
    const dto = parseServiceJobDto(makeServiceJobDto());
    const job = adaptServiceJob(dto);
    expect(job.id).toBe("job-11111111-1111-1111-1111-111111111111");
    expect(job.status).toBe("on_the_way");
    expect(job.assignmentStatus).toBe("accepted");
    expect(job.scheduledDate).toBe("2026-08-05");
  });

  it("handles nullable fields without throwing", () => {
    const dto = parseServiceJobDto(makeServiceJobDto({ customer_id: null, assigned_staff_id: null, scheduled_date: null }));
    const job = adaptServiceJob(dto);
    expect(job.customerId).toBeNull();
    expect(job.scheduledDate).toBeNull();
  });

  it("rejects an unknown status value instead of guessing", () => {
    const dto = parseServiceJobDto(makeServiceJobDto({ status: "teleported" }));
    expect(() => adaptServiceJob(dto)).toThrow(UnknownStatusError);
  });

  it("rejects an unknown assignment_status value", () => {
    const dto = parseServiceJobDto(makeServiceJobDto({ assignment_status: "vibing" }));
    expect(() => adaptServiceJob(dto)).toThrow(UnknownStatusError);
  });

  it("rejects a malformed DTO at the validation boundary, not the adapter", () => {
    expect(() => parseServiceJobDto({ id: 123 })).toThrow(ContractValidationError);
  });
});
