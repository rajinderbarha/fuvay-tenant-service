# PHASE 6B — Tenant Portal Integration Report

Generated: 2026-07-08

| Page | Primary API(s) |
|------|----------------|
| /profile | profileApi.getProfile(), businessProfileApi.get()/update(), ProfilePhotoUploader |
| /provider/service-areas | providerServiceAreasApi list/create/update/delete, categoryDashboardApi.getRuntime() |
| /provider/offerings | providerOfferingsApi listAvailable/listEnabled/enable/update/activate/deactivate |
| /provider/service-coverage (NEW) | providerOfferingsApi.listEnabled(), providerBrandApi get/set supported, providerServiceOptionApi get/set supported |
| /provider/team-members | providerTeamMembersApi, providerOnboardingApi, categoryDashboardApi |
| /provider/availability | providerAvailabilityApi list/create/update/delete |
| /documents | documentsApi list/generate/getSigningUrl/get |
| /notifications | notificationsApi list/getChannels/setChannel |
| /settings | settingsApi, complianceApi, securityApi |
| /finance | financeApi wallet/deposit/packages/commission/invoices/payouts |
