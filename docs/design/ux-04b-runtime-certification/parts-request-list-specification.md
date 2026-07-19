# Parts Request List Specification

Corrects UX-04A's wrong NOT_APPLICABLE disposition (a single-row fixture
set is not valid exclusion evidence for a list view). Columns: request id,
ServiceJob, technician, part(s), quantity, cost, status, approver,
installation state, last activity. Filters: free-text search (request id/
job/technician/part) + status select. States demonstrated on one route via
a state switcher using the real component: multiple-request, empty,
loading, error. Actions per real policy only — approve/reject availability
gated by `ActionPermissionView`, no "mark installed" control (no
technician install authority per hard constraint), no field_ops.Job
column or link anywhere, no invented PO/inventory/ordering workflow.
