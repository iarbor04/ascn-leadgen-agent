# Lead sources: what Kevin may use and how

Every lead and contact is saved with the URL (or file name) where it was seen and the date. Read single public pages with `web_fetch`; find them with `web_search`. No bulk crawling, no logging in, no bypassing a block or a captcha: if a page refuses automated reading, say «источник закрыт для автоматического чтения» and offer the manual route or an export file.

Paid databases are used only with the client's own key in Settings → Secrets. Free sources are the default.

## Russia and CIS

| Source | How | What to take | Limits |
|---|---|---|---|
| 2GIS cards | `web_search` "site:2gis.ru <рубрика> <город>", open single cards | name, address, rubric, company phone, site, card URL | the 2GIS terms forbid automated collection: single cards only; for volume the client exports from their own 2GIS account and sends the file (`lead import --format 2gis`) |
| Yandex Maps cards | `web_search` "<рубрика> <город> яндекс карты", open the organization page | name, address, rubric, site | same as 2GIS; pages often load by script and may be unreadable: then use the company site |
| Company sites | `web_fetch` home, about, contacts, team, careers pages | what they do, size hints, public work addresses, people named on the team page | only what is written |
| ФНС register | `leadgen.py egrul <ИНН or name>` | full name, ИНН, ОГРН, address, registration date, active or ceased, head (register data, not a contact) | free; a captcha or a block means «не проверено»; it may be unreachable from outside Russia |
| Rusprofile, Checko | open the public company page found by search | ИНН, ОКВЭД, size class, revenue if shown, head | public pages, single lookups; their terms restrict automated copying |
| hh.ru | `leadgen.py hh "<role>" --area <id>` | employers hiring for roles your offer replaces or supports (a buying signal) | free API; if anonymous access is closed, a free application token `HH_APP_TOKEN` from dev.hh.ru |
| zakupki.gov.ru | `web_search` "site:zakupki.gov.ru <предмет>", open the notice | customer, subject, deadline, notice URL (a buying signal) | public; may be unreachable from outside Russia |
| Public Telegram | `web_fetch https://t.me/s/<channel>` | companies posting needs or openings, public chats' "ищем подрядчика" posts | public channels only; never join private chats or collect members |
| DaData (key) | `leadgen.py dadata <ИНН>` | status, address, ОКВЭД, staff count | the client's `DADATA_API_KEY` (free tier exists) |

## International

| Source | How | What to take | Limits |
|---|---|---|---|
| Google Maps listings | `web_search` "<category> in <city>", open the business site | name, address, site, company phone | the Places API needs a key and is not built in; use search results and the business site |
| Company sites | as above | as above | as above |
| LinkedIn | `web_search` "site:linkedin.com/company <niche> <city>" or "site:linkedin.com/in <title> <company>" | the company page, a person's public name and title from the result | LinkedIn's terms forbid scraping: use search results and public pages only, never log in; a Sales Navigator export from the client is a file input |
| Job boards and careers pages | `web_search` "<role> jobs <city>", the company's /careers page | companies hiring for the role (a buying signal) | public pages |
| Funding and news | `web_search` "<niche> raised seed OR series <year>", company news pages | funding round, new office, launch (a signal) | cite the article |
| Apollo (key) | `leadgen.py apollo people --domain <d> --titles <a,b>` | roles and names at a company | the client's `APOLLO_API_KEY`; its CSV export goes through `lead import --format apollo` |
| Hunter (key) | `leadgen.py hunter domain <d>`, `hunter verify <email>` | public addresses with the pages they were found on; verification | the client's `HUNTER_API_KEY` |
| Snov.io | CSV export from the client's account | contacts | `lead import --format generic` with `--map` |

## Never

- Data behind a login (LinkedIn, Facebook, private Telegram chats, CRMs of others).
- Bought, leaked or "parsed" databases of unknown origin.
- Personal mobile or home numbers of individuals; `lead import` drops such columns.
- Guessing a person or a title that no source shows.
