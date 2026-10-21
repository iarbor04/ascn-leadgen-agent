# Design decisions

- **Source:** Sintra's sales helper Milli (public page sintra.ai/ai-employees/sales-agent), focused on lead generation, plus the owner's additions (2026-10-21): both markets with a choice at onboarding; leads wherever convenient (Google Sheets and HubSpot via ASCN apps, amoCRM and Bitrix24 via the client's key or webhook in Secrets, always CSV/XLSX + .md); free sources by default, paid only with the client's own key; autonomy while the owner is not in the chat. No Sintra text copied. Structure and conventions mirror `ascn-legal-agent` (newest repo): public IDENTITY / SOUL / soul field, rules in `AGENTS.leadgen-rules.md` placed at the top of AGENTS.md, operating contract in `AGENTS.leadgen-addon.md`.
- **Name:** Kevin (masculine forms in Russian). Russian address «вы» unless the user writes «ты» (as the task and BUILD-GUIDE say; note: Lara and Clara default to «ты» — owner to confirm).

## Milli scope → skills

| Milli item | Skill |
|---|---|
| sales strategy, pricing review, negotiation, onboarding new reps, upsells/downsells, insight distillation | `sales-playbook` (merged: all advisory, same inputs) |
| cold call scripts, mock sales calls, predict objections | `call-scripts` |
| cold and follow-up emails, personalize at scale by role / industry / past interactions / intent | `cold-outreach`, `follow-up-sequences` |
| objection handling in writing, replies | `reply-handling` |
| build and improve proposals | `sales-proposal` |
| prioritize leads and activities, fit analysis | `lead-scoring`, `ideal-customer` (fit analysis of one company lives with the criteria it uses) |
| follow-up and warm-lead tracking | `follow-up-sequences` |
| forecast pipeline health, performance analysis | `pipeline-report` |
| onboarding: business/ICP/offers/goals → tools → strategy → approve drafts → improve | `leadgen-onboarding` (+ `crm-sync`, `lead-routines`) |
| (lead generation focus) | `lead-search`, `decision-maker-finder`, `intent-signals` |
| (owner: autonomy) | `lead-routines` |

Merged on purpose: account research into `decision-maker-finder` and `lead-search`; call prep into `call-scripts`; forecast and weekly wrap into `pipeline-report`. Not included: logging calls/meetings from transcripts, CRM hygiene of the client's whole CRM, renewals (not lead generation).

## What the script enforces (so the model can't skip it)

- `lead add` refuses a lead without a source; contacts need a source; email status is one of public / verified / unverified / pattern / invalid; `lead import` drops personal mobile and home phone columns.
- `outbox new` blocks pattern and invalid addresses, addresses not in the lead's contacts, do-not-contact matches, missing opt-out lines, unfilled placeholders, duplicates; `outbox approve --by` records the yes and splits by daily limits; `outbox mark sent` works only for approved messages and re-checks stage, do-not-contact and stopped sequences.
- `reply --class no|opt_out` stops the sequence and adds the do-not-contact entry; `not_now` sets a revisit date.
- `mx` only says the domain accepts mail; it never upgrades a pattern address. Mailbox verification only with Hunter (client's key).
- `crm push` is a dry run by default, skips anything already in the CRM, never updates existing records, reads back after `--yes`, never pushes a lead twice.
- `report weekly` forecast uses only the client's own last 4 weeks and refuses with fewer than 20 first messages.
- Network failure → `"status": "not checked"` with the reason; secrets are scrubbed from every output.

## Data sources

Free: web_search/web_fetch of single public pages (2GIS, Yandex Maps, company sites, Rusprofile/Checko, zakupki.gov.ru, t.me/s/, Google Maps listings via search, LinkedIn search results only, job boards), ФНС register (`egrul.nalog.ru` two-step search; captcha → not checked), hh.ru vacancies API, DNS-over-HTTPS MX (Cloudflare, Google). Paid with the client's key: DaData, Hunter, Apollo; Snov.io via its CSV export. amoCRM API v4 (`/api/v4/leads/complex`), Bitrix24 inbound webhook (`crm.lead.add`, `crm.duplicate.findbycomm`).

Checked from the build machine on 2026-10-21 (outside Russia): MX via DoH works; `api.hh.ru/vacancies` returned 403 for anonymous requests (hence the optional free `HH_APP_TOKEN`); `egrul.nalog.ru` and `zakupki.gov.ru` timed out (likely geo-blocked outside Russia). Must be re-checked from the ASCN sandbox. Endpoints of amoCRM, Bitrix24, Hunter, Apollo and DaData are written from their public docs and need a check with a real key before release.

## Terms of service

2GIS, Yandex Maps, Rusprofile/Checko and LinkedIn restrict automated collection: the agent reads single pages found by search, records the URL, and for volume asks the client for their own export. No logins, no captcha solving, no bought databases (`knowledge/lead-sources.md`).

## Legal note

`knowledge/outreach-rules.md`: a plain note per market (152-ФЗ, 38-ФЗ; GDPR/UK, CAN-SPAM), given once at onboarding, with official links opened 2026-10-21; not legal advice, details go to Lara.
