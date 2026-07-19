# Responsive Tenant Behavior

`Ux03NavItem.mobileBehavior` (`full` / `collapsed_summary` /
`hidden_on_mobile`) records intended per-item mobile treatment (see
tenant-navigation-map.csv). `DataTable`'s `mobileCard` prop (inherited from
UX-01) is available to every `TenantListPage` usage but was not populated
with a custom mobile card renderer in this phase's showcase pages — they
rely on the design system's default responsive table behavior. Not
verified in a real viewport/browser this phase (Mode B).
