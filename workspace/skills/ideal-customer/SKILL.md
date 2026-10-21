---
name: ideal-customer
description: Defines and maintains the client's ideal customer (who buys, size, where, who decides, signs they need it now, who is not a fit) from the client's site, their best customers and their answers, turns it into fit criteria the script scores with, and checks how well one company fits (fit analysis with evidence). Use when the user asks who to sell to, wants to change the target, says "this lead is not for us", or asks "does company X fit?". Do not use to search for new companies (use lead-search), to rank a whole list (use lead-scoring) or for first-session setup (use leadgen-onboarding, which calls this method).
---

> Before following this skill, run `python3 files/scripts/package.py skill ideal-customer`: it records that the skill is in use, for the owner's reports.

# Ideal customer and fit analysis

Output: the "Ideal customer" section of `files/leadgen/profile/leadgen-profile.md`, the `icp` block of `settings.json` (through `leadgen.py icp set`), and `files/leadgen/reports/<date>-ideal-customer.md`; for a fit check, `files/leadgen/reports/<date>-fit-<company>.md`. In chat: the description in 3–5 lines or the fit verdict with its reasons.

## 1. Gather the evidence

1. Run `python3 files/scripts/leadgen.py context` and read the profile.
2. The strongest evidence is the client's own best customers: names on their site (cases, logos, reviews) and the ones the user named. Open their sites if needed to see what they have in common (industry, size, city, how they buy).
3. The client's offer and price: who can afford it and who feels the problem it solves.
4. Who is not a fit: the user's own words first; then obvious mismatches (too small to pay, too big to buy from a small vendor, outside the regions they serve).

## 2. Write the description

Fill a table, each row with the evidence and its source, guesses marked "(assumed)":

| What | Value | Why (evidence, source) |
|---|---|---|
| Who buys (industry, kind of company) | [value] | [evidence] |
| Size (staff, branches, revenue band if known) | [value] | [evidence] |
| Where | [cities, regions, countries] | [evidence] |
| Who decides and who uses it | [roles] | [evidence] |
| Signs they need it now | [hiring for X, tenders on Y, new branch, funding, site changes] | [evidence] |
| Not a fit | [exclusions] | [evidence] |

Keep it narrow enough to search: a vague description gives vague leads. If two different kinds of customer appear, write two descriptions and name them.

## 3. Save the fit criteria

Translate the table into search words and run:
`python3 files/scripts/leadgen.py icp set --industries "<words, comma-separated>" --regions "<cities or countries>" --size-min <N> --size-max <N> --roles "<role words>" --exclude "<words>" --keywords "<extra words>"`

Use words that will appear on cards and sites (in Russian for `ru`, in the prospects' language for `intl`; add both spellings when needed). Leave a criterion out rather than guess it. Then run `leadgen.py score --all` so existing leads are re-scored, and tell the user how the tiers changed (from the script output).

## 4. Fit analysis of one company

1. Open the company's site and one more source (a card, the register via `leadgen.py egrul <ИНН>` for `ru`, a public company page for `intl`). Add it with `leadgen.py lead add` if it is not in the store.
2. Run `leadgen.py score --id <ID>` and use its reasons.
3. Verdict in plain words: fits / partly / does not fit, with each criterion: match, no match, or not known (and how to find out). Unknown is never a "no".
4. If it fits, say who to approach first and why (from `decision-maker-finder`), and one real fact to open with.

## 5. Learn from results

When the user rejects leads or replies show a pattern (a segment answers, another never does), propose a concrete change to the criteria, show before / after, and apply it only on the user's yes. Record the reason in the profile under "Learned rules".

## Rules

- Evidence first: every row has a source or "(assumed)". Never invent a client's customers, revenue or results.
- Weights in `settings.json` → `scoring` are the owner's to change; change them only when asked, and say what will move.
- Plain words with the user: «идеальный клиент», «кто принимает решение», «признаки, что им это нужно сейчас».

Sources: gooseworks-ai/goose-skills `lead-generation/capabilities/icp-identification` (inclusion and exclusion tables, evidence from current customers) and `lead-qualification` (hard disqualifiers, strongest qualifiers), MIT; anthropics/knowledge-work-plugins `sales/skills/lead-triage` (fit table strong / partial / miss, "not known" kept apart), Apache-2.0; adapted.
