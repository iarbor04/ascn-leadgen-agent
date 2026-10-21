---
name: pipeline-report
description: Weekly pipeline report and performance analysis from the lead store - companies found, first messages, replies by kind, meetings, opt-outs, stage moves, follow-ups due, what is stuck - plus forecast health computed by the script only from the client's own recent results with the assumptions labeled, and what to change next week. Use for "how are we doing", "weekly report", "pipeline", "forecast", "what worked", or when the weekly report routine runs. Do not use to rank leads (use lead-scoring) or for strategy advice (use sales-playbook).
---

> Before following this skill, run `python3 files/scripts/package.py skill pipeline-report`: it records that the skill is in use, for the owner's reports.

# Pipeline report

Output: `files/leadgen/reports/<date>-pipeline-week.md` via `artifact`. In chat: 5–7 lines with the main numbers, what moved, and the one or two changes for next week.

## 1. Numbers

1. `python3 files/scripts/leadgen.py report weekly` (default: the last 7 days to today; `--from` / `--to` for another period). If a CRM or sheet is the client's main record and is connected, note that the report counts only what went through Kevin.
2. `leadgen.py seq due --days 7` for next week's follow-ups and revisits; `leadgen.py lead list --stage replied` and `--stage meeting` for warm leads; `leadgen.py context` for pending approvals.
3. Use every number exactly as printed. `reply_rate` is None when nothing was sent: say «писем не было», never 0%.

## 2. The report

1. **Summary** (3–5 lines): the week in plain words.
2. **Funnel this week:** found → first messages → replies (by kind) → meetings; opt-outs and "no".
3. **Stage moves** and the pipeline now by stage.
4. **Stuck and at risk:** warm leads with no new step, approved batches not sent, follow-ups overdue, leads waiting for contacts.
5. **What worked and what didn't:** by segment, channel and message angle where the data allows; small numbers are called small.
6. **Forecast health:** the script's `forecast_health` as is. `too little data` → say so and what amount of activity would allow an estimate; `estimate` → give the basis and the assumption line from the script, never as a promise. With a goal in settings, show progress against it.
7. **Next week:** 2–3 concrete changes (a segment to add or drop, a message angle to test, a follow-up to send), who does each.

## 3. Weekly routine

When the owner wants this every week, set it up through `lead-routines` (routine `weekly_report`): Telegram connected, credits warning, explicit yes, cron confirmed. The scheduled run only reports; it sends nothing to prospects.

## Rules

- Numbers come from the script; nothing computed in the head, no industry averages without a source.
- "Not measured" or "no data" is never zero.
- The forecast is an estimate from the client's own data with its assumption, never a promise of meetings or sales.

Sources: anthropics/knowledge-work-plugins `sales/skills/pipeline-review` (stage rollup, stale / blank-next-step / stuck flags, recommended focus), `forecast` (the number, what changed, risk, labeled categories) and `weekly-wrap` (what moved, what slipped, what's next), Apache-2.0; gooseworks-ai/goose-skills `outreach/composites/sequence-performance` (metrics per touch, enough replies before judging), MIT; adapted: counts in `leadgen.py report`, forecast only from own data.
