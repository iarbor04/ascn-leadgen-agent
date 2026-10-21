---
name: leadgen-onboarding
description: First-session onboarding for the lead generation agent. Leads with how the client earns (more qualified leads and meetings, as help, never a guarantee), asks for one thing (the website or two sentences), reads the site, picks the market branch (Russia/CIS or international), gives the market's short legal note once, drafts the ideal-customer description and returns a first small batch of real companies that fit, each with the reason and the source link, in the same session. Then offers where to keep leads and the "works while you're away" routines. Use when the profile is empty, on the first message, when the user sends a website or a short description without a task, or says "start" / "what can you do". Do not use when the user arrives with a concrete task (do it with its skill and fill the profile along the way), or to change the ideal customer later (use ideal-customer).
---

> Before following this skill, run `python3 files/scripts/package.py skill leadgen-onboarding`: it records that the skill is in use, for the owner's reports.

# Lead generation onboarding

Goal: in 3–4 messages the user has an ideal-customer description and a first batch of real companies that fit, with reasons and sources. Not a questionnaire.

Output: filled `files/leadgen/profile/leadgen-profile.md` and `settings.json` (`market`, `icp`), the first leads in the store, `files/leadgen/reports/<date>-first-leads.md` plus the lead table (CSV/XLSX) via `artifact`; in chat a short list of the companies and one next step.

## 1. Introduce yourself (first contact only)

If the start greeting already introduced you, skip this. Otherwise, in the user's language, plain words, under ~900 characters:
1. **How they earn with you:** one line: more qualified leads and meetings with companies that fit, said as help («помогу»), never as a guarantee.
2. **What you do:** 1–2 lines (find companies with the source of each, find who decides, write personal messages, nothing goes out without their yes, keep working while they are away).
3. **One request:** «Пришлите сайт или в двух предложениях: что вы продаёте и кому.»

If the user asks for a guarantee: nobody can promise results in advance; you measure, fix and measure again.

## 2. Read the site

1. Run `python3 files/scripts/leadgen.py context`.
2. With a website: `web_fetch` the home page and, if they exist, about, services or products, prices, cases or clients, contacts. Take only what is written: what they sell, to whom, cases and client names shown on the site, cities, prices if shown.
3. Without a website: work from the two sentences; everything else is "(assumed)".
4. Fill the profile sections Business and Ideal customer, each fact with "(site, <page>)" or "(owner, <date>)". Never put a guess in without "(assumed)".

## 3. Market branch and the legal note

1. Decide `ru`, `intl` or `both` per `knowledge/markets.md`. Two or more strong signals one way → say it in one line so the user can correct it. Mixed → this becomes one of the questions in step 5.
2. Save `market` and `market_evidence` in `settings.json` and the profile.
3. Give the market's short legal note from `knowledge/outreach-rules.md`, in plain words, 2–3 lines, once. Write the date into the profile ("Legal note given").

## 4. First result in the same session

Do this right after the site, before any more questions:
1. **Ideal-customer draft** (method: `ideal-customer`, step 2): who buys, size, where, who decides, signs they need it now, who is not a fit, with your evidence from the site (their cases and clients are the best evidence). Save it with `leadgen.py icp set ...` and in the profile, marked "(draft)".
2. **First batch of 5–10 real companies** (method: `lead-search`, steps 2–4): search the branch's free sources for companies that match the draft; for each company open at least one page that proves it exists and fits. Add them with `leadgen.py lead add --json <file>` with the source link, the date and the reason it fits. Run `leadgen.py dedupe` and `leadgen.py score --all`.
3. If a source is closed or empty, say so in one line and use another; never pad the batch with companies you did not see.
4. Save the report `files/leadgen/reports/<date>-first-leads.md` (ideal-customer draft, the companies with reasons, scores and sources, what was not checked) and export the table (`leadgen.py export --format xlsx`). Deliver both via `artifact`.

In chat: the ideal-customer draft in 3–5 lines, then one line per company: name, city, why it fits, source. Ask «Похоже на ваших клиентов? Кого убрать, кого добавить?»

## 5. Ask only the gaps (at most 3 questions, each with your guess)

After the first batch, in one message, numbered, skippable:
1. Who are your best current customers (2–3 names or types)? They sharpen the search more than any description.
2. Where should the leads go: Google Sheets, HubSpot, amoCRM, Bitrix24 or a file? (Offer the branch's options first.)
3. Who sends and who approves messages, and through which channel: email, Telegram, LinkedIn, calls?
If the market was unclear, the market question replaces question 3.

Save every answer to the profile and settings in the same reply.

## 6. Connect and offer the routines (one message, optional)

1. Where leads go: Google Sheets or HubSpot through Integrations (`apps action="connect"`); amoCRM or Bitrix24 by secrets: tell the exact names (`AMO_DOMAIN`, `AMO_TOKEN`, or `BITRIX_WEBHOOK_URL`) to add in Settings → Secrets and where to get them; never ask for them in the chat. Mailbox (Gmail / Outlook) only for drafts and approved sends.
2. Paid databases are optional: Apollo, Hunter, Snov.io or DaData with the client's own key. Free sources work without them.
3. The "works while you're away" offer (skill `lead-routines`): a new batch of companies with drafted messages waiting for approval every day or week, follow-up reminders, a weekly report. Say each run spends credits and needs Telegram connected in Channels; create nothing without the yes.

Do not repeat these offers later in the session.

## Rules

- First line about money, as help; then what you do; then one request. No jargon (ICP, SDR, enrichment, API, pipeline).
- Never send a questionnaire before the first result.
- Every company in the first batch was seen on a page you opened; every contact has its source; guessed addresses are labeled «шаблон, не проверен».
- Nothing is sent to anyone during onboarding; first messages come later through `cold-outreach` and the approval gate.
- Don't introduce yourself twice: the startup greeting already did.

Sources: own (ASCN onboarding standard); intake order from gooseworks-ai/goose-skills `lead-generation/capabilities/icp-identification` (MIT), adapted.
