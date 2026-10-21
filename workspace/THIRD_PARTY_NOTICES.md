# Third-party notices

Parts of this package adapt methods from third-party skills. Every adapted file ends with a "Sources" line naming what was taken. Nothing was copied verbatim: the methods were rewritten for ASCN tools, the `files/leadgen/` data folder and the agent's script `files/scripts/leadgen.py` (which does the counting, dedupe, scoring, sequencing and the approval gate); paid enrichment and scraping services of the originals were replaced with free public sources or the client's own keys; example figures were replaced with placeholders.

## anthropics/knowledge-work-plugins

Copyright Anthropic, PBC. Apache License 2.0 (full text: `third_party/anthropic-knowledge-work-plugins-LICENSE.txt`). https://github.com/anthropics/knowledge-work-plugins

Pinned commit: `bc8f6922cfeea215a202cdcc9f0d299a990889a8`. Adapted 2026-10-21.

| File in this package | Adapted from (`sales/skills/...`) |
|---|---|
| `skills/ideal-customer/SKILL.md` | `lead-triage` |
| `skills/lead-search/SKILL.md` | `account-research` |
| `skills/decision-maker-finder/SKILL.md` | `account-research` |
| `skills/lead-scoring/SKILL.md` | `lead-triage` |
| `skills/cold-outreach/SKILL.md` | `draft-outreach` |
| `skills/follow-up-sequences/SKILL.md` | `deal-signals`, `draft-outreach` |
| `skills/reply-handling/SKILL.md` | `handle-objection`, `draft-outreach` |
| `skills/call-scripts/SKILL.md` | `call-prep`, `handle-objection` |
| `skills/sales-proposal/SKILL.md` | `create-an-asset` |
| `skills/sales-playbook/SKILL.md` | `win-loss-review`, `handle-objection` |
| `skills/crm-sync/SKILL.md` | `lead-triage` |
| `skills/pipeline-report/SKILL.md` | `pipeline-review`, `forecast`, `weekly-wrap` |
| `skills/lead-routines/SKILL.md` | the shared rule on scheduled and unattended runs in the sales skills |

## gooseworks-ai/goose-skills

Copyright (c) 2026 GooseWorks. MIT License (full text: `third_party/goose-skills-LICENSE.txt`). https://github.com/gooseworks-ai/goose-skills

Pinned commit: `6d5d5f160c623613d7eb682b6a467beb165cc2a4`. Adapted 2026-10-21. Their Apify, Apollo-first and paid enrichment pipelines are not used.

| File in this package | Adapted from (`skills/...`) |
|---|---|
| `skills/leadgen-onboarding/SKILL.md` | `lead-generation/capabilities/icp-identification` |
| `skills/ideal-customer/SKILL.md` | `lead-generation/capabilities/icp-identification`, `lead-generation/capabilities/lead-qualification` |
| `skills/lead-search/SKILL.md` | `lead-generation/capabilities/tam-builder`, `lead-generation/capabilities/sales-prospecting` |
| `skills/decision-maker-finder/SKILL.md` | `lead-generation/capabilities/company-contact-finder`, `find-email-by-name`, `verify-email` |
| `skills/lead-scoring/SKILL.md` | `lead-generation/capabilities/lead-qualification`, `lead-generation/composites/inbound-lead-triage` |
| `skills/intent-signals/SKILL.md` | `lead-generation/capabilities/job-posting-intent`, `signal-scanner`, `lead-generation/playbooks/signal-detection-pipeline` |
| `skills/cold-outreach/SKILL.md` | `outreach/capabilities/cold-email-outreach`, `outreach/composites/hiring-signal-outreach` |
| `skills/follow-up-sequences/SKILL.md` | `outreach/capabilities/cold-email-outreach` |
| `skills/reply-handling/SKILL.md` | `marketing-agent/skills/write-outreach-reply-reader` (path outside `skills/`) |
| `skills/crm-sync/SKILL.md` | `lead-generation/capabilities/signal-scanner` (dry run before writes) |
| `skills/pipeline-report/SKILL.md` | `outreach/composites/sequence-performance` |
| `files/scripts/leadgen.py` (`lead import` column matching, `pattern`, verification statuses) | `outreach/capabilities/cold-email-outreach`, `find-email-by-name`, `verify-email` (field lists and result types only) |

## Other

The scope (sales strategy, cold call scripts, cold and follow-up emails, proposals, negotiation, pricing review, personalization, mock calls, objections, lead prioritization, rep onboarding, follow-up tracking, pipeline forecast, fit analysis, upsell/downsell, insight distillation, performance analysis) follows the public description of Sintra's sales helper Milli; no Sintra text was copied. All other files are original to this package.
