# Team Member Detail Pattern

`components/ux03/widgets/TeamMemberDetail.tsx` is the single pattern used
for both staff and technician members. Base sections: identity card (name,
email, descriptive job title, canonical role badge, status). Technician
role additionally renders: availability, active job link, skills, brands,
certifications (with expiry), completed-jobs count, rating, recent parts
activity count. Permissions section: the tenant owner is excluded (full
authority by role); staff/technician get the `PermissionEditor`.
