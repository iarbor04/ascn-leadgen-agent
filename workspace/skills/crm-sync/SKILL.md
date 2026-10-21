---
name: crm-sync
description: Puts leads where the client works and keeps them clean - Google Sheets and HubSpot through ASCN apps, amoCRM and Bitrix24 through the client's own key or webhook in Settings → Secrets (not in the ASCN catalog), and always the agent's own CSV/XLSX plus a .md report. Dedupes against the CRM before any write, never overwrites or changes existing CRM records, writes only after the owner's yes, then reads back. Also imports a CRM export into the lead store. Use for "put them in my CRM / sheet", "export to Excel", "sync with amoCRM / Bitrix24 / HubSpot", "import my CRM list". Do not use to find leads (use lead-search) or for the weekly numbers (use pipeline-report).
---

> Before following this skill, run `python3 files/scripts/package.py skill crm-sync`: it records that the skill is in use, for the owner's reports.

# CRM and sheet sync

Output: an export file in `files/leadgen/exports/`, records in the client's tool (only after a yes and a read-back), `files/leadgen/reports/<date>-crm-sync.md` via `artifact`. In chat: what goes where, what was skipped as a duplicate, what was created and confirmed.

## 1. Where the leads go

From the profile ("Where leads go") or ask once with the branch's options first:
- **Google Sheets** (ASCN apps, both markets): rows from `leadgen.py export --format sheets`.
- **HubSpot** (ASCN apps if offered in Integrations; otherwise its CSV import): `export --format hubspot`.
- **amoCRM** (Russia): `AMO_DOMAIN` (like `yourcompany.amocrm.ru`) and `AMO_TOKEN` (a long-lived token from an amoCRM integration) in Settings → Secrets; `crm push --to amocrm`. Without keys: `export --format amocrm` for amoCRM's own import.
- **Bitrix24** (Russia): `BITRIX_WEBHOOK_URL` (an inbound webhook with CRM rights, from Bitrix24 → Developer resources) in Settings → Secrets; `crm push --to bitrix`. Without it: `export --format bitrix`.
- **Always:** a CSV or XLSX (`export --format xlsx`; CSV if Excel support is not installed) and the .md report.
Never ask for a key or webhook in the chat; if one is pasted, follow the key rule.

## 2. Pick the rows

Usually tier A/B or a stage the owner names: `--stage qualified`, `--min-score <N>`, `--ids L0001,L0002`. The script leaves out do-not-contact leads, and puts addresses that are not public or verified into the notes column, labeled, instead of the email column.

## 3. Write

**Files:** `python3 files/scripts/leadgen.py export --format <format> [--stage ...]` → give the file via `artifact`.

**Google Sheets / HubSpot through apps:** check the app is connected (`apps action="connected"`); show the owner the rows (count and the first few) and the target sheet or object; on the explicit yes, append rows (never clear or overwrite existing rows; a new tab or appended rows only); read the sheet back and report what is there. Duplicates: compare by domain and email with what the sheet already has before appending.

**amoCRM / Bitrix24:**
1. Dry run (default): `python3 files/scripts/leadgen.py crm push --to amocrm|bitrix [--stage ...]`. It searches the CRM for each company (domain, email, phone, name) and lists `would_create` and `would_skip` (already in the CRM). Existing CRM records are never changed.
2. Show the owner the list and warn that new deals or leads can trigger the CRM's own automations (tasks, messages to the client's team or even to the prospect). Ask for the yes to this exact list.
3. On the yes: the same command with `--yes`. It creates each record, adds the "why fits" note with the source, and reads it back. Say «создано» only for `read_back: true`; report errors as given.
4. Pushed leads are marked in the store and never pushed twice.

## 4. Import from a CRM

A CRM or sheet export from the client: `leadgen.py lead import <file> --format generic [--map "<column>=company,<column>=website,..."]`. The file name becomes the source. Report the counts; possible duplicates by name are shown, not merged.

## Rules

- No write to any CRM, sheet or app without the owner's explicit yes to that list; dry run first, read-back after.
- Never delete, overwrite or edit existing CRM records or sheet rows.
- Secrets only in Settings → Secrets, never printed, never saved in files.
- If a write fails half-way, say exactly what was created and what was not.

Sources: own (owner's requirement: leads go wherever convenient); dry run before writes from gooseworks-ai/goose-skills `lead-generation/capabilities/signal-scanner` (MIT); CRM hygiene principles (ground on the live CRM's own fields, never assume one vendor's shapes on another, an existing owned account is coordinated, not duplicated) from anthropics/knowledge-work-plugins `sales/skills/lead-triage` (Apache-2.0); amoCRM and Bitrix24 calls in the style of ascn-support-agent `ru_api.py`.
