# Profile System Design

SEMARC profiles are planned metadata bundles for architecture standards.

Profiles should let projects opt into reusable conventions without expanding the
core semantic language.

Current status: profiles are loaded and composed (v0.8.0), including inheritance and
cycle detection, and their modules are resolved through the stdlib. Profiles do not change
generated code directly; they influence module selection, diagnostics and the manifest.

## Purpose

Profiles can eventually represent:

- ecommerce architecture defaults
- CRM architecture defaults
- inventory architecture defaults
- company standards
- security requirements
- generator preferences
- approved package sets

Example future syntax:

```text
PROFILE Ecommerce
```

or:

```text
PROFILE CompanyEcommerce
```

## Directory Layout

```text
profiles/
├── ecommerce.profile
├── crm.profile
├── inventory.profile
├── blog.profile
└── company_standard.profile
```

Profile files currently contain metadata only.

## Foundation Objects

```text
architecture/profiles/
├── profile.py
├── registry.py
└── loader.py
```

`Profile` stores:

- name
- description
- extends
- packages
- metadata

`ProfileRegistry` stores loaded profiles by name.

`ProfileLoader` reads `profiles/*.profile` files.

## Loading Flow

Planned flow:

```text
PROFILE Ecommerce
    |
    v
ProfileLoader
    |
    v
ProfileRegistry
    |
    v
future profile pass
    |
    v
package selection and architecture constraints
```

The current compiler only preserves `ProfileNode` metadata in AST and IR.

## Inheritance Design

Future profiles may support inheritance:

```text
PROFILE CompanyEcommerce

EXTENDS Ecommerce
```

The intended resolution order is:

1. Load base profile metadata.
2. Load child profile metadata.
3. Merge package lists deterministically.
4. Let child metadata override base metadata.
5. Validate cycles.
6. Expose resolved profile metadata to later compiler passes.

Inheritance must remain explicit and deterministic.

## Relationship to Packages

Profiles may select packages:

```text
name: Ecommerce
packages: payment, notification, storage
```

Future profile expansion should load package metadata through the package
registry, then validate package compatibility before architecture expansion.

## Boundaries

Profiles may influence future compiler passes, but they must not:

- change parsing rules dynamically
- generate code directly
- bypass semantic validation
- inject target-specific syntax into AST or IR
- hide company policy inside generators

Company standards should live in profiles and packages, not in hardcoded target
generators.

## Roadmap

Near-term:

- profile metadata loading
- profile registry contracts
- profile inheritance resolver
- package compatibility checks

Later:

- company security baselines
- organization-approved packages
- target profile recommendations
- architecture constraint bundles
- standard route, repository, and validation conventions
