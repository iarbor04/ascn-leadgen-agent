# Market branch

Decides which sources, CRMs, channels and legal note Kevin uses. Set once at onboarding and stored as `market` (`ru`, `intl` or `both`) in `files/leadgen/settings.json` and in the profile ("Market"), with the evidence and the date. Every skill reads it before suggesting a source or a tool.

## Values

- `ru`: the client sells in Russia (or to Russian companies).
- `intl`: everywhere else.
- CIS (Kazakhstan, Belarus, Uzbekistan and others): ask where their customers are. Russian sources (2GIS, hh.ru, Rusprofile) cover parts of the CIS; registers differ by country.
- `both`: set `both` and keep the two source lists apart per batch.

What matters is where the **client's customers** are, not where the client is registered or which language the chat uses.

## How to detect

| Strong `ru` signals | Strong `intl` signals |
|---|---|
| domain .ru / .рф / .su | prices in $, €, £ or other non-ruble currencies |
| ИНН, ОГРН, «ООО», «ИП» on the site | a non-Russian legal address |
| prices in ₽ / руб. | Stripe, PayPal, Shopify, HubSpot forms |
| a Russian address, cities of Russia in cases | LinkedIn, X as the main channels |
| amoCRM / Bitrix24 widgets, Telegram and VK as the main channels | case studies with foreign companies |
| tenders, 44-ФЗ / 223-ФЗ mentioned | |

Not signals on their own: the chat language; a +7 phone (Kazakhstan uses it too).

Rule: 2 or more strong signals one way and none the other → set it and say it in one line so the user can correct it. Mixed or none → ask one question: «Где ваши клиенты: в России и СНГ или за рубежом?»

## What changes by branch

| Area | `ru` | `intl` |
|---|---|---|
| Company lists | 2GIS and Yandex Maps cards found by search; Rusprofile / Checko public pages; client's CSV exports | Google Maps listings found by search; company sites; public LinkedIn company pages found by search; client's CSV exports |
| Company check | ФНС register (`leadgen.py egrul`), DaData with the client's key | company site, public registers of the country (opened by link), Apollo with the client's key |
| Buying signals | hh.ru vacancies (`leadgen.py hh`), zakupki.gov.ru tenders, new branches on 2GIS, public Telegram channels | job boards and careers pages, funding news, new offices, site changes |
| Contacts | public work addresses on the site, `pattern` + Hunter verify with the client's key | the same; Apollo / Hunter / Snov.io with the client's key |
| Channels | email, Telegram (paste-ready from the owner's account), calls | email, LinkedIn (paste-ready unless connected), calls |
| Where leads go | amoCRM, Bitrix24 (keys in Secrets), Google Sheets, CSV/XLSX | Google Sheets, HubSpot (apps), CSV/XLSX |
| Legal note | 152-ФЗ and 38-ФЗ (`outreach-rules.md`) | GDPR (Europe, UK), CAN-SPAM (US) (`outreach-rules.md`) |

Save `market`, `market_evidence` (2–3 signals) and the date. If the user corrects it, overwrite and follow the new branch from then on.
