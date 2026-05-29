# v0.4 Architecture Gap Analysis

This document identifies future package candidates. It does not implement them.

## Useful Future Package Types

- `payment`: provider-specific payment flows, webhooks, refunds, and audit requirements.
- `reporting`: exports, scheduled reports, and analytics read models.
- `search`: indexing, search adapters, and query constraints.
- `notification`: email, SMS, push, and event-driven notification rules.
- `audit`: append-only activity logging and compliance metadata.
- `storage`: local, object storage, and media handling modules.
- `cache`: Redis and application cache policies.
- `role_permission`: roles, permissions, and route protection policies.

## Current Foundation Gaps

- Package dependency resolution is metadata-only.
- Profile inheritance is loaded but not applied to compiler behavior.
- Package compatibility constraints are not evaluated yet.
- Target-specific package mappings are intentionally absent.

## Boundary Reminder

Future package implementation should remain deterministic and target-neutral until the generator mapping stage.
