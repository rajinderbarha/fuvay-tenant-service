"use client";
// HOME-SERVICES-SUPER-ADMIN-RECONCILIATION: this route existed only as
// /[complaint_id]/ (the 360 detail page) with no list/queue page -- both
// the legacy /admin/complaints redirect and the 360 page's own "Back to
// Complaints" button targeted this exact path, so it 404'd live. The real
// backend (app/engines/vertical_directory/admin_router.py) and API client
// (verticalDirectoryApi) and workspace component (VerticalComplaintWorkspace)
// all already existed and work -- this was purely a missing page file.
import React from "react";
import { VerticalComplaintWorkspace } from "../../../../components/directory/VerticalComplaintWorkspace";

export default function HomeServicesComplaintsPage() {
  return <VerticalComplaintWorkspace vertical="home-services" verticalLabel="Home Services" />;
}
