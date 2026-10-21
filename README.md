# ascn-leadgen-agent — Kevin, lead generation specialist

An ASCN marketplace agent: replicates Sintra's sales helper Milli with the focus on lead generation, plus the owner's additions (Russia/CIS and international branch at onboarding; leads in Google Sheets, HubSpot, amoCRM, Bitrix24 or the agent's own CSV/XLSX + .md; free sources by default, paid ones only with the client's key; opt-in routines that work while the owner is not in the chat). Nothing reaches a prospect without the owner's explicit yes to that batch; every lead and contact carries its source link and date.

## Skills (15)

| Skill | What it does |
|---|---|
| leadgen-onboarding | money-first intro, one request (site), market branch + legal note, ideal-customer draft and a first batch of real companies in the same session |
| ideal-customer | ideal customer with evidence, fit criteria for the script, fit analysis of one company |
| lead-search | real companies from free public sources (RU / intl) or the client's files and keys, saved with sources, deduped, scored |
| decision-maker-finder | who decides, public work contacts with sources, pattern addresses labeled, verification only with a key |
| lead-scoring | fit + signal score from the script, tiers A/B/C/DQ, reasons and next action |
| intent-signals | hiring (hh.ru, job boards), tenders, new branches, funding, site changes; optional weekly watch |
| cold-outreach | personal first messages from real facts, script checks, the owner's yes per batch, daily limits |
| follow-up-sequences | 2–4 steps with script dates, stop on reply / opt-out, warm leads that went quiet |
| reply-handling | reply classes recorded by the script, drafted answers, written objections |
| call-scripts | cold call script, call prep, objections, mock calls with feedback |
| sales-proposal | build or improve a proposal from the client's own facts |
| sales-playbook | strategy, pricing review, negotiation, new-rep playbook, upsell/downsell, insights |
| crm-sync | Sheets / HubSpot via apps, amoCRM / Bitrix24 via keys, CSV/XLSX; dry run, no overwrites, read-back |
| pipeline-report | weekly numbers, stuck leads, forecast health from own data with assumptions |
| lead-routines | opt-in daily/weekly lead batch, follow-up reminders, weekly report, signal watch (Telegram needed) |

## Script `files/scripts/leadgen.py`

Standard library only, JSON output, secrets never printed, failed sources → "not checked". Commands: `context`, `icp show|set`, `lead add|import|list|show|set-stage|contact|signal`, `dedupe [--apply]`, `score`, `egrul`, `hh`, `dadata`, `hunter domain|verify|find`, `apollo people`, `mx`, `pattern`, `seq plan|due|mark|stop|list`, `reply`, `dnc add|check|list`, `outbox new|list|show|approve|mark|cancel`, `export --format amocrm|bitrix|hubspot|sheets|csv|xlsx`, `crm push --to amocrm|bitrix [--yes]`, `report weekly`, `check`. See the file header.

Tests (offline, mocked HTTP): `python3 tools/test_leadgen.py`.

## Data

`files/leadgen/`: `profile/leadgen-profile.md`, `settings.json`, `leads/leads.json` and `leads/dnc.json`, `outbox/`, `sequences/`, `exports/`, `reports/`, `logs/events.jsonl`.

## Install and publish

`marketplace/install-or-update-from-github.md` (one prompt, hash-checked bundle), then the soul from `marketplace/soul-intro.md`. Start prompt: `marketplace/startup-task.md`. Before publishing: `marketplace/pre-publish-check.md` (purge on the owner's yes).

After any change: `python3 tools/build_manifest.py && python3 tools/build_manifest.py --check`, `python3 tools/test_leadgen.py`.
