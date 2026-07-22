# Read-Path Privacy Limitations

- **Pricing GET-by-zone/rule-ID**: documented since 2F-37's
  `known-limitations.md` as an out-of-mutation-scope read-path tenant
  scoping gap; unresolved, unchanged this slice (mutation routes for
  pricing are protected; the read endpoints were not brought into this
  program's mutation-only scope).
- **Item/location ownership**: previously documented gap (2F-36 era)
  regarding read-path ownership checks for certain item/location lookups;
  unresolved, unchanged.

Both remain read-path privacy limitations, not mutation-authorization
gaps — consistent with this program's mutation-only scope throughout.
