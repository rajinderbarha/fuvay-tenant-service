"""Service Catalog Engine — tenant-defined services.

A catalog item's `service_type` is the same vocabulary field_ops uses for
Job.job_type (repair/service/consultation). Booking conversion reads this
field to automatically select the correct workflow — see
BookingService.convert_to_job().
"""
from app.engines.field_ops.constants import JobType

SERVICE_TYPES = [JobType.REPAIR, JobType.SERVICE, JobType.CONSULTATION]


class PricingModel:
    FIXED           = "fixed"            # price known upfront (e.g. AC Annual Service)
    POST_ASSESSMENT = "post_assessment"  # price discovered after a technician visit
    HOURLY          = "hourly"           # billed by time spent

PRICING_MODELS = [PricingModel.FIXED, PricingModel.POST_ASSESSMENT, PricingModel.HOURLY]
