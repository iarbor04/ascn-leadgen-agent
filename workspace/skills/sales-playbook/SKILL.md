---
name: sales-playbook
description: Advisory sales work in one place - a sales strategy for the client's offer and market, a pricing review, negotiation tips for a specific deal, a playbook and first-week plan for onboarding a new sales rep (scripts, message templates, qualification questions, objection answers), upsell and downsell ideas for existing customers, and insight distillation (what the client's own results, replies and notes say works). Everything is built from the profile and the store; benchmarks only with a source. Use for "sales strategy", "how should we sell", "is our price right", "how do I negotiate this", "train a new salesperson", "what else can we sell them", "what have we learned". Do not use for one proposal (use sales-proposal), one call (use call-scripts) or the weekly numbers (use pipeline-report).
---

> Before following this skill, run `python3 files/scripts/package.py skill sales-playbook`: it records that the skill is in use, for the owner's reports.

# Sales playbook and advice

Output: `files/leadgen/reports/<date>-<topic>.md` (strategy, pricing review, negotiation plan, rep playbook, upsell ideas or insights), delivered via `artifact`. In chat: the 3–5 key points and one next step.

Before any part: `python3 files/scripts/leadgen.py context`, the profile, and for evidence `leadgen.py report weekly --from <date>` and the replies and notes in the store. Separate in every output: what the client's own data shows, what the client told us, and your recommendation (labeled as such).

## 1. Sales strategy

For the client's offer and market, one page:
1. Who to sell to first (the ideal customer, the segment with the best evidence) and why.
2. Channels in order (email, Telegram, LinkedIn, calls, partners, events) with the reason for the market (`knowledge/markets.md`).
3. The message: the problem, the promise the client can keep, the proof they have.
4. The weekly rhythm: how many new companies, messages and follow-ups the owner can really review, within the daily limits.
5. What to measure and when to change course (from `pipeline-report`).
6. Risks and what is not known.

## 2. Pricing review

From the client's prices and what replies, calls and lost deals say (`reply` notes, `no` and `not_now` reasons). Check: is the price clear on first read, is there a simple entry option, does the price match the segment's size, are discounts given without a trade. Competitor prices only from pages you opened, with links and dates. Output: findings and options with pros and cons; the decision is the owner's. No invented market averages.

## 3. Negotiation tips for a deal

From the lead's history and the owner's notes: what they want, what they said they need, who decides, alternatives on both sides. Give: the goal and the walk-away point (the owner's, ask if unknown), what to trade (never give a discount without getting something: volume, term, prepayment, a case study), answers to the likely pushbacks (`call-scripts` step 3), and the next step. No legal terms: contracts go to Lara.

## 4. Onboarding a new sales rep

A playbook the rep can use from day one: the offer in plain words, the ideal customer and disqualifiers, the call script and message templates (from `call-scripts` and `cold-outreach`, with placeholders), qualification questions, objection answers, the approval rules (nothing goes out without the owner's yes, opt-out lines, do-not-contact), where leads live and how stages are used, and a first-week plan with daily tasks. Add a mock-call exercise per day (`call-scripts` step 4).

## 5. Upsell and downsell ideas

For customers the client names (or won leads in the store): what else from the client's own offer fits their situation, when to offer it (a trigger: growth, a new branch, the end of a project), and a lighter option for those who said "too expensive" (downsell) only if the client has or agrees to make one. Never invent products or prices.

## 6. Insight distillation

What the client's own data says: which segments and messages got replies, which objections repeat, why deals were lost, what the winners had in common. Counts come from `leadgen.py report weekly` (run for several periods if needed) and the store; small numbers are said to be small («слишком мало данных для вывода»). Turn each insight into one concrete change and who does it.

## Rules

- Recommendations are labeled as recommendations; data is data; the owner decides.
- No invented benchmarks, conversion rates or competitor facts: a source link, «по моему опыту, без источника», or left out.
- No financial, legal or tax advice beyond sales practice; contracts go to Lara, business strategy beyond sales to Max.

Sources: written for this package from Sintra Milli's scope (strategy, pricing review, negotiation, rep onboarding, upsell/downsell, insight distillation; no text copied); anthropics/knowledge-work-plugins `sales/skills/win-loss-review` (patterns in what wins and loses, objections that repeat) and `handle-objection` (objection vs negotiation move), Apache-2.0; adapted.
