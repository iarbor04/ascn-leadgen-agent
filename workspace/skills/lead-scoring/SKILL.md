---
name: lead-scoring
description: Scores and prioritizes leads by fit with the ideal customer and by buying signals, using the script's weights from settings.json, and returns a ranked list with the reasons for each score, the tier (A / B / C, DQ for excluded or do-not-contact) and the next action per lead. Works on the saved leads or on a list the user uploads. Use for "which leads first", "prioritize", "score this list", "who is hot", or after a new batch. Do not use to define the ideal customer (use ideal-customer), to find new companies (use lead-search) or to report on the whole pipeline (use pipeline-report).
---

> Before following this skill, run `python3 files/scripts/package.py skill lead-scoring`: it records that the skill is in use, for the owner's reports.

# Lead scoring and priorities

Output: scores, tiers and reasons in the store; `files/leadgen/reports/<date>-priorities.md` with the ranked table, delivered via `artifact`. In chat: the top leads with one-line reasons and the action for each tier.

## 1. Inputs

1. Run `python3 files/scripts/leadgen.py context`. No fit criteria → run `ideal-customer` first; the script refuses to score without them.
2. An uploaded list goes in first: `leadgen.py lead import <file> --format ...` (it merges duplicates and keeps the file name as the source).
3. Fresh signals help the score: if the user wants it, run `intent-signals` for the top candidates first.

## 2. Score

Run `python3 files/scripts/leadgen.py score --all` (or `--id <ID>` for one lead). How it works, to explain in plain words if asked:
- **Fit** (up to 60): industry, region, size and role of the contact against the ideal customer, with the owner's weights. Each criterion is match, no match, or not known; not known gives no points and is listed so it can be checked.
- **Signals** (up to the cap in settings): each kind of signal counts once; older than the window in settings counts half.
- **Exclusions**: an exclusion word or the do-not-contact list → DQ.
- **Tiers**: thresholds from settings.

Use the script's numbers and reasons as printed. Never adjust a score by hand; if it looks wrong, the criteria or weights need a change (`ideal-customer`), and the user decides.

## 3. Prioritize

| Tier | Action |
|---|---|
| A | find the decision maker today, first message in the next batch |
| B | contacts and a message this week; watch for a signal |
| C | keep; re-check when a signal appears |
| DQ | no outreach; say why |

Within a tier: inbound requests first (a form, a message, a referral: signal `inbound` or `referral`), then leads with a fresh signal, then leads already in contact (a warm lead that went quiet beats a cold one), then by score. Existing conversations and owned accounts in the client's CRM are flagged: coordinate, don't start over.

## 4. Deliver

Report: the ranked table (id, company, score, tier, the reasons, what is not known, next action, source), what changed since the last scoring, and the criteria used. Chat: top 5–10 in one line each and one next step.

## Rules

- Numbers come from the script only. No invented probabilities ("[N]% likely to buy").
- "Not known" is never a "no": say how to find it out.
- A DQ lead is never sent a message, whatever its score was before.

Sources: anthropics/knowledge-work-plugins `sales/skills/lead-triage` (fit and intent tables, priority tiers, owned-account override, one-line reason per row), Apache-2.0; gooseworks-ai/goose-skills `lead-generation/capabilities/lead-qualification` (hard disqualifiers, confidence with reasons, calibration from the owner's feedback) and `lead-generation/composites/inbound-lead-triage` (inbound before cold, by source urgency), MIT; adapted: arithmetic moved into `leadgen.py score`.
