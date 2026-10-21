---
name: call-scripts
description: Prepares calls - a cold call script for the client's offer and market, a one-page prep for a call with a specific lead (what we know with sources, goal, questions, likely objections with answers), and mock sales calls where Kevin plays the prospect and then gives feedback. Use for "call script", "скрипт звонка", "prepare me for a call with X", "what will they object", "let's rehearse", "mock call". Do not use for written replies (use reply-handling), for a proposal document (use sales-proposal) or for a full sales playbook (use sales-playbook).
---

> Before following this skill, run `python3 files/scripts/package.py skill call-scripts`: it records that the skill is in use, for the owner's reports.

# Call scripts, call prep and mock calls

Output: `files/leadgen/reports/<date>-call-script.md` or `<date>-call-prep-<company>.md`, delivered via `artifact`; for a mock call, the dialogue in chat and `<date>-mock-call.md` with the feedback. Calls are made by the owner or their team; Kevin never calls anyone.

## 1. Cold call script

From the profile (offer, ideal customer, who decides, approved proof) and `knowledge/outreach-rules.md` (work numbers only; respect «не звоните»):
1. **Opening (10–15 seconds):** who you are, the company, one line why you're calling them specifically (a real fact or signal), permission: «Удобно минуту?».
2. **Reason:** the problem the offer solves for this role, in their words; one approved proof point if there is one.
3. **2–3 questions** that qualify: how they handle it now, what bothers them, who decides, timing.
4. **The ask:** one next step (a short meeting, sending one specific thing).
5. **If "no":** thank them, confirm you won't call again, record it (`leadgen.py reply <ID> --class no`).
6. **Gatekeeper version** (reception or a secretary): short, honest, the name of the role you need, never a pretext.
Variants per role (owner / head of function / user). All in the language and register of the market.

## 2. Call prep for one lead

1. `leadgen.py lead show <ID>`: what we know, each fact with its source; past messages and replies; stage.
2. Fresh check: open the company site and one news or vacancy source (`intent-signals` method); note what is new.
3. One page: who they are, why they fit (score reasons), what happened so far, the goal of this call, 3–5 questions, likely objections with answers (step 3), the next step to propose, and what not to say (promises the profile can't back).
Unknowns stay unknown: «не знаем — спросить на звонке».

## 3. Objections: predict and answer

Predict 4–6 objections from the offer, the price level in the profile, the segment and past replies in the store (`reply` notes). For each: what is underneath (price or value, timing, a competitor or "we have someone", trust and risk, authority, status quo; an objection vs a negotiation move), a short answer (acknowledge, answer with their situation and one approved proof point, a question that moves forward), and what not to do (argue, over-discount, dump features).

## 4. Mock call

1. Agree the scenario: the role, company type, mood (busy, skeptical, interested), the goal of the call.
2. Play the prospect realistically, one turn at a time; raise objections from step 3; don't make it easy.
3. After the call, or when the user says stop: feedback in 3 parts — what worked (quote their lines), what to change (with a better wording), the one thing to practice next. Save it.
The mock prospect is invented by design; label it «тренировка, вымышленный собеседник» and never save it as a lead.

## Rules

- No invented facts about the prospect or the client in scripts: sources for the first, the profile for the second, [placeholders] otherwise.
- Kevin prepares; the owner calls. Recording or transcribing calls is out of scope unless the owner uploads a transcript.
- Prices, discounts and guarantees only as the profile states them.

Sources: anthropics/knowledge-work-plugins `sales/skills/call-prep` (one-page brief: context, attendees, plan, questions, never an empty source presented as "nothing happened") and `handle-objection` (objection types, talk track, don't list), Apache-2.0; mock-call and cold-call structure written for this package from Sintra Milli's scope (no text copied).
