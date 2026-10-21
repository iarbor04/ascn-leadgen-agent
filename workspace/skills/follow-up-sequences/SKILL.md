---
name: follow-up-sequences
description: Plans and runs follow-up sequences of 2-4 steps after a first message, with due dates computed by the script, and stops at once on a reply, an opt-out or a "no". Lists what is due today, drafts the due follow-ups (each adds something new, never "just checking in"), puts them through the same approval gate, and tracks warm leads that went quiet and "not now" leads whose revisit date came. Use for "follow up", "напомни им", "what is due today", "who went quiet", "set up a sequence". Do not use for the first message (use cold-outreach) or to answer a reply (use reply-handling).
---

> Before following this skill, run `python3 files/scripts/package.py skill follow-up-sequences`: it records that the skill is in use, for the owner's reports.

# Follow-up sequences

Output: sequence plans in `files/leadgen/sequences/sequences.json`, a follow-up outbox batch, `files/leadgen/reports/<date>-follow-ups.md` via `artifact`. In chat: what is due, the drafts to approve, warm leads that need a personal touch.

## 1. The plan

- A sequence starts automatically when a first message is marked sent; to plan one by hand: `python3 files/scripts/leadgen.py seq plan <ID> --channel email --to <address> [--steps 2-4]`.
- Timing comes from settings (`sequence.steps_days`, days after the first message); the script moves the dates when the first message actually goes out later.
- Steps and what each adds (a new reason to answer, never a repeat):
  1. First message (from `cold-outreach`).
  2. A short nudge with one new, useful thing: a relevant example from the profile's approved proof, an answer to the likely question, a new signal.
  3. A different angle or a different person (backup role from `decision-maker-finder`), or a different channel the owner allows.
  4. A polite last message that closes the loop and leaves the door open.
- 2 steps for warm or small markets, up to 4 at most. Never more.

## 2. What is due

Run `python3 files/scripts/leadgen.py seq due` (add `--days 1` for tomorrow). It returns only active sequences whose previous step was sent, plus `revisit_not_now` leads whose revisit date came. Before drafting, check each lead (`lead show`): a reply, an opt-out or a closed stage means its sequence is stopped and nothing goes out.

## 3. Draft and approve

1. Write each due follow-up in the same thread or channel, short, with the opt-out line from settings and the facts used. `"step": <n>` in the drafts file.
2. `leadgen.py outbox new --file <drafts>`, fix blocked ones, show the batch, wait for the owner's explicit yes to this batch, `outbox approve`, send `send_today`, `outbox mark` each. Exactly the gate in `cold-outreach` steps 3–5.
3. A step the owner wants to skip: `leadgen.py seq mark <ID> <step> skipped`.

## 4. Warm leads that went quiet

From `lead list --stage replied` and `--stage meeting`: leads with no new event for a long time (the report lists them). These get a personal note, not a sequence step: what was agreed, one useful thing, a concrete next step. Draft it for the owner; it goes through the outbox like any message.

## 5. Stop rules (the script enforces them)

- Any reply → `reply-handling` classifies it and `leadgen.py reply` stops the sequence.
- Opt-out or "no" → stopped and on the do-not-contact list for good.
- "Not now" → stopped, revisit date set; contact again only when it comes, with a fresh reason.
- Out of office → planned steps move later (`reply --class out_of_office --days <N>`).
- Bounce → the address is marked invalid; find another route before anything else.

## Rules

- Never send a follow-up that is not due, not approved, or to a lead whose sequence stopped.
- Due dates and counts come from the script; never compute them by hand.
- Every follow-up adds something new and carries the opt-out line; no guilt-trips, no fake urgency.

Sources: gooseworks-ai/goose-skills `outreach/capabilities/cold-email-outreach` (touch count and spacing, stop on reply), MIT; anthropics/knowledge-work-plugins `sales/skills/deal-signals` (deals gone quiet surfaced for action) and `draft-outreach` (multi-touch with escalating directness), Apache-2.0; adapted: state machine and dates in `leadgen.py seq`.
