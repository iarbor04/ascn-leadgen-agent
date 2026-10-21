# Outreach rules and the legal note by market

Kevin is not a lawyer. Give the short note below once per market at onboarding, in plain words, and save the date in the profile ("Legal note given"). Do not quote article numbers or fines beyond what is here; if the user wants details, open the official link in the same reply, or route them to Lara. The links were opened on 2026-10-21 (ftc.gov may refuse automated reading: then find the guide by search). Open the link again before quoting anything more specific.

## Russia (`ru`)

Plain note to the user (adapt the words, keep the meaning):
> Пишем только на открытые рабочие контакты компаний и только по делу. Закон о персональных данных (152-ФЗ) касается и рабочих адресов конкретных людей, поэтому я храню только то, что опубликовано открыто, с источником, и сразу удаляю человека из рассылки по первой просьбе. Закон о рекламе (38-ФЗ) требует согласия на рекламные рассылки, поэтому мы не делаем массовую рекламу: каждое письмо — личное деловое предложение конкретной компании, с понятным способом отказаться. Это не юридическая консультация; если нужна проверка — подключим юриста (Лару).

Links to open before quoting details:
- 152-ФЗ «О персональных данных»: https://www.consultant.ru/document/cons_doc_LAW_61801/
- 38-ФЗ «О рекламе», статья 18: https://www.consultant.ru/document/cons_doc_LAW_58968/

## International (`intl`)

Plain note to the user:
> We only use public business contacts and write one relevant, personal message per company. In the US (CAN-SPAM) every commercial email needs an honest subject and sender, must be recognizable as a business offer, carries your postal address and a working way to opt out that we honor, and the law makes no exception for business-to-business email. In Europe and the UK (GDPR and local e-privacy rules) a named person's work address is personal data: we keep only what is public, with its source, tell people how to stop, and remove them at once; some countries (for example Germany) require prior consent even for business emails, so we check before writing there. This is not legal advice.

Links to open before quoting details:
- CAN-SPAM compliance guide (FTC): https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business
- GDPR text: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- UK ICO guidance on B2B marketing: https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/

## Rules for every message (both markets)

1. One company, one relevant reason, one ask. No mass identical blasts.
2. Every fact about the prospect comes from a saved source; the batch lists the facts used.
3. Every cold message and follow-up ends with an opt-out line (settings.json → `sender.opt_out_line_ru` / `opt_out_line_en`). Email for the US also carries the sender's postal address from the profile; if it is missing, it is a `[placeholder]` and the batch is blocked.
4. Honest subject and sender: no "Re:" or "Fwd:" on a first message, no fake familiarity («как договаривались»), no invented mutual contacts.
5. Daily limits from settings.json (`limits`) per channel; `outbox approve` splits a bigger batch over days.
6. A reply "no", "не интересно", "не пишите", an unsubscribe request or a complaint → `reply --class no|opt_out`: stopped and on the do-not-contact list for good.
7. Telegram and LinkedIn messages go from the owner's own account and follow the platform's rules; Kevin prepares paste-ready texts, the owner sends them.
8. Calls: only company and work numbers; respect "не звоните".
