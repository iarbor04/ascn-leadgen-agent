#!/usr/bin/env python3
"""Kevin's lead store, checks and connectors. Standard library only. Every command prints short JSON.

Data lives in files/leadgen/ (leads/, outbox/, sequences/, exports/, reports/, logs/, settings.json, profile/).
Secrets come from Settings -> Secrets as environment variables; they are never printed or saved.
A source that cannot be reached returns "status": "not checked" with the reason: never zero, never "not found".

  context                                  profile, ideal customer, counts, due follow-ups, outbox, routines, limits
  icp show | icp set [--industries a,b] [--regions a,b] [--size-min N] [--size-max N] [--roles a,b]
                     [--exclude a,b] [--keywords a,b]       the fit criteria the scoring uses
  lead add --company NAME --source URL [--seen DATE] [--domain D] [--inn N] [--city C] ... [--contact-name ...]
  lead add --json FILE                     a JSON list of leads (see LEAD_FIELDS); merges into existing leads on
                                           domain, INN/OGRN, email or phone; a same-name match is only flagged
  lead import FILE.csv [--format apollo|hunter|2gis|generic] [--map "csv column=field,..."] [--source TEXT]
  lead list [--stage S] [--tier A] [--min-score N] [--batch B] [--limit N]
  lead show ID | lead set-stage ID STAGE [--note T] | lead contact ID ... | lead signal ID --type T --detail D --source URL
  dedupe [--apply]                         duplicate groups (sure: domain, INN, OGRN, email, phone; possible: name)
  score [--id ID] [--all]                  fit + intent score, tier and the reason list, from settings.json
  egrul INN|NAME                           ФНС open register (egrul.nalog.ru), free; captcha or block -> not checked
  hh QUERY [--area N] [--pages N]          hh.ru public vacancies grouped by employer (hiring = buying signal)
  dadata INN|QUERY                         company card from DaData            needs DADATA_API_KEY
  hunter domain D | hunter verify EMAIL | hunter find D FIRST LAST          needs HUNTER_API_KEY
  apollo people --domain D [--titles a,b] [--limit N]                       needs APOLLO_API_KEY
  mx DOMAIN|EMAIL [--update]               MX records via DNS-over-HTTPS (free); domain accepts mail != mailbox exists
  pattern DOMAIN --first F --last L        candidate addresses, always labeled "pattern, not verified"
  seq plan ID [--channel email] [--to X] [--start DATE] [--steps N] | seq due [--date D] [--days N]
  seq mark ID STEP sent|skipped [--date D] | seq stop ID --reason R | seq list
  reply ID --class interested|question|meeting|not_now|no|opt_out|out_of_office|wrong_person|bounce [--note T]
  dnc add VALUE|ID [--reason R] | dnc check VALUE... [--lead ID] [--batch B] | dnc list
  outbox new --file F [--channel email|telegram|linkedin|call]   drafted messages, checked, awaiting approval
  outbox list | outbox show B [--md] | outbox approve B --by NAME [--note T] | outbox cancel B
  outbox mark B MSG_ID|today sent|failed|skipped [--error T]      only approved messages can be marked sent
  export --format amocrm|bitrix|hubspot|sheets|csv|xlsx [--stage S] [--min-score N] [--ids a,b] [--out PATH]
  crm push --to amocrm|bitrix [--stage S] [--ids a,b] [--yes]     dry run by default; --yes writes and reads back
                                           amoCRM: AMO_DOMAIN, AMO_TOKEN; Bitrix24: BITRIX_WEBHOOK_URL
  report weekly [--from D] [--to D]        found, contacted, replied, meetings, stage moves, forecast health
  check                                    consistency of the store: sources, gates, DNC, sequences

Test hooks: LEADGEN_DATA (data folder), LEADGEN_TODAY (YYYY-MM-DD).
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("PACKAGE_ROOT") or HERE.parents[1])
UA = "ascn-leadgen/1.0 (+https://ascn.ai)"
STAGES = ["new", "qualified", "contacted", "replied", "meeting", "proposal", "won", "lost", "not_now", "dnc"]
CLOSED = {"won", "lost", "dnc"}
EMAIL_STATUSES = ["public", "verified", "unverified", "pattern", "invalid"]
SENDABLE = {"public", "verified"}
SIGNAL_TYPES = ["hiring", "tender", "funding", "new_branch", "site_change", "inbound", "referral", "news", "other"]
CHANNELS = ["email", "telegram", "linkedin", "call"]
FREE_MAIL = {"gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com", "icloud.com", "me.com",
             "mail.ru", "bk.ru", "inbox.ru", "list.ru", "yandex.ru", "ya.ru", "yandex.com", "rambler.ru", "proton.me",
             "protonmail.com", "gmx.de", "gmx.net", "aol.com"}
LEGAL_FORMS = {"ооо", "оао", "зао", "пао", "ао", "ип", "нко", "ано", "гк", "llc", "ltd", "inc", "gmbh", "co", "corp",
               "corporation", "limited", "plc", "sa", "srl", "bv", "ag", "company", "компания", "группа", "group"}
SECRET_ENV = ["AMO_DOMAIN", "AMO_TOKEN", "BITRIX_WEBHOOK_URL", "HUNTER_API_KEY", "APOLLO_API_KEY", "DADATA_API_KEY",
              "DADATA_SECRET_KEY", "HH_APP_TOKEN"]
LEAD_FIELDS = ["company", "domain", "website", "inn", "ogrn", "city", "country", "address", "industry", "size", "phone",
               "email", "reason", "batch", "market", "source", "seen", "what", "contacts", "signals", "notes"]


# ---------- basics ----------

def data_dir():
    return Path(os.environ.get("LEADGEN_DATA") or ROOT / "files" / "leadgen")


def today():
    t = os.environ.get("LEADGEN_TODAY")
    return date.fromisoformat(t) if t else date.today()


def now_iso():
    if os.environ.get("LEADGEN_TODAY"):
        return os.environ["LEADGEN_TODAY"] + "T12:00:00Z"
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scrub(text):
    """Removes secret values from any text before it is printed."""
    s = str(text)
    for k in SECRET_ENV:
        v = os.environ.get(k)
        if v and len(v) >= 4:
            s = s.replace(v, f"[{k}]")
    return s


def out(obj, code=0):
    print(scrub(json.dumps(obj, ensure_ascii=False, indent=1)))
    sys.exit(code)


def fail(error, hint=None, **extra):
    d = {"ok": False, "error": error}
    if hint:
        d["hint"] = hint
    d.update(extra)
    out(d, 1)


def load(path, default):
    p = data_dir() / path
    if not p.is_file():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        fail(f"{path} is not valid JSON", "show the file to the owner before changing it; never overwrite it silently")


def save(path, obj):
    p = data_dir() / path
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)


def settings():
    s = load("settings.json", {})
    s.setdefault("icp", {})
    s.setdefault("scoring", {})
    s.setdefault("limits", {})
    s.setdefault("sender", {})
    s.setdefault("sequence", {})
    s.setdefault("routines", {})
    return s


def log_event(kind, **kw):
    p = data_dir() / "logs" / "events.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": now_iso(), "date": today().isoformat(), "type": kind, **kw}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def events():
    p = data_dir() / "logs" / "events.jsonl"
    res = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                res.append(json.loads(line))
            except ValueError:
                continue
    return res


def csv_list(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def parse_date(s, default=None):
    if not s:
        return default
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        fail(f"bad date {s!r}", "use YYYY-MM-DD")


# ---------- normalization ----------

def norm_domain(s):
    s = (s or "").strip().lower()
    if not s:
        return ""
    if "@" in s and "/" not in s:
        s = s.split("@", 1)[1]
    s = re.sub(r"^[a-z]+://", "", s)
    s = s.split("/")[0].split("?")[0].split(":")[0]
    s = s[4:] if s.startswith("www.") else s
    return s if "." in s else ""


def company_domain(s):
    d = norm_domain(s)
    return "" if d in FREE_MAIL else d


def norm_email(s):
    s = (s or "").strip().lower().strip("<>.,;")
    if s.startswith("mailto:"):
        s = s[7:]
    return s if re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-zа-я0-9\-]{2,}", s) else ""


def norm_phone(s):
    d = re.sub(r"\D", "", s or "")
    if len(d) == 11 and d.startswith("8"):
        d = "7" + d[1:]
    return "+" + d if len(d) >= 10 else ""


def norm_name(s):
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[«»\"'“”„`]", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    words = [w for w in s.split() if w not in LEGAL_FORMS]
    return " ".join(words)


def norm_inn(s):
    d = re.sub(r"\D", "", str(s or ""))
    return d if len(d) in (10, 12) else ""


def norm_ogrn(s):
    d = re.sub(r"\D", "", str(s or ""))
    return d if len(d) in (13, 15) else ""


def parse_size(s):
    """'51-200', '200+', '~50', '120 сотрудников' -> (low, high) or None."""
    if s is None or s == "":
        return None
    nums = [int(x) for x in re.findall(r"\d+", str(s).replace(" ", ""))]
    if not nums:
        return None
    if len(nums) >= 2:
        return min(nums[:2]), max(nums[:2])
    if "+" in str(s):
        return nums[0], 10 ** 7
    return nums[0], nums[0]


# ---------- the lead store ----------

def store():
    st = load("leads/leads.json", {"next": 1, "leads": {}})
    st.setdefault("next", 1)
    st.setdefault("leads", {})
    return st


def save_store(st):
    save("leads/leads.json", st)


def keys_of(lead):
    """Strong keys (sure duplicates) and the weak name key."""
    strong = set()
    if lead.get("domain"):
        strong.add("domain:" + lead["domain"])
    if lead.get("inn"):
        strong.add("inn:" + lead["inn"])
    if lead.get("ogrn"):
        strong.add("ogrn:" + lead["ogrn"])
    if lead.get("phone"):
        strong.add("phone:" + lead["phone"])
    if lead.get("email"):
        strong.add("email:" + lead["email"])
    for c in lead.get("contacts") or []:
        if c.get("email"):
            strong.add("email:" + c["email"])
    name = lead.get("name_norm") or norm_name(lead.get("company"))
    weak = "name:" + name + "|" + (lead.get("city") or "").lower() if name else None
    return strong, weak


def make_source(src, seen=None, what=None):
    if isinstance(src, dict):
        url = (src.get("url") or "").strip()
        seen = src.get("seen") or seen
        what = src.get("what") or what
    else:
        url = (src or "").strip()
    if not url:
        return None
    return {"url": url, "seen": str(parse_date(seen, today())), "what": what or ""}


def clean_contact(c, default_seen=None):
    """Returns (contact, error). Every contact needs a source; a guessed address stays labeled 'pattern'."""
    src = make_source(c.get("source"), c.get("seen") or default_seen)
    if not src:
        return None, "contact without source: say where the person and the contact were seen"
    email = norm_email(c.get("email"))
    status = (c.get("email_status") or ("unverified" if email else "")).lower()
    if email and status not in EMAIL_STATUSES:
        return None, f"email_status must be one of {EMAIL_STATUSES}"
    if c.get("email") and not email:
        return None, f"not an email address: {c.get('email')!r}"
    name = (c.get("name") or "").strip()
    if not (name or email or c.get("linkedin") or c.get("telegram")):
        return None, "empty contact"
    return {"name": name, "title": (c.get("title") or "").strip(), "email": email, "email_status": status if email else "",
            "linkedin": (c.get("linkedin") or "").strip(), "telegram": (c.get("telegram") or "").strip(),
            "phone": norm_phone(c.get("phone")), "phone_kind": "work" if c.get("phone") else "",
            "source": src, "mx": c.get("mx", "")}, None


def clean_signal(s, default_seen=None):
    src = make_source(s.get("source"), s.get("seen") or default_seen)
    if not src:
        return None, "signal without source"
    kind = (s.get("type") or "other").lower()
    if kind not in SIGNAL_TYPES:
        kind = "other"
    return {"type": kind, "detail": (s.get("detail") or "").strip(), "source": src,
            "date": str(parse_date(s.get("date") or src["seen"], today()))}, None


def clean_lead(raw):
    """Returns (lead, errors). A lead needs a company name and a source."""
    errors = []
    company = (raw.get("company") or "").strip()
    if not company:
        return None, ["company name is required"]
    src = make_source(raw.get("source"), raw.get("seen"), raw.get("what"))
    if not src:
        return None, [f"{company}: no source; every lead needs the link (or file) where it was seen and the date"]
    website = (raw.get("website") or "").strip()
    domain = company_domain(raw.get("domain") or website or raw.get("email"))
    lead = {"company": company, "name_norm": norm_name(company), "domain": domain,
            "website": website or (f"https://{domain}" if domain else ""),
            "inn": norm_inn(raw.get("inn")), "ogrn": norm_ogrn(raw.get("ogrn")),
            "city": (raw.get("city") or "").strip(), "country": (raw.get("country") or "").strip(),
            "address": (raw.get("address") or "").strip(), "industry": (raw.get("industry") or "").strip(),
            "size": str(raw.get("size") or "").strip(), "phone": norm_phone(raw.get("phone")),
            "email": norm_email(raw.get("email")), "reason": (raw.get("reason") or "").strip(),
            "batch": (raw.get("batch") or "").strip(), "market": (raw.get("market") or "").strip(),
            "sources": [src], "contacts": [], "signals": [], "notes": []}
    if raw.get("inn") and not lead["inn"]:
        errors.append(f"{company}: INN {raw.get('inn')!r} is not 10 or 12 digits, left empty")
    for c in raw.get("contacts") or []:
        cc, err = clean_contact(c, src["seen"])
        if err:
            errors.append(f"{company}: {err}")
        else:
            lead["contacts"].append(cc)
    for s in raw.get("signals") or []:
        ss, err = clean_signal(s, src["seen"])
        if err:
            errors.append(f"{company}: {err}")
        else:
            lead["signals"].append(ss)
    for n in raw.get("notes") or []:
        lead["notes"].append({"date": today().isoformat(), "text": str(n)})
    return lead, errors


def merge_into(dst, src):
    """Adds what dst lacks; never overwrites a value the store already has."""
    changed = []
    for k in ["domain", "website", "inn", "ogrn", "city", "country", "address", "industry", "size", "phone", "email",
              "reason", "market"]:
        if src.get(k) and not dst.get(k):
            dst[k] = src[k]
            changed.append(k)
    for s in src.get("sources") or []:
        if s["url"] not in {x["url"] for x in dst.get("sources", [])}:
            dst.setdefault("sources", []).append(s)
            changed.append("sources")
    have = {(c.get("email") or c.get("linkedin") or c.get("name")).lower() for c in dst.get("contacts", [])}
    for c in src.get("contacts") or []:
        key = (c.get("email") or c.get("linkedin") or c.get("name")).lower()
        if key not in have:
            dst.setdefault("contacts", []).append(c)
            have.add(key)
            changed.append("contacts")
    sig = {(s["type"], s["detail"]) for s in dst.get("signals", [])}
    for s in src.get("signals") or []:
        if (s["type"], s["detail"]) not in sig:
            dst.setdefault("signals", []).append(s)
            changed.append("signals")
    dst.setdefault("notes", []).extend(src.get("notes") or [])
    dst["updated"] = now_iso()
    return sorted(set(changed))


def find_match(st, lead):
    strong, weak = keys_of(lead)
    possible = []
    for lid, other in st["leads"].items():
        s2, w2 = keys_of(other)
        if strong & s2:
            return lid, sorted(strong & s2), []
        if weak and weak == w2:
            possible.append(lid)
    return None, [], possible


def add_leads(raws):
    st = store()
    dnc = load_dnc()
    res = {"ok": True, "added": [], "merged": [], "possible_duplicates": [], "rejected": [], "in_dnc": []}
    for raw in raws:
        lead, errors = clean_lead(raw)
        if not lead:
            res["rejected"] += errors
            continue
        res["rejected"] += errors
        hit = dnc_match(dnc, lead_values(lead))
        lid, keys, possible = find_match(st, lead)
        if lid:
            changed = merge_into(st["leads"][lid], lead)
            res["merged"].append({"id": lid, "company": st["leads"][lid]["company"], "by": keys, "added": changed})
            continue
        lid = f"L{st['next']:04d}"
        st["next"] += 1
        lead.update({"id": lid, "stage": "dnc" if hit else "new", "score": None, "tier": None, "score_reasons": [],
                     "created": now_iso(), "updated": now_iso(), "history": [{"date": today().isoformat(),
                                                                                "stage": "dnc" if hit else "new"}],
                     "crm": {}})
        st["leads"][lid] = lead
        res["added"].append({"id": lid, "company": lead["company"]})
        if hit:
            res["in_dnc"].append({"id": lid, "company": lead["company"], "match": hit})
        if possible:
            res["possible_duplicates"].append({"id": lid, "same_name_as": possible})
        log_event("lead_added", lead=lid, source=lead["sources"][0]["url"], batch=lead.get("batch"))
    save_store(st)
    res["counts"] = {k: len(v) for k, v in res.items() if isinstance(v, list)}
    return res


def get_lead(st, lid):
    lead = st["leads"].get((lid or "").upper())
    if not lead:
        fail(f"no lead {lid}", "lead list shows the ids")
    return lead


def short(lead):
    best = next((c for c in lead.get("contacts", []) if c.get("email_status") in SENDABLE), None) or \
        (lead.get("contacts") or [None])[0]
    return {"id": lead["id"], "company": lead["company"], "domain": lead.get("domain"), "city": lead.get("city"),
            "stage": lead.get("stage"), "score": lead.get("score"), "tier": lead.get("tier"),
            "contact": {k: best.get(k) for k in ("name", "title", "email", "email_status")} if best else None,
            "source": lead["sources"][0]["url"] if lead.get("sources") else None}


def set_stage(lead, stage, note=None):
    if stage not in STAGES:
        fail(f"unknown stage {stage}", f"one of {STAGES}")
    old = lead.get("stage")
    lead["stage"] = stage
    lead.setdefault("history", []).append({"date": today().isoformat(), "stage": stage})
    if note:
        lead.setdefault("notes", []).append({"date": today().isoformat(), "text": note})
    lead["updated"] = now_iso()
    log_event("stage", lead=lead["id"], old=old, new=stage)


# ---------- CSV import ----------

SYNONYMS = {
    "company": ["company", "company name", "organization", "organisation", "account name", "компания", "название",
                "наименование", "название компании", "организация", "name"],
    "website": ["website", "site", "url сайта", "сайт", "веб-сайт", "company website", "domain", "domain name", "домен"],
    "inn": ["inn", "инн"], "ogrn": ["ogrn", "огрн"],
    "city": ["city", "company city", "город"], "country": ["country", "company country", "страна"],
    "address": ["address", "company address", "адрес"],
    "industry": ["industry", "category", "rubric", "отрасль", "рубрика", "рубрики", "категория", "сфера"],
    "size": ["# employees", "employees", "company size", "headcount", "сотрудников", "численность", "штат"],
    "phone": ["company phone", "corporate phone", "phone", "телефон", "телефоны", "рабочий телефон"],
    "email": ["company email", "e-mail", "email компании", "почта"],
    "source": ["source", "source url", "url", "link", "ссылка", "источник", "ссылка 2гис", "2gis url", "карточка"],
    "contact_first": ["first name", "first", "имя"], "contact_last": ["last name", "last", "фамилия"],
    "contact_name": ["full name", "contact name", "контакт", "контактное лицо", "фио"],
    "title": ["title", "position", "job title", "должность"],
    "contact_email": ["email", "email address", "work email", "e-mail контакта"],
    "email_status": ["email status", "verification status", "status"],
    "linkedin": ["person linkedin url", "linkedin url", "linkedin", "linkedin profile"],
    "contact_phone": ["work direct phone", "direct phone"],
}
PRIVATE_PHONE_COLUMNS = ["mobile phone", "home phone", "personal phone", "мобильный", "личный телефон", "other phone"]
FORMAT_HINTS = {"apollo": {"company": "company", "contact_email": "email"},
                "hunter": {"company": "organization", "contact_email": "email address", "website": "domain name"}}


def map_columns(header, fmt, custom):
    low = {h.strip().lower(): h for h in header}
    mapping = {}
    for k, v in (FORMAT_HINTS.get(fmt) or {}).items():
        if v in low:
            mapping[k] = low[v]
    for field, names in SYNONYMS.items():
        if field in mapping:
            continue
        for n in names:
            if n in low and low[n] not in mapping.values():
                mapping[field] = low[n]
                break
    if fmt == "2gis" and "email" not in mapping and "contact_email" in mapping:
        mapping["email"] = mapping.pop("contact_email")  # a 2GIS card shows the company address, not a person's
    for pair in csv_list(custom):
        if "=" in pair:
            col, field = [x.strip() for x in pair.split("=", 1)]
            if col.lower() in low:
                mapping[field] = low[col.lower()]
    private = [low[c] for c in PRIVATE_PHONE_COLUMNS if c in low]
    return mapping, private


def email_status_from(value, fmt):
    v = (value or "").strip().lower()
    if v in ("verified", "valid", "deliverable"):
        return "verified"
    if v in ("guessed", "extrapolated", "pattern", "likely to engage", "catch-all"):
        return "pattern" if v != "catch-all" else "unverified"
    if v in ("invalid", "undeliverable", "bounced"):
        return "invalid"
    return "unverified"


def read_table(path):
    p = Path(path)
    if not p.is_file():
        fail(f"no file {path}")
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "cp1251"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        fail("cannot decode the file", "save it as CSV in UTF-8")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    return rows, (list(rows[0].keys()) if rows else [])


def cmd_import(a):
    rows, header = read_table(a.file)
    if not rows:
        fail("the file has no rows")
    fmt = a.format or "generic"
    mapping, private = map_columns(header, fmt, a.map)
    if "company" not in mapping:
        fail("no company column found", "pass --map \"<your column>=company\"", columns=header)
    default_src = a.source or f"file:{Path(a.file).name} ({fmt} export)"
    raws, dropped_private = [], 0
    for r in rows:
        g = lambda f: (r.get(mapping[f]) or "").strip() if f in mapping else ""  # noqa: E731
        if any((r.get(c) or "").strip() for c in private):
            dropped_private += 1
        src = g("source") or default_src
        raw = {"company": g("company"), "website": g("website"), "inn": g("inn"), "ogrn": g("ogrn"), "city": g("city"),
               "country": g("country"), "address": g("address"), "industry": g("industry"), "size": g("size"),
               "phone": g("phone"), "email": g("email"), "source": src, "seen": a.seen, "batch": a.batch or "",
               "what": f"row from {Path(a.file).name}"}
        name = g("contact_name") or " ".join(x for x in (g("contact_first"), g("contact_last")) if x)
        cemail = g("contact_email")
        if name or cemail or g("linkedin"):
            raw["contacts"] = [{"name": name, "title": g("title"), "email": cemail,
                                "email_status": email_status_from(g("email_status"), fmt) if cemail else "",
                                "linkedin": g("linkedin"), "phone": g("contact_phone"), "source": src, "seen": a.seen}]
        raws.append(raw)
    res = add_leads(raws)
    res["mapping"] = mapping
    res["rows"] = len(rows)
    if private:
        res["private_phones_ignored"] = {"columns": private, "rows_with_value": dropped_private,
                                         "why": "personal mobile and home numbers are never stored"}
    out(res)


# ---------- do-not-contact ----------

def load_dnc():
    return load("leads/dnc.json", {"entries": []})


def dnc_kind(v):
    v = v.strip()
    if norm_email(v):
        return "email", norm_email(v)
    if norm_inn(v) and re.fullmatch(r"\d+", v):
        return "inn", norm_inn(v)
    if norm_phone(v) and re.fullmatch(r"[\d\s()+\-]+", v):
        return "phone", norm_phone(v)
    if norm_domain(v):
        return "domain", norm_domain(v)
    return "name", norm_name(v)


def lead_values(lead):
    vals = []
    if lead.get("domain"):
        vals.append(("domain", lead["domain"]))
    if lead.get("inn"):
        vals.append(("inn", lead["inn"]))
    if lead.get("phone"):
        vals.append(("phone", lead["phone"]))
    if lead.get("email"):
        vals.append(("email", lead["email"]))
    for c in lead.get("contacts") or []:
        if c.get("email"):
            vals.append(("email", c["email"]))
        if c.get("phone"):
            vals.append(("phone", c["phone"]))
    return vals


def dnc_match(dnc, values):
    hits = []
    entries = {(e["kind"], e["value"]) for e in dnc.get("entries", [])}
    for kind, v in values:
        if (kind, v) in entries:
            hits.append(f"{kind}:{v}")
        if kind == "email" and ("domain", v.split("@", 1)[1]) in entries:
            hits.append(f"domain:{v.split('@', 1)[1]}")
    return sorted(set(hits))


def dnc_add_values(values, reason, lead_id=None):
    dnc = load_dnc()
    have = {(e["kind"], e["value"]) for e in dnc["entries"]}
    added = []
    for kind, v in values:
        if v and (kind, v) not in have:
            dnc["entries"].append({"kind": kind, "value": v, "reason": reason or "", "added": today().isoformat(),
                                   "lead": lead_id or ""})
            have.add((kind, v))
            added.append(f"{kind}:{v}")
    save("leads/dnc.json", dnc)
    if added:
        log_event("dnc", lead=lead_id, values=added, reason=reason)
    return added


def cmd_dnc(a):
    if a.action == "list":
        d = load_dnc()
        out({"ok": True, "count": len(d["entries"]), "entries": d["entries"][-200:]})
    if a.action == "add":
        if not a.values:
            fail("nothing to add")
        st = store()
        values, lead_ids = [], []
        for v in a.values:
            if re.fullmatch(r"[Ll]\d{4,}", v):
                lead = get_lead(st, v)
                values += lead_values(lead) or [("name", lead["name_norm"])]
                lead_ids.append(lead["id"])
            else:
                values.append(dnc_kind(v))
        added = dnc_add_values(values, a.reason, ",".join(lead_ids) or None)
        stopped = []
        seqs = load("sequences/sequences.json", {})
        for lid, lead in st["leads"].items():
            if dnc_match(load_dnc(), lead_values(lead)) or lid in lead_ids:
                if lead.get("stage") != "dnc":
                    set_stage(lead, "dnc", f"do not contact: {a.reason or 'owner request'}")
                if seqs.get(lid, {}).get("status") == "active":
                    seqs[lid].update({"status": "stopped", "stop_reason": "dnc", "stopped": today().isoformat()})
                    stopped.append(lid)
        save_store(st)
        save("sequences/sequences.json", seqs)
        out({"ok": True, "added": added, "sequences_stopped": stopped})
    # check
    values = [dnc_kind(v) for v in a.values or []]
    st = store()
    if a.lead:
        values += lead_values(get_lead(st, a.lead))
    if a.batch:
        b = load_batch(a.batch)
        for m in b["messages"]:
            values.append(dnc_kind(m["to"]))
            values += lead_values(st["leads"].get(m["lead"], {}))
    hits = dnc_match(load_dnc(), values)
    out({"ok": True, "checked": len(values), "blocked": bool(hits), "matches": hits})


# ---------- ideal customer and scoring ----------

def cmd_icp(a):
    s = settings()
    icp = s["icp"]
    if a.action == "set":
        for f in ("industries", "regions", "roles", "exclude", "keywords"):
            v = getattr(a, f)
            if v is not None:
                icp[f] = csv_list(v)
        if a.size_min is not None:
            icp["size_min"] = a.size_min
        if a.size_max is not None:
            icp["size_max"] = a.size_max
        icp["updated"] = today().isoformat()
        s["icp"] = icp
        save("settings.json", s)
    filled = [k for k in ("industries", "regions", "roles", "keywords") if icp.get(k)] + \
        (["size"] if icp.get("size_min") or icp.get("size_max") else [])
    out({"ok": True, "icp": icp, "criteria_set": filled,
         "ready_for_scoring": bool(filled), "hint": None if filled else "set at least one criterion: icp set --industries ..."})


def _hit(words, *texts):
    blob = " ".join(t for t in texts if t).lower().replace("ё", "е")
    return [w for w in words if w and w.lower().replace("ё", "е") in blob]


def score_lead(lead, s):
    icp, sc = s["icp"], s["scoring"]
    w = {"industry": 20, "region": 15, "size": 15, "role": 10, **(sc.get("fit") or {})}
    iw = {"hiring": 15, "tender": 20, "funding": 15, "new_branch": 10, "site_change": 5, "inbound": 25, "referral": 20,
          "news": 5, "other": 3, **(sc.get("intent") or {})}
    cap, days = sc.get("intent_cap", 40), sc.get("signal_days", 90)
    tiers = {"A": 70, "B": 45, **(sc.get("tiers") or {})}
    reasons, unknown = [], []
    excl = _hit(icp.get("exclude") or [], lead.get("industry"), lead.get("company"), lead.get("reason"))
    if excl:
        return 0, "DQ", [f"excluded: {', '.join(excl)}"], []
    if lead.get("stage") == "dnc" or dnc_match(load_dnc(), lead_values(lead)):
        return 0, "DQ", ["on the do-not-contact list"], []
    got = total = 0
    checks = []
    if icp.get("industries"):
        checks.append(("industry", _hit(icp["industries"] + (icp.get("keywords") or []), lead.get("industry"),
                                        lead.get("company"), lead.get("reason")),
                       bool(lead.get("industry") or lead.get("reason"))))
    if icp.get("regions"):
        checks.append(("region", _hit(icp["regions"], lead.get("city"), lead.get("country"), lead.get("address")),
                       bool(lead.get("city") or lead.get("country") or lead.get("address"))))
    if icp.get("size_min") or icp.get("size_max"):
        rng = parse_size(lead.get("size"))
        lo, hi = icp.get("size_min") or 0, icp.get("size_max") or 10 ** 7
        ok = bool(rng) and rng[1] >= lo and rng[0] <= hi
        checks.append(("size", [lead.get("size")] if ok else [], bool(rng)))
    if icp.get("roles"):
        titles = " | ".join(c.get("title", "") for c in lead.get("contacts") or [])
        checks.append(("role", _hit(icp["roles"], titles), bool(titles.strip())))
    if not checks:
        return None, None, [], ["ideal customer not set"]
    for name, hits, known in checks:
        total += w.get(name, 0)
        if hits:
            got += w.get(name, 0)
            reasons.append(f"{name}: match ({', '.join(str(h) for h in hits[:3])})")
        elif known:
            reasons.append(f"{name}: no match")
        else:
            unknown.append(name)
            reasons.append(f"{name}: not known")
    fit = round(60 * got / total) if total else 0
    intent, seen_types = 0, set()
    for sig in sorted(lead.get("signals") or [], key=lambda x: x.get("date", ""), reverse=True):
        if sig["type"] in seen_types:
            continue
        seen_types.add(sig["type"])
        age = (today() - parse_date(sig.get("date"), today())).days
        pts = iw.get(sig["type"], 3) * (1 if age <= days else 0.5)
        intent += pts
        reasons.append(f"signal {sig['type']} ({sig.get('date')}): {sig.get('detail')[:80]}" +
                       (" [older than %d days, half weight]" % days if age > days else ""))
    intent = min(cap, round(intent))
    score = fit + intent
    tier = "A" if score >= tiers["A"] else "B" if score >= tiers["B"] else "C"
    reasons.insert(0, f"fit {fit}/60, intent {intent}/{cap}")
    return score, tier, reasons, unknown


def cmd_score(a):
    st, s = store(), settings()
    ids = [a.id.upper()] if a.id else [lid for lid, ld in st["leads"].items()
                                       if a.all or ld.get("score") is None]
    res, missing_icp = [], False
    for lid in ids:
        lead = get_lead(st, lid)
        score, tier, reasons, unknown = score_lead(lead, s)
        if score is None:
            missing_icp = True
            break
        lead.update({"score": score, "tier": tier, "score_reasons": reasons, "scored": today().isoformat()})
        res.append({"id": lid, "company": lead["company"], "score": score, "tier": tier, "reasons": reasons,
                    "not_known": unknown})
    if missing_icp:
        fail("ideal customer not set", "run the ideal-customer skill: icp set --industries ... first")
    save_store(st)
    res.sort(key=lambda x: (-x["score"], x["id"]))
    tiers = {}
    for r in res:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    out({"ok": True, "scored": len(res), "tiers": tiers, "leads": res[:100] if not a.id else res})


# ---------- dedupe ----------

def cmd_dedupe(a):
    st = store()
    by_key, by_name = {}, {}
    for lid, lead in st["leads"].items():
        strong, weak = keys_of(lead)
        for k in strong:
            by_key.setdefault(k, []).append(lid)
        if weak:
            by_name.setdefault(weak, []).append(lid)
    parent = {lid: lid for lid in st["leads"]}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for ids in by_key.values():
        for other in ids[1:]:
            ra, rb = find(ids[0]), find(other)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    groups = {}
    for lid in st["leads"]:
        groups.setdefault(find(lid), []).append(lid)
    sure = [sorted(g) for g in groups.values() if len(g) > 1]
    sure_sets = [set(g) for g in sure]
    possible = [sorted(ids) for ids in by_name.values()
                if len(ids) > 1 and not any(set(ids) <= g for g in sure_sets)]
    merged = []
    if a.apply:
        for g in sure:
            keep = g[0]
            for other in g[1:]:
                merge_into(st["leads"][keep], st["leads"][other])
                st["leads"][keep].setdefault("merged_from", []).append(other)
                del st["leads"][other]
            merged.append({"kept": keep, "removed": g[1:]})
            log_event("dedupe", lead=keep, removed=g[1:])
        save_store(st)
    out({"ok": True, "sure_groups": sure, "possible_same_name": possible, "merged": merged,
         "hint": None if a.apply or not sure else "show the groups; on the owner's yes run dedupe --apply"})


# ---------- network ----------

def http(method, url, headers=None, body=None, form=None, timeout=25):
    """Returns (ok, data_or_error). Never raises and never prints secrets."""
    data = None
    h = {"User-Agent": UA, "Accept": "application/json", **(headers or {})}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    host = urllib.parse.urlsplit(url).netloc
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return True, json.loads(raw) if raw.strip() else {}
            except ValueError:
                return False, f"{host} returned a page, not data (it may ask for a captcha or block automated reading)"
    except urllib.error.HTTPError as e:
        hint = {401: "key invalid or expired", 403: "access refused (key rights, region block or the service closed "
                "anonymous access)", 404: "not found at this address", 429: "rate limit, try later"}.get(e.code, "")
        return False, scrub(f"HTTP {e.code} from {host}. {hint}".strip())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return False, scrub(f"cannot reach {host}: {getattr(e, 'reason', e)}")


def not_checked(source, reason, **extra):
    out({"ok": True, "status": "not checked", "source": source, "reason": scrub(reason),
         "note": "say «не проверено» with the reason; never report it as zero or as «не найдено»", **extra})


def need_key(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        out({"ok": False, "status": "needs key", "missing": missing,
             "hint": "this source needs the client's own key: add it in Settings → Secrets (never in the chat); "
                     "free sources work without it"}, 1)
    return [os.environ[n] for n in names]


def cmd_egrul(a):
    src = "https://egrul.nalog.ru/"
    ok, r = http("POST", src, form={"query": a.query, "region": "", "PreventChromeAutocomplete": ""})
    if not ok:
        not_checked(src, r)
    if not isinstance(r, dict) or r.get("captchaRequired") or not r.get("t"):
        not_checked(src, "the register asked for a captcha or returned no search token; never solve or bypass it",
                    manual=f"{src} (the owner can check by hand)")
    ok, res = http("GET", f"{src}search-result/{r['t']}")
    if not ok:
        not_checked(src, res)
    rows = []
    for x in (res.get("rows") or [])[: a.limit]:
        rows.append({"name": x.get("n") or x.get("c"), "short_name": x.get("c"), "inn": x.get("i"), "ogrn": x.get("o"),
                     "kpp": x.get("p"), "address": x.get("a"), "head": x.get("g"), "registered": x.get("r"),
                     "ceased": x.get("e") or None, "kind": {"ul": "company", "fl": "sole trader"}.get(x.get("k"), x.get("k"))})
    out({"ok": True, "status": "checked", "source": src, "checked_on": today().isoformat(), "query": a.query,
         "found": len(rows), "rows": rows,
         "note": "ceased companies are not leads; the head's name is public register data, not a contact"})


def cmd_hh(a):
    src = "https://api.hh.ru/vacancies"
    h = {"HH-User-Agent": UA}
    if os.environ.get("HH_APP_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["HH_APP_TOKEN"]
    employers = {}
    total = None
    for page in range(max(1, min(a.pages, 5))):
        q = {"text": a.query, "per_page": 50, "page": page, "order_by": "publication_time"}
        if a.area:
            q["area"] = a.area
        ok, r = http("GET", src + "?" + urllib.parse.urlencode(q), headers=h)
        if not ok:
            if page == 0:
                not_checked(src, r, hint="hh.ru may close anonymous access; a free application token from dev.hh.ru "
                                         "goes into Settings → Secrets as HH_APP_TOKEN")
            break
        total = r.get("found")
        for v in r.get("items") or []:
            e = v.get("employer") or {}
            key = e.get("id") or e.get("name")
            if not key:
                continue
            rec = employers.setdefault(key, {"employer": e.get("name"), "employer_url": e.get("alternate_url"),
                                             "vacancies": 0, "titles": [], "latest": "", "areas": set()})
            rec["vacancies"] += 1
            if len(rec["titles"]) < 5 and v.get("name") not in rec["titles"]:
                rec["titles"].append(v.get("name"))
            rec["latest"] = max(rec["latest"], (v.get("published_at") or "")[:10])
            rec["areas"].add((v.get("area") or {}).get("name") or "")
            rec.setdefault("example_url", v.get("alternate_url"))
        if len(r.get("items") or []) < 50:
            break
    rows = sorted(({**x, "areas": sorted(a_ for a_ in x["areas"] if a_)} for x in employers.values()),
                  key=lambda x: (-x["vacancies"], x["employer"] or ""))
    out({"ok": True, "status": "checked", "source": src, "checked_on": today().isoformat(), "query": a.query,
         "vacancies_found": total, "employers": rows[: a.limit],
         "signal": "hiring for this role = the company spends on this problem now; add as signal type hiring with "
                   "example_url as the source"})


def cmd_dadata(a):
    (key,) = need_key("DADATA_API_KEY")
    src = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/"
    method = "findById/party" if re.fullmatch(r"\d{10}|\d{12}|\d{13}|\d{15}", a.query) else "suggest/party"
    ok, r = http("POST", src + method, headers={"Authorization": "Token " + key}, body={"query": a.query, "count": 5})
    if not ok:
        not_checked("DaData", r)
    rows = []
    for s in r.get("suggestions") or []:
        d = s.get("data") or {}
        rows.append({"name": s.get("value"), "inn": d.get("inn"), "ogrn": d.get("ogrn"),
                     "address": (d.get("address") or {}).get("value"), "okved": d.get("okved"),
                     "status": (d.get("state") or {}).get("status"), "employees": d.get("employee_count"),
                     "head_title": (d.get("management") or {}).get("post")})
    out({"ok": True, "status": "checked", "source": "DaData (" + method + ")", "checked_on": today().isoformat(),
         "rows": rows})


def cmd_hunter(a):
    (key,) = need_key("HUNTER_API_KEY")
    base = "https://api.hunter.io/v2/"
    if a.action == "domain":
        ok, r = http("GET", base + "domain-search?" + urllib.parse.urlencode({"domain": norm_domain(a.args[0]), "limit": 10,
                                                                               "api_key": key}))
        if not ok:
            not_checked("Hunter", r)
        d = r.get("data") or {}
        people = [{"name": " ".join(x for x in (e.get("first_name"), e.get("last_name")) if x), "title": e.get("position"),
                   "email": e.get("value"), "email_status": "verified" if (e.get("verification") or {}).get("status") == "valid"
                   else "unverified", "type": e.get("type"), "confidence": e.get("confidence"),
                   "seen_on": [s.get("uri") for s in (e.get("sources") or [])[:2]], "linkedin": e.get("linkedin")}
                  for e in d.get("emails") or []]
        out({"ok": True, "status": "checked", "source": "Hunter domain search", "checked_on": today().isoformat(),
             "domain": d.get("domain"), "pattern": d.get("pattern"), "people": people,
             "note": "use seen_on as the contact's source; 'generic' addresses are company inboxes"})
    if a.action == "verify":
        email = norm_email(a.args[0])
        if not email:
            fail("not an email address")
        ok, r = http("GET", base + "email-verifier?" + urllib.parse.urlencode({"email": email, "api_key": key}))
        if not ok:
            not_checked("Hunter verifier", r)
        d = r.get("data") or {}
        status = {"valid": "verified", "invalid": "invalid"}.get(d.get("status"), "unverified")
        updated = update_email_status(email, status, f"Hunter verifier: {d.get('status')}") if a.update else []
        out({"ok": True, "status": "checked", "source": "Hunter verifier", "email": email, "result": d.get("status"),
             "store_status": status, "accept_all": d.get("accept_all"), "updated_contacts": updated})
    if a.action == "find":
        if len(a.args) < 3:
            fail("hunter find DOMAIN FIRST LAST")
        ok, r = http("GET", base + "email-finder?" + urllib.parse.urlencode(
            {"domain": norm_domain(a.args[0]), "first_name": a.args[1], "last_name": a.args[2], "api_key": key}))
        if not ok:
            not_checked("Hunter finder", r)
        d = r.get("data") or {}
        st = "verified" if (d.get("verification") or {}).get("status") == "valid" else "pattern"
        out({"ok": True, "status": "checked", "source": "Hunter finder", "email": d.get("email"), "email_status": st,
             "score": d.get("score"), "seen_on": [s.get("uri") for s in (d.get("sources") or [])[:3]],
             "note": "without verification this is a pattern guess: label it «шаблон, не проверен»"})
    fail("hunter domain D | hunter verify EMAIL | hunter find D FIRST LAST")


def cmd_apollo(a):
    (key,) = need_key("APOLLO_API_KEY")
    body = {"q_organization_domains_list": [norm_domain(a.domain)], "per_page": min(a.limit, 25), "page": 1}
    if a.titles:
        body["person_titles"] = csv_list(a.titles)
    ok, r = http("POST", "https://api.apollo.io/api/v1/mixed_people/api_search", headers={"X-Api-Key": key,
                                                                                          "Cache-Control": "no-cache"},
                 body=body)
    if not ok:
        not_checked("Apollo people search", r)
    people = [{"name": p.get("name") or " ".join(x for x in (p.get("first_name"), p.get("last_name_obfuscated")) if x),
               "title": p.get("title"), "linkedin": p.get("linkedin_url"),
               "company": (p.get("organization") or {}).get("name"), "has_email": p.get("has_email")}
              for p in r.get("people") or []]
    out({"ok": True, "status": "checked", "source": "Apollo people search", "checked_on": today().isoformat(),
         "people": people, "note": "Apollo search gives roles, not verified emails; the source of each person is "
                                   "'Apollo API, <date>'"})


def mx_lookup(domain):
    for url in (f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX",
                f"https://dns.google/resolve?name={domain}&type=MX"):
        ok, r = http("GET", url, headers={"Accept": "application/dns-json"}, timeout=10)
        if ok and isinstance(r, dict) and "Status" in r:
            recs = [x.get("data") for x in r.get("Answer") or [] if x.get("type") == 15]
            return {"status": "checked", "has_mx": bool(recs), "records": recs, "resolver": urllib.parse.urlsplit(url).netloc,
                    "nxdomain": r.get("Status") == 3}
        err = r
    return {"status": "not checked", "reason": err}


def update_email_status(email, status, why):
    st = store()
    updated = []
    for lead in st["leads"].values():
        for c in lead.get("contacts") or []:
            if c.get("email") == email:
                old = c.get("email_status")
                if status == "verified" or old != "verified":
                    c["email_status"] = status
                c.setdefault("checks", []).append({"date": today().isoformat(), "result": why})
                updated.append({"lead": lead["id"], "from": old, "to": c["email_status"]})
    save_store(st)
    return updated


def cmd_mx(a):
    domain = norm_domain(a.target)
    if not domain:
        fail("not a domain or an email")
    r = mx_lookup(domain)
    if r["status"] != "checked":
        not_checked("DNS-over-HTTPS", r["reason"], domain=domain)
    updated = []
    if a.update:
        st = store()
        for lead in st["leads"].values():
            for c in lead.get("contacts") or []:
                if c.get("email", "").endswith("@" + domain):
                    c["mx"] = "ok" if r["has_mx"] else "none"
                    if not r["has_mx"]:
                        c["email_status"] = "invalid"
                    updated.append(lead["id"])
        save_store(st)
    out({"ok": True, "domain": domain, **r, "updated_leads": sorted(set(updated)),
         "meaning": "has_mx = the domain accepts mail; it does NOT prove that a mailbox exists. A pattern address "
                    "stays «шаблон, не проверен» until a verifier says valid"})


def translit(s):
    table = dict(zip("абвгдеёзийклмнопрстуфхыэ", "abvgdeezijklmnoprstufhye"))
    table.update({"ж": "zh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ю": "yu", "я": "ya", "ь": "", "ъ": ""})
    return "".join(table.get(ch, ch) for ch in s.lower())


def cmd_pattern(a):
    domain = company_domain(a.domain)
    if not domain:
        fail("a company domain is needed (not a free mail domain)")
    f, l_ = re.sub(r"[^a-z]", "", translit(a.first)), re.sub(r"[^a-z]", "", translit(a.last))
    if not f or not l_:
        fail("first and last name are needed")
    forms = {"first.last": f"{f}.{l_}", "first": f, "flast": f"{f[0]}{l_}", "firstlast": f"{f}{l_}",
             "first_last": f"{f}_{l_}", "last": l_, "f.last": f"{f[0]}.{l_}", "last.first": f"{l_}.{f}"}
    if a.pattern:
        key = a.pattern.replace("{first}", "first").replace("{last}", "last").replace("{f}", "f")
        forms = {key: forms.get(key, "")} if key in forms else forms
    cands = [{"email": f"{v}@{domain}", "form": k, "email_status": "pattern"} for k, v in forms.items() if v]
    out({"ok": True, "domain": domain, "candidates": cands,
         "label": "шаблон, не проверен / pattern, not verified",
         "rule": "never send to a pattern address; verify it (hunter verify, with the client's key) or ask the owner"})


# ---------- sequences and replies ----------

def seqs():
    return load("sequences/sequences.json", {})


def plan_steps(start, steps_days, n):
    steps = [{"n": 1, "kind": "first", "due": start.isoformat(), "status": "planned"}]
    for i in range(1, n):
        off = steps_days[i - 1] if i - 1 < len(steps_days) else steps_days[-1] + 7 * (i - len(steps_days))
        steps.append({"n": i + 1, "kind": "follow_up", "due": (start + timedelta(days=off)).isoformat(),
                      "status": "planned", "offset_days": off})
    return steps


def cmd_seq(a):
    s, S = settings(), seqs()
    cfg = {"steps_days": [3, 7, 14], "max_steps": 4, **s["sequence"]}
    if a.action == "list":
        out({"ok": True, "sequences": [{"lead": k, "status": v["status"], "channel": v["channel"],
                                        "next": next((x for x in v["steps"] if x["status"] == "planned"), None)}
                                       for k, v in sorted(S.items())]})
    if a.action == "due":
        d = parse_date(a.date, today()) + timedelta(days=a.days or 0)
        st, due, revisit = store(), [], []
        for lid, q in S.items():
            if q["status"] != "active":
                continue
            prev_done = True
            for step in q["steps"]:
                if step["status"] == "planned":
                    if prev_done and parse_date(step["due"]) <= d:
                        lead = st["leads"].get(lid, {})
                        due.append({"lead": lid, "company": lead.get("company"), "step": step["n"], "kind": step["kind"],
                                    "due": step["due"], "overdue_days": max(0, (today() - parse_date(step["due"])).days),
                                    "channel": q["channel"], "to": q.get("to")})
                    break
                prev_done = step["status"] in ("sent", "skipped")
        for lid, lead in st["leads"].items():
            rv = lead.get("revisit")
            if lead.get("stage") == "not_now" and rv and parse_date(rv) <= d:
                revisit.append({"lead": lid, "company": lead["company"], "revisit": rv})
        due.sort(key=lambda x: (x["due"], x["lead"]))
        out({"ok": True, "date": d.isoformat(), "due": due, "count": len(due), "revisit_not_now": revisit})
    st = store()
    lead = get_lead(st, a.id)
    lid = lead["id"]
    if a.action == "plan":
        if lead.get("stage") in CLOSED or lead.get("stage") == "not_now":
            fail(f"lead {lid} is {lead['stage']}: no sequence")
        if dnc_match(load_dnc(), lead_values(lead)):
            fail(f"lead {lid} is on the do-not-contact list")
        if S.get(lid, {}).get("status") == "active" and not a.force:
            fail(f"lead {lid} already has an active sequence", "seq list; pass --force to replan")
        n = max(2, min(a.steps or len(cfg["steps_days"]) + 1, cfg["max_steps"]))
        start = parse_date(a.start, today())
        S[lid] = {"channel": a.channel, "to": a.to or "", "started": start.isoformat(), "status": "active",
                  "steps": plan_steps(start, cfg["steps_days"], n)}
        save("sequences/sequences.json", S)
        log_event("seq_plan", lead=lid, steps=n)
        out({"ok": True, "lead": lid, "sequence": S[lid]})
    q = S.get(lid)
    if not q:
        fail(f"lead {lid} has no sequence", "seq plan first")
    if a.action == "stop":
        q.update({"status": "stopped", "stop_reason": a.reason or "manual", "stopped": today().isoformat()})
        save("sequences/sequences.json", S)
        log_event("seq_stop", lead=lid, reason=a.reason)
        out({"ok": True, "lead": lid, "status": "stopped"})
    if a.action == "mark":
        if q["status"] != "active":
            fail(f"the sequence of {lid} is {q['status']} ({q.get('stop_reason')}): nothing more goes out")
        step = next((x for x in q["steps"] if x["n"] == a.step), None)
        if not step:
            fail(f"no step {a.step}")
        when = parse_date(a.date, today())
        step.update({"status": a.result, "done": when.isoformat()})
        if a.step == 1 and a.result == "sent":
            for x in q["steps"][1:]:
                if x["status"] == "planned":
                    x["due"] = (when + timedelta(days=x.get("offset_days", 0))).isoformat()
            if lead.get("stage") in ("new", "qualified"):
                set_stage(lead, "contacted")
                save_store(st)
        if all(x["status"] in ("sent", "skipped") for x in q["steps"]):
            q.update({"status": "done", "stop_reason": "all steps done", "stopped": when.isoformat()})
        save("sequences/sequences.json", S)
        out({"ok": True, "lead": lid, "status": q["status"],
             "next": next((x for x in q["steps"] if x["status"] == "planned"), None)})
    fail("seq plan|due|mark|stop|list")


REPLY_EFFECT = {"interested": ("replied", True, False), "question": ("replied", True, False),
                "meeting": ("meeting", True, False), "not_now": ("not_now", True, False), "no": ("lost", True, True),
                "opt_out": ("dnc", True, True), "wrong_person": (None, True, False), "bounce": (None, True, False),
                "out_of_office": (None, False, False)}


def cmd_reply(a):
    if a.cls not in REPLY_EFFECT:
        fail(f"class must be one of {sorted(REPLY_EFFECT)}")
    st, S, s = store(), seqs(), settings()
    lead = get_lead(st, a.id)
    lid = lead["id"]
    stage, stop, dnc = REPLY_EFFECT[a.cls]
    res = {"ok": True, "lead": lid, "class": a.cls}
    q = S.get(lid)
    if a.cls == "out_of_office" and q and q["status"] == "active":
        for x in q["steps"]:
            if x["status"] == "planned":
                x["due"] = (parse_date(x["due"]) + timedelta(days=a.days)).isoformat()
        res["sequence"] = f"paused: planned steps moved {a.days} days later"
    elif stop and q and q["status"] == "active":
        q.update({"status": "stopped", "stop_reason": "reply:" + a.cls, "stopped": today().isoformat()})
        res["sequence"] = "stopped"
    if stage:
        set_stage(lead, stage, a.note)
    if a.cls == "not_now":
        lead["revisit"] = (today() + timedelta(days=s.get("not_now_days", 90))).isoformat()
        res["revisit"] = lead["revisit"]
    if a.cls == "bounce":
        to = (q or {}).get("to")
        for c in lead.get("contacts") or []:
            if not to or c.get("email") == to:
                c["email_status"] = "invalid"
        res["email"] = "marked invalid"
    if a.cls == "wrong_person":
        lead.setdefault("notes", []).append({"date": today().isoformat(), "text": "wrong person: find the right one " +
                                             (a.note or "")})
    if dnc:
        res["dnc_added"] = dnc_add_values(lead_values(lead) or [("name", lead["name_norm"])],
                                          "replied no" if a.cls == "no" else "opted out", lid)
    save_store(st)
    save("sequences/sequences.json", S)
    log_event("reply", lead=lid, cls=a.cls, channel=(q or {}).get("channel"))
    res["stage"] = lead["stage"]
    out(res)


# ---------- outbox ----------

PLACEHOLDER = re.compile(r"\[[^\]\n]{2,}\]|\{\{[^}]+\}\}|<[A-ZА-Я_ ]{3,}>")
OPT_OUT_MARKERS = ["отпис", "не пиши", "не писать", "больше не", "ответьте «нет»", "ответьте \"нет\"", "напишите «нет»",
                   "unsubscribe", "opt out", "opt-out", "reply \"no\"", "reply 'no'", "reply no", "won't write again",
                   "will not write again", "stop hearing", "let me know if you'd rather not"]


def load_batch(bid):
    b = load(f"outbox/{bid.upper()}.json", None)
    if not b:
        fail(f"no batch {bid}", "outbox list")
    return b


def has_opt_out(body, s):
    low = body.lower()
    lines = [s["sender"].get("opt_out_line_ru"), s["sender"].get("opt_out_line_en")] + (s["sender"].get("opt_out_markers") or [])
    return any(x and x.lower() in low for x in lines) or any(m in low for m in OPT_OUT_MARKERS)


def check_message(m, st, s, dnc, seen_to):
    blocked, warn = [], []
    lead = st["leads"].get((m.get("lead") or "").upper())
    if not lead:
        return ["unknown lead"], warn, None
    if lead.get("stage") in CLOSED:
        blocked.append(f"lead is {lead['stage']}")
    to = (m.get("to") or "").strip()
    ch = m["channel"]
    if not to:
        blocked.append("no recipient")
    if ch == "email":
        e = norm_email(to)
        if not e:
            blocked.append("recipient is not an email address")
        else:
            c = next((c for c in lead.get("contacts") or [] if c.get("email") == e), None)
            status = c.get("email_status") if c else ("public" if e == lead.get("email") else None)
            if status is None:
                blocked.append("address is not in the lead's contacts: add it with its source first")
            elif status == "pattern":
                blocked.append("pattern address, not verified: verify it first")
            elif status == "invalid":
                blocked.append("address is invalid (bounced or failed verification)")
            elif status == "unverified":
                warn.append("address not verified: tell the owner before approving")
            if c and c.get("mx") == "none":
                blocked.append("the domain does not accept mail")
        if (m.get("step") or 1) == 1 and not (m.get("subject") or "").strip():
            warn.append("no subject")
    hit = dnc_match(dnc, lead_values(lead) + [dnc_kind(to)] if to else lead_values(lead))
    if hit:
        blocked.append("do-not-contact: " + ", ".join(hit))
    body = m.get("body") or ""
    if len(body.strip()) < 20:
        blocked.append("empty or too short")
    if ch in ("email", "telegram", "linkedin") and not has_opt_out(body, s):
        blocked.append("no opt-out line (every cold message offers to stop)")
    ph = PLACEHOLDER.findall(body + " " + (m.get("subject") or ""))
    if ph:
        blocked.append("unfilled placeholders: " + ", ".join(ph[:3]))
    if to and to.lower() in seen_to:
        blocked.append("same recipient twice in this batch")
    seen_to.add(to.lower())
    if ch == "email" and len(body.split()) > 180:
        warn.append("long: a first message reads best under ~120 words")
    return blocked, warn, lead


def sent_today(channel):
    d = today().isoformat()
    return sum(1 for e in events() if e.get("type") == "sent" and e.get("date") == d and e.get("channel") == channel)


def cmd_outbox(a):
    s = settings()
    limits = {"email": 30, "telegram": 20, "linkedin": 15, "call": 40, "batch_max": 25, **s["limits"]}
    if a.action == "new":
        try:
            items = json.loads(Path(a.file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            fail(f"cannot read drafts: {e}")
        if not isinstance(items, list) or not items:
            fail("the file must hold a JSON list of messages")
        if len(items) > limits["batch_max"]:
            fail(f"{len(items)} messages: more than batch_max {limits['batch_max']}", "split into smaller batches")
        st, dnc, seen_to = store(), load_dnc(), set()
        existing = sorted((data_dir() / "outbox").glob("B*.json"))
        bid = f"B{(int(existing[-1].stem[1:]) + 1) if existing else 1:04d}"
        msgs = []
        for i, m in enumerate(items, 1):
            m = {**m, "channel": m.get("channel") or a.channel}
            if m["channel"] not in CHANNELS:
                fail(f"channel must be one of {CHANNELS}")
            blocked, warn, lead = check_message(m, st, s, dnc, seen_to)
            msgs.append({"id": f"{bid}-{i:02d}", "lead": (m.get("lead") or "").upper(),
                         "company": lead["company"] if lead else None, "channel": m["channel"], "to": m.get("to", ""),
                         "step": m.get("step") or 1, "subject": m.get("subject", ""), "body": m.get("body", ""),
                         "facts": m.get("facts") or [], "blocked": blocked, "warnings": warn,
                         "status": "blocked" if blocked else "draft"})
        b = {"id": bid, "created": now_iso(), "status": "awaiting_approval", "messages": msgs}
        save(f"outbox/{bid}.json", b)
        log_event("outbox_new", batch=bid, messages=len(msgs))
        out({"ok": True, "batch": bid, "messages": len(msgs), "ready": sum(1 for m in msgs if not m["blocked"]),
             "blocked": [{"id": m["id"], "company": m["company"], "why": m["blocked"]} for m in msgs if m["blocked"]],
             "warnings": [{"id": m["id"], "why": m["warnings"]} for m in msgs if m["warnings"]],
             "next": "show the ready messages to the owner; send nothing until they say yes to this batch"})
    if a.action == "list":
        rows = []
        for f in sorted((data_dir() / "outbox").glob("B*.json")):
            b = json.loads(f.read_text(encoding="utf-8"))
            cnt = {}
            for m in b["messages"]:
                cnt[m["status"]] = cnt.get(m["status"], 0) + 1
            rows.append({"batch": b["id"], "status": b["status"], "created": b["created"][:10], "messages": cnt})
        out({"ok": True, "batches": rows})
    b = load_batch(a.batch)
    if a.action == "show":
        res = {"ok": True, **{k: b[k] for k in ("id", "status", "created")}, "approval": b.get("approval"),
               "messages": b["messages"]}
        if a.md:
            lines = [f"# Outreach batch {b['id']}", "", f"Status: {b['status']}. Created: {b['created'][:10]}.", ""]
            for m in b["messages"]:
                lines += [f"## {m['id']} · {m['company']} · {m['channel']} · step {m['step']}", "",
                          f"**To:** {m['to']}", ""]
                if m.get("subject"):
                    lines += [f"**Subject:** {m['subject']}", ""]
                lines += [m["body"], ""]
                if m.get("facts"):
                    lines += ["**Facts used:** " + "; ".join(str(x) for x in m["facts"]), ""]
                if m["blocked"]:
                    lines += ["**Blocked:** " + "; ".join(m["blocked"]), ""]
                if m["warnings"]:
                    lines += ["**Check:** " + "; ".join(m["warnings"]), ""]
            p = data_dir() / "outbox" / f"{b['id']}.md"
            p.write_text("\n".join(lines), encoding="utf-8")
            res = {"ok": True, "batch": b["id"], "md": str(p.relative_to(ROOT)) if ROOT in p.parents else str(p)}
        out(res)
    if a.action == "cancel":
        b["status"] = "cancelled"
        for m in b["messages"]:
            if m["status"] in ("draft", "approved"):
                m["status"] = "cancelled"
        save(f"outbox/{b['id']}.json", b)
        out({"ok": True, "batch": b["id"], "status": "cancelled"})
    if a.action == "approve":
        if not a.by:
            fail("--by is required: who said yes")
        if b["status"] not in ("awaiting_approval",):
            fail(f"batch is {b['status']}")
        st, dnc, seen_to = store(), load_dnc(), set()
        approved, newly_blocked = [], []
        for m in b["messages"]:
            if m["status"] != "draft":
                continue
            blocked, warn, _ = check_message(m, st, s, dnc, seen_to)  # re-check: replies and DNC may have changed
            if blocked:
                m.update({"status": "blocked", "blocked": blocked})
                newly_blocked.append({"id": m["id"], "why": blocked})
                continue
            m["status"] = "approved"
            approved.append(m)
        plan = {}
        for m in approved:
            ch = m["channel"]
            room = limits.get(ch, 30) - sent_today(ch) - len([x for x in plan.get(ch, [])])
            plan.setdefault(ch, [])
            if room > 0:
                plan[ch].append(m["id"])
        later = [m["id"] for m in approved if m["id"] not in sum(plan.values(), [])]
        b["status"] = "approved"
        b["approval"] = {"by": a.by, "at": now_iso(), "note": a.note or "", "approved": [m["id"] for m in approved],
                         "today": sum(plan.values(), []), "later": later}
        save(f"outbox/{b['id']}.json", b)
        log_event("approve", batch=b["id"], by=a.by, approved=len(approved))
        out({"ok": True, "batch": b["id"], "approved": len(approved), "send_today": b["approval"]["today"],
             "later_days": later, "blocked_on_recheck": newly_blocked,
             "limits": {ch: {"limit": limits.get(ch), "sent_today": sent_today(ch)} for ch in plan},
             "next": "send only send_today through the connected tool, then outbox mark <batch> <id> sent"})
    if a.action == "mark":
        if b["status"] not in ("approved", "partly_sent"):
            fail(f"batch {b['id']} is {b['status']}: nothing in it may be sent", "the owner's yes is recorded with outbox approve")
        ids = b.get("approval", {}).get("today", []) if a.msg == "today" else [a.msg.upper()]
        st, S, done = store(), seqs(), []
        for mid in ids:
            m = next((x for x in b["messages"] if x["id"] == mid), None)
            if not m:
                fail(f"no message {mid}")
            if a.result == "sent":
                if m["status"] != "approved":
                    fail(f"{mid} is {m['status']}: only approved messages can be sent")
                if sent_today(m["channel"]) >= limits.get(m["channel"], 30):
                    fail(f"daily {m['channel']} limit reached ({limits.get(m['channel'])})", "the rest goes on the next day")
                lead = st["leads"].get(m["lead"])
                q = S.get(m["lead"])
                stop = []
                if lead and (lead.get("stage") in CLOSED or lead.get("stage") == "not_now"):
                    stop.append(f"lead is now {lead['stage']}")
                if dnc_match(load_dnc(), lead_values(lead or {}) + [dnc_kind(m["to"])]):
                    stop.append("now on the do-not-contact list")
                if q and q["status"] == "stopped" and m["step"] > 1:
                    stop.append(f"sequence stopped ({q.get('stop_reason')})")
                if stop:
                    m.update({"status": "skipped", "error": "; ".join(stop)})
                    log_event("send_skipped", batch=b["id"], msg=mid, lead=m["lead"], error=m["error"])
                    done.append(mid + " skipped: " + m["error"])
                    continue
                m.update({"status": "sent", "sent_at": now_iso()})
                log_event("sent", batch=b["id"], msg=mid, lead=m["lead"], channel=m["channel"], step=m["step"])
                if not q or q["status"] != "active":
                    cfg = {"steps_days": [3, 7, 14], "max_steps": 4, **s["sequence"]}
                    q = S[m["lead"]] = {"channel": m["channel"], "to": m["to"], "started": today().isoformat(),
                                        "status": "active", "steps": plan_steps(today(), cfg["steps_days"],
                                                                                min(cfg["max_steps"], len(cfg["steps_days"]) + 1))}
                step = next((x for x in q["steps"] if x["n"] == m["step"]), None)
                if step:
                    step.update({"status": "sent", "done": today().isoformat()})
                    if all(x["status"] in ("sent", "skipped") for x in q["steps"]):
                        q.update({"status": "done", "stop_reason": "all steps done"})
                if lead and lead.get("stage") in ("new", "qualified"):
                    set_stage(lead, "contacted")
            else:
                m.update({"status": a.result, "error": a.error or ""})
                log_event("send_" + a.result, batch=b["id"], msg=mid, lead=m["lead"], error=a.error)
            done.append(mid)
        left = [m for m in b["messages"] if m["status"] == "approved"]
        b["status"] = "partly_sent" if left else "sent"
        save(f"outbox/{b['id']}.json", b)
        save_store(st)
        save("sequences/sequences.json", S)
        out({"ok": True, "batch": b["id"], "marked": done, "result": a.result, "approved_left": len(left)})
    fail("outbox new|list|show|approve|mark|cancel")


# ---------- export and CRM ----------

def pick(st, a):
    leads = [ld for ld in st["leads"].values() if ld.get("stage") != "dnc"]
    if getattr(a, "ids", None):
        want = {x.upper() for x in csv_list(a.ids)}
        leads = [ld for ld in leads if ld["id"] in want]
    if getattr(a, "stage", None):
        leads = [ld for ld in leads if ld.get("stage") == a.stage]
    if getattr(a, "min_score", None) is not None:
        leads = [ld for ld in leads if (ld.get("score") or 0) >= a.min_score]
    dnc = load_dnc()
    return [ld for ld in leads if not dnc_match(dnc, lead_values(ld))]


def best_contact(lead):
    cs = lead.get("contacts") or []
    return next((c for c in cs if c.get("email_status") in SENDABLE), None) or (cs[0] if cs else {})


def row_for(lead, fmt):
    c = best_contact(lead)
    email = c.get("email") if c.get("email_status") in SENDABLE else ""
    note_email = f"{c['email']} ({c['email_status']}, not verified)" if c.get("email") and not email else ""
    first, _, last = (c.get("name") or "").partition(" ")
    why = lead.get("reason") or ""
    note = "; ".join(x for x in [why, f"score {lead.get('score')} {lead.get('tier') or ''}".strip()
                                 if lead.get("score") is not None else "", note_email,
                                 "source: " + lead["sources"][0]["url"] + " (" + lead["sources"][0]["seen"] + ")"] if x)
    phone = lead.get("phone") or c.get("phone") or ""
    if fmt == "amocrm":
        return {"Название сделки": f"{lead['company']} — Kevin", "Компания": lead["company"], "Контакт": c.get("name", ""),
                "Должность": c.get("title", ""), "Рабочий email": email or lead.get("email", ""), "Рабочий телефон": phone,
                "Web": lead.get("website", ""), "ИНН": lead.get("inn", ""), "Город": lead.get("city", ""),
                "Теги": "kevin;" + (lead.get("batch") or ""), "Примечание": note}
    if fmt == "bitrix":
        return {"Название лида": f"{lead['company']} — Kevin", "Название компании": lead["company"], "Имя": first,
                "Фамилия": last, "Должность": c.get("title", ""), "Рабочий телефон": phone,
                "Рабочий e-mail": email or lead.get("email", ""), "Корпоративный сайт": lead.get("website", ""),
                "Адрес": lead.get("address", "") or lead.get("city", ""), "Источник": "Kevin", "Комментарий": note}
    if fmt == "hubspot":
        return {"Company name": lead["company"], "Company Domain Name": lead.get("domain", ""), "First Name": first,
                "Last Name": last, "Job Title": c.get("title", ""), "Email": email, "Phone Number": phone,
                "City": lead.get("city", ""), "Country/Region": lead.get("country", ""), "Lifecycle Stage": "lead",
                "Lead Status": {"new": "NEW", "qualified": "OPEN", "contacted": "ATTEMPTED_TO_CONTACT",
                                "replied": "CONNECTED", "meeting": "IN_PROGRESS"}.get(lead.get("stage"), "OPEN"),
                "Notes": note}
    return {"id": lead["id"], "company": lead["company"], "website": lead.get("website", ""), "inn": lead.get("inn", ""),
            "city": lead.get("city", ""), "country": lead.get("country", ""), "industry": lead.get("industry", ""),
            "size": lead.get("size", ""), "company_phone": lead.get("phone", ""), "company_email": lead.get("email", ""),
            "contact": c.get("name", ""), "title": c.get("title", ""), "contact_email": c.get("email", ""),
            "email_status": c.get("email_status", ""), "linkedin": c.get("linkedin", ""), "stage": lead.get("stage"),
            "score": lead.get("score") if lead.get("score") is not None else "", "tier": lead.get("tier") or "",
            "why_fits": why, "signals": "; ".join(f"{x['type']}: {x['detail']}" for x in lead.get("signals") or []),
            "source": lead["sources"][0]["url"], "seen": lead["sources"][0]["seen"]}


def cmd_export(a):
    st = store()
    leads = sorted(pick(st, a), key=lambda x: (-(x.get("score") or 0), x["id"]))
    if not leads:
        fail("no leads match", "lead list")
    fmt = a.format
    rows = [row_for(ld, "sheets" if fmt in ("csv", "xlsx", "sheets") else fmt) for ld in leads]
    folder = data_dir() / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{today().isoformat()}-{fmt}"
    note = None
    if fmt == "xlsx":
        try:
            import openpyxl  # optional, not in the standard library
            path = Path(a.out) if a.out else folder / f"{stem}.xlsx"
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Leads"
            ws.append(list(rows[0].keys()))
            for r in rows:
                ws.append([r[k] for k in rows[0]])
            wb.save(path)
        except ImportError:
            fmt, note = "csv", "openpyxl is not installed: saved as CSV, which Excel opens"
    if fmt != "xlsx":
        path = Path(a.out) if a.out else folder / f"{stem}.csv"
        delim = ";" if fmt in ("amocrm", "bitrix") else ","
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=delim)
            w.writeheader()
            w.writerows(rows)
    log_event("export", format=a.format, rows=len(rows))
    out({"ok": True, "file": str(path), "rows": len(rows), "format": a.format, "note": note,
         "excluded": "do-not-contact leads; unverified addresses go to the notes column, not the email column",
         "next": {"sheets": "add the rows to the owner's Google Sheet through the connected app, after their yes",
                  "hubspot": "import the file in HubSpot, or create records through the connected app after a yes"}
         .get(a.format)})


def amo_base():
    domain, token = need_key("AMO_DOMAIN", "AMO_TOKEN")
    return f"https://{domain.replace('https://', '').rstrip('/')}", {"Authorization": f"Bearer {token}"}


def bitrix_hook():
    (hook,) = need_key("BITRIX_WEBHOOK_URL")
    return hook.rstrip("/")


def crm_find(target, lead, c):
    """Returns (found_ids, error). Read-only duplicate search in the CRM."""
    if target == "amocrm":
        base, h = amo_base()
        q = lead.get("domain") or c.get("email") or lead["company"]
        ok, r = http("GET", f"{base}/api/v4/companies?" + urllib.parse.urlencode({"query": q, "limit": 5}), headers=h)
        if not ok:
            return None, r
        return [x["id"] for x in ((r or {}).get("_embedded") or {}).get("companies", [])], None
    hook = bitrix_hook()
    found = []
    for typ, val in (("EMAIL", c.get("email")), ("PHONE", lead.get("phone") or c.get("phone"))):
        if not val:
            continue
        ok, r = http("POST", f"{hook}/crm.duplicate.findbycomm.json", body={"type": typ, "values": [val]})
        if not ok:
            return None, r
        res = (r or {}).get("result") or {}
        if isinstance(res, dict):
            for ids in res.values():
                found += ids
    ok, r = http("POST", f"{hook}/crm.company.list.json", body={"filter": {"TITLE": lead["company"]}, "select": ["ID"]})
    if not ok:
        return None, r
    found += [x.get("ID") for x in (r or {}).get("result") or []]
    return sorted(set(str(x) for x in found)), None


def crm_create(target, lead, c, s):
    note = row_for(lead, "sheets")
    if target == "amocrm":
        base, h = amo_base()
        contact = {"name": c.get("name") or lead["company"], "custom_fields_values": []}
        if c.get("email") and c.get("email_status") in SENDABLE:
            contact["custom_fields_values"].append({"field_code": "EMAIL", "values": [{"value": c["email"], "enum_code": "WORK"}]})
        if lead.get("phone"):
            contact["custom_fields_values"].append({"field_code": "PHONE", "values": [{"value": lead["phone"], "enum_code": "WORK"}]})
        if not contact["custom_fields_values"]:
            del contact["custom_fields_values"]
        body = [{"name": f"{lead['company']} — Kevin", "_embedded": {"contacts": [contact], "companies": [{"name": lead["company"]}],
                                                                   "tags": [{"name": "kevin"}]}}]
        if s["crm"].get("amocrm_pipeline_id"):
            body[0]["pipeline_id"] = s["crm"]["amocrm_pipeline_id"]
        ok, r = http("POST", f"{base}/api/v4/leads/complex", headers=h, body=body)
        if not ok:
            return None, r
        lid = (r[0] if isinstance(r, list) and r else {}).get("id")
        ok, back = http("GET", f"{base}/api/v4/leads/{lid}", headers=h)
        if lid:
            http("POST", f"{base}/api/v4/leads/{lid}/notes", headers=h,
                 body=[{"note_type": "common", "params": {"text": f"Почему подходит: {note['why_fits']}. Источник: "
                                                                  f"{note['source']} ({note['seen']})"}}])
        return {"id": lid, "read_back": ok and (back or {}).get("id") == lid}, None
    hook = bitrix_hook()
    first, _, last = (c.get("name") or "").partition(" ")
    fields = {"TITLE": f"{lead['company']} — Kevin", "COMPANY_TITLE": lead["company"], "NAME": first, "LAST_NAME": last,
              "POST": c.get("title", ""), "WEB": [{"VALUE": lead.get("website", ""), "VALUE_TYPE": "WORK"}],
              "COMMENTS": f"Почему подходит: {note['why_fits']}. Источник: {note['source']} ({note['seen']})",
              "SOURCE_DESCRIPTION": "Kevin (ASCN)"}
    if c.get("email") and c.get("email_status") in SENDABLE:
        fields["EMAIL"] = [{"VALUE": c["email"], "VALUE_TYPE": "WORK"}]
    if lead.get("phone"):
        fields["PHONE"] = [{"VALUE": lead["phone"], "VALUE_TYPE": "WORK"}]
    ok, r = http("POST", f"{hook}/crm.lead.add.json", body={"fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}})
    if not ok:
        return None, r
    new_id = (r or {}).get("result")
    ok, back = http("POST", f"{hook}/crm.lead.get.json", body={"id": new_id})
    return {"id": new_id, "read_back": ok and str(((back or {}).get("result") or {}).get("ID")) == str(new_id)}, None


def cmd_crm(a):
    if a.action != "push":
        fail("crm push --to amocrm|bitrix")
    st, s = store(), settings()
    s.setdefault("crm", {})
    leads = [ld for ld in pick(st, a) if not (ld.get("crm") or {}).get(a.to)]
    if not leads:
        fail("no leads to push (already pushed, do-not-contact or no match)")
    if len(leads) > 50 and a.yes:
        fail("more than 50 leads in one push", "push in parts, the owner approves each")
    plan, errors = [], []
    for lead in leads:
        c = best_contact(lead)
        found, err = crm_find(a.to, lead, c)
        if err:
            errors.append({"lead": lead["id"], "error": err})
            continue
        plan.append({"lead": lead["id"], "company": lead["company"], "action": "skip: already in CRM" if found else "create",
                     "crm_matches": found})
    if not a.yes:
        out({"ok": True, "dry_run": True, "target": a.to, "would_create": [p for p in plan if p["action"] == "create"],
             "would_skip": [p for p in plan if p["action"] != "create"], "not_checked": errors,
             "next": "show this to the owner; existing CRM records are never changed. On their yes: crm push ... --yes"})
    created = []
    for p in plan:
        if p["action"] != "create":
            continue
        lead = st["leads"][p["lead"]]
        res, err = crm_create(a.to, lead, best_contact(lead), s)
        if err:
            errors.append({"lead": p["lead"], "error": err})
            continue
        lead.setdefault("crm", {})[a.to] = {"id": res["id"], "pushed": today().isoformat(), "read_back": res["read_back"]}
        created.append({"lead": p["lead"], "crm_id": res["id"], "read_back": res["read_back"]})
        log_event("crm_push", lead=p["lead"], target=a.to, crm_id=res["id"])
    save_store(st)
    out({"ok": not errors, "target": a.to, "created": created, "skipped": [p for p in plan if p["action"] != "create"],
         "errors": errors, "note": "say «создано» only for rows with read_back true"})


# ---------- report and context ----------

def cmd_report(a):
    end = parse_date(a.to, today())
    start = parse_date(a.date_from, end - timedelta(days=6))
    ev = [e for e in events() if start.isoformat() <= e.get("date", "") <= end.isoformat()]
    st = store()

    def count(t, **kw):
        return sum(1 for e in ev if e.get("type") == t and all(e.get(k) == v for k, v in kw.items()))
    sent = [e for e in ev if e.get("type") == "sent"]
    contacted = sorted({e["lead"] for e in sent if e.get("step") == 1})
    replies = [e for e in ev if e.get("type") == "reply"]
    by_cls = {}
    for e in replies:
        by_cls[e["cls"]] = by_cls.get(e["cls"], 0) + 1
    positive = sum(by_cls.get(k, 0) for k in ("interested", "question", "meeting"))
    real_replies = sum(v for k, v in by_cls.items() if k not in ("out_of_office", "bounce"))
    moves = {}
    for e in ev:
        if e.get("type") == "stage":
            k = f"{e.get('old')}→{e.get('new')}"
            moves[k] = moves.get(k, 0) + 1
    by_channel = {}
    for e in sent:
        by_channel[e.get("channel")] = by_channel.get(e.get("channel"), 0) + 1
    stages = {}
    for ld in st["leads"].values():
        stages[ld.get("stage")] = stages.get(ld.get("stage"), 0) + 1
    meetings = count("stage", new="meeting")
    # forecast health from the client's own last 4 weeks, never from industry averages
    h0 = (end - timedelta(days=27)).isoformat()
    hist = [e for e in events() if h0 <= e.get("date", "") <= end.isoformat()]
    h_first = len({e["lead"] for e in hist if e.get("type") == "sent" and e.get("step") == 1})
    h_reply = len({e["lead"] for e in hist if e.get("type") == "reply" and e.get("cls") not in ("out_of_office", "bounce")})
    h_meet = sum(1 for e in hist if e.get("type") == "stage" and e.get("new") == "meeting")
    goal = (s := settings()).get("goals", {}).get("meetings_per_week")
    if h_first < 20:
        forecast = {"status": "too little data", "first_touches_4w": h_first,
                    "assumption": "a forecast needs at least 20 first messages in the last 4 weeks of this client's own data"}
    else:
        rate = h_meet / h_first
        planned = len([1 for q in seqs().values() if q["status"] == "active"])
        forecast = {"status": "estimate", "basis": f"own last 4 weeks: {h_first} first messages, {h_reply} replies, "
                    f"{h_meet} meetings", "meetings_per_first_touch": round(rate, 3),
                    "active_sequences": planned, "expected_meetings_from_active": round(rate * planned, 1),
                    "assumption": "next weeks convert like the last 4; not a promise"}
    if goal:
        forecast["goal_meetings_per_week"] = goal
        forecast["this_week_vs_goal"] = f"{meetings} of {goal}"
    due_next = []
    for lid, q in seqs().items():
        if q["status"] == "active":
            nxt = next((x for x in q["steps"] if x["status"] == "planned"), None)
            if nxt and parse_date(nxt["due"]) <= end + timedelta(days=7):
                due_next.append(lid)
    out({"ok": True, "period": [start.isoformat(), end.isoformat()],
         "found": count("lead_added"), "first_messages": len(contacted), "messages_sent": len(sent),
         "by_channel": by_channel, "replies": real_replies, "replies_by_class": by_cls, "positive_replies": positive,
         "reply_rate": round(real_replies / len(contacted), 3) if contacted else None,
         "meetings": meetings, "opt_outs": by_cls.get("opt_out", 0), "said_no": by_cls.get("no", 0),
         "stage_moves": moves, "pipeline_now": stages, "followups_due_next_7_days": len(due_next),
         "batches_approved": count("approve"), "crm_pushed": count("crm_push"), "forecast_health": forecast,
         "note": "reply_rate is replies / leads that got a first message in the period; None = nothing sent"})


def profile_filled():
    p = data_dir() / "profile" / "leadgen-profile.md"
    if not p.is_file():
        return False
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("- business:") and line.split(":", 1)[1].strip():
            return True
    return False


def cmd_context(a):
    s, st = settings(), store()
    stages, tiers = {}, {}
    for ld in st["leads"].values():
        stages[ld.get("stage")] = stages.get(ld.get("stage"), 0) + 1
        if ld.get("tier"):
            tiers[ld["tier"]] = tiers.get(ld["tier"], 0) + 1
    due = overdue = 0
    for q in seqs().values():
        if q["status"] != "active":
            continue
        prev = True
        for x in q["steps"]:
            if x["status"] == "planned":
                if prev and parse_date(x["due"]) <= today():
                    due += 1
                    overdue += parse_date(x["due"]) < today()
                break
            prev = x["status"] in ("sent", "skipped")
    pending = []
    for f in sorted((data_dir() / "outbox").glob("B*.json")):
        b = json.loads(f.read_text(encoding="utf-8"))
        if b["status"] in ("awaiting_approval", "approved", "partly_sent"):
            pending.append({"batch": b["id"], "status": b["status"],
                            "approved_not_sent": sum(1 for m in b["messages"] if m["status"] == "approved")})
    reports = sorted((data_dir() / "reports").glob("*.md"))
    prof = data_dir() / "profile" / "leadgen-profile.md"
    out({"ok": True, "profile_filled": profile_filled(),
         "profile": prof.read_text(encoding="utf-8")[:3000] if profile_filled() else None,
         "market": s.get("market") or None, "language": s.get("language") or None,
         "icp": s["icp"], "leads": len(st["leads"]), "stages": stages, "tiers": tiers,
         "followups_due_today": due, "overdue": overdue,
         "revisit_due": sum(1 for ld in st["leads"].values() if ld.get("stage") == "not_now" and ld.get("revisit")
                            and parse_date(ld["revisit"]) <= today()),
         "outbox_pending": pending, "dnc": len(load_dnc()["entries"]),
         "sent_today": {ch: sent_today(ch) for ch in CHANNELS},
         "limits": {"email": 30, "telegram": 20, "linkedin": 15, "call": 40, **s["limits"]},
         "crm_target": s.get("crm", {}).get("target"), "routines": s["routines"],
         "keys_present": {k: bool(os.environ.get(k)) for k in SECRET_ENV},
         "last_report": reports[-1].name if reports else None})


def cmd_check(a):
    st, S, dnc = store(), seqs(), load_dnc()
    issues = []
    for lid, ld in st["leads"].items():
        if not ld.get("sources"):
            issues.append(f"{lid}: no source")
        if ld.get("stage") not in STAGES:
            issues.append(f"{lid}: unknown stage {ld.get('stage')}")
        for c in ld.get("contacts") or []:
            if not c.get("source"):
                issues.append(f"{lid}: contact {c.get('name') or c.get('email')} has no source")
        hit = dnc_match(dnc, lead_values(ld))
        if hit and S.get(lid, {}).get("status") == "active":
            issues.append(f"{lid}: on do-not-contact but its sequence is active")
        if ld.get("stage") in CLOSED and S.get(lid, {}).get("status") == "active":
            issues.append(f"{lid}: stage {ld['stage']} but its sequence is active")
    for f in sorted((data_dir() / "outbox").glob("B*.json")):
        b = json.loads(f.read_text(encoding="utf-8"))
        for m in b["messages"]:
            if m["status"] == "sent" and not b.get("approval"):
                issues.append(f"{m['id']}: sent without a recorded approval")
            if m["status"] in ("approved", "sent") and m.get("blocked"):
                issues.append(f"{m['id']}: {m['status']} although blocked: {m['blocked']}")
    keys = {}
    for lid, ld in st["leads"].items():
        for k in keys_of(ld)[0]:
            keys.setdefault(k, []).append(lid)
    dups = {k: v for k, v in keys.items() if len(v) > 1}
    if dups:
        issues.append(f"{len(dups)} duplicate keys: run dedupe")
    out({"ok": not issues, "leads": len(st["leads"]), "sequences": len(S), "dnc": len(dnc["entries"]),
         "issues": issues[:100]})


# ---------- CLI ----------

def lead_from_flags(a):
    raw = {k: getattr(a, k, None) for k in ("company", "domain", "website", "inn", "ogrn", "city", "country", "address",
                                            "industry", "size", "phone", "email", "reason", "batch", "market", "source",
                                            "seen", "what")}
    raw = {k: v for k, v in raw.items() if v}
    if a.contact_name or a.contact_email or a.linkedin:
        raw["contacts"] = [{"name": a.contact_name, "title": a.title, "email": a.contact_email,
                            "email_status": a.email_status, "linkedin": a.linkedin, "phone": a.contact_phone,
                            "source": a.contact_source or a.source, "seen": a.seen}]
    if a.signal:
        raw["signals"] = []
        for sg in a.signal:
            t, _, d = sg.partition(":")
            raw["signals"].append({"type": t, "detail": d, "source": a.signal_source or a.source, "seen": a.seen})
    if a.note:
        raw["notes"] = [a.note]
    return raw


def cmd_lead(a):
    if a.action == "add":
        if a.json:
            try:
                raws = json.loads(Path(a.json).read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                fail(f"cannot read {a.json}: {e}")
            out(add_leads(raws if isinstance(raws, list) else [raws]))
        if not a.company:
            fail("--company and --source are required (or --json FILE)")
        out(add_leads([lead_from_flags(a)]))
    if a.action == "import":
        a.file = a.args[0] if a.args else None
        if not a.file:
            fail("lead import FILE.csv")
        cmd_import(a)
    st = store()
    if a.action == "list":
        leads = list(st["leads"].values())
        if a.stage:
            leads = [x for x in leads if x.get("stage") == a.stage]
        if a.tier:
            leads = [x for x in leads if x.get("tier") == a.tier.upper()]
        if a.min_score is not None:
            leads = [x for x in leads if (x.get("score") or 0) >= a.min_score]
        if a.batch:
            leads = [x for x in leads if x.get("batch") == a.batch]
        leads.sort(key=lambda x: (-(x.get("score") or -1), x["id"]))
        out({"ok": True, "count": len(leads), "leads": [short(x) for x in leads[: a.limit]]})
    if not a.args:
        fail(f"lead {a.action} ID")
    lead = get_lead(st, a.args[0])
    if a.action == "show":
        q = seqs().get(lead["id"])
        out({"ok": True, "lead": lead, "sequence": q, "dnc": dnc_match(load_dnc(), lead_values(lead))})
    if a.action == "set-stage":
        if len(a.args) < 2:
            fail("lead set-stage ID STAGE")
        set_stage(lead, a.args[1], a.note)
        if a.args[1] in CLOSED:
            S = seqs()
            if S.get(lead["id"], {}).get("status") == "active":
                S[lead["id"]].update({"status": "stopped", "stop_reason": "stage " + a.args[1]})
                save("sequences/sequences.json", S)
        save_store(st)
        out({"ok": True, "lead": lead["id"], "stage": lead["stage"]})
    if a.action == "contact":
        c, err = clean_contact({"name": a.contact_name, "title": a.title, "email": a.contact_email,
                                "email_status": a.email_status, "linkedin": a.linkedin, "phone": a.contact_phone,
                                "telegram": a.telegram, "source": a.contact_source or a.source, "seen": a.seen})
        if err:
            fail(err)
        changed = merge_into(lead, {"contacts": [c]})
        if dnc_match(load_dnc(), lead_values(lead)) and lead.get("stage") != "dnc":
            set_stage(lead, "dnc", "contact is on the do-not-contact list")
        save_store(st)
        out({"ok": True, "lead": lead["id"], "added": changed, "contacts": len(lead["contacts"])})
    if a.action == "signal":
        sg, err = clean_signal({"type": a.type, "detail": a.detail, "source": a.source, "seen": a.seen, "date": a.date})
        if err:
            fail(err)
        changed = merge_into(lead, {"signals": [sg]})
        save_store(st)
        out({"ok": True, "lead": lead["id"], "added": changed, "hint": "run score --id to update the score"})
    fail("lead add|import|list|show|set-stage|contact|signal")


def main():
    p = argparse.ArgumentParser(description="Kevin lead store", usage=__doc__)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("context")
    sub.add_parser("check")
    x = sub.add_parser("icp")
    x.add_argument("action", choices=["show", "set"])
    for f in ("industries", "regions", "roles", "exclude", "keywords"):
        x.add_argument("--" + f)
    x.add_argument("--size-min", type=int)
    x.add_argument("--size-max", type=int)
    x = sub.add_parser("lead")
    x.add_argument("action", choices=["add", "import", "list", "show", "set-stage", "contact", "signal"])
    x.add_argument("args", nargs="*")
    for f in ("company", "domain", "website", "inn", "ogrn", "city", "country", "address", "industry", "size", "phone",
              "email", "reason", "batch", "market", "source", "seen", "what", "json", "contact-name", "title",
              "contact-email", "email-status", "linkedin", "contact-phone", "contact-source", "telegram", "signal-source",
              "note", "stage", "tier", "format", "map", "type", "detail", "date"):
        x.add_argument("--" + f)
    x.add_argument("--signal", action="append")
    x.add_argument("--min-score", type=int)
    x.add_argument("--limit", type=int, default=50)
    x = sub.add_parser("dedupe")
    x.add_argument("--apply", action="store_true")
    x = sub.add_parser("score")
    x.add_argument("--id")
    x.add_argument("--all", action="store_true")
    x = sub.add_parser("egrul")
    x.add_argument("query")
    x.add_argument("--limit", type=int, default=10)
    x = sub.add_parser("hh")
    x.add_argument("query")
    x.add_argument("--area")
    x.add_argument("--pages", type=int, default=1)
    x.add_argument("--limit", type=int, default=30)
    x = sub.add_parser("dadata")
    x.add_argument("query")
    x = sub.add_parser("hunter")
    x.add_argument("action", choices=["domain", "verify", "find"])
    x.add_argument("args", nargs="+")
    x.add_argument("--update", action="store_true")
    x = sub.add_parser("apollo")
    x.add_argument("action", choices=["people"])
    x.add_argument("--domain", required=True)
    x.add_argument("--titles")
    x.add_argument("--limit", type=int, default=10)
    x = sub.add_parser("mx")
    x.add_argument("target")
    x.add_argument("--update", action="store_true")
    x = sub.add_parser("pattern")
    x.add_argument("domain")
    x.add_argument("--first", required=True)
    x.add_argument("--last", required=True)
    x.add_argument("--pattern")
    x = sub.add_parser("seq")
    x.add_argument("action", choices=["plan", "due", "mark", "stop", "list"])
    x.add_argument("id", nargs="?")
    x.add_argument("step", nargs="?", type=int)
    x.add_argument("result", nargs="?", choices=["sent", "skipped"])
    x.add_argument("--channel", default="email", choices=CHANNELS)
    x.add_argument("--to")
    x.add_argument("--start")
    x.add_argument("--steps", type=int)
    x.add_argument("--date")
    x.add_argument("--days", type=int, default=0)
    x.add_argument("--reason")
    x.add_argument("--force", action="store_true")
    x = sub.add_parser("reply")
    x.add_argument("id")
    x.add_argument("--class", dest="cls", required=True)
    x.add_argument("--note")
    x.add_argument("--days", type=int, default=7)
    x = sub.add_parser("dnc")
    x.add_argument("action", choices=["add", "check", "list"])
    x.add_argument("values", nargs="*")
    x.add_argument("--reason")
    x.add_argument("--lead")
    x.add_argument("--batch")
    x = sub.add_parser("outbox")
    x.add_argument("action", choices=["new", "list", "show", "approve", "mark", "cancel"])
    x.add_argument("batch", nargs="?")
    x.add_argument("msg", nargs="?")
    x.add_argument("result", nargs="?", choices=["sent", "failed", "skipped"])
    x.add_argument("--file")
    x.add_argument("--channel", default="email", choices=CHANNELS)
    x.add_argument("--by")
    x.add_argument("--note")
    x.add_argument("--error")
    x.add_argument("--md", action="store_true")
    x = sub.add_parser("export")
    x.add_argument("--format", required=True, choices=["amocrm", "bitrix", "hubspot", "sheets", "csv", "xlsx"])
    x.add_argument("--stage")
    x.add_argument("--min-score", type=int)
    x.add_argument("--ids")
    x.add_argument("--out")
    x = sub.add_parser("crm")
    x.add_argument("action", choices=["push"])
    x.add_argument("--to", required=True, choices=["amocrm", "bitrix"])
    x.add_argument("--stage")
    x.add_argument("--min-score", type=int)
    x.add_argument("--ids")
    x.add_argument("--yes", action="store_true")
    x = sub.add_parser("report")
    x.add_argument("kind", choices=["weekly"])
    x.add_argument("--from", dest="date_from")
    x.add_argument("--to")
    a = p.parse_args()
    if not a.cmd:
        sys.exit(__doc__)
    if a.cmd in ("outbox",) and a.action in ("show", "approve", "mark", "cancel") and not a.batch:
        fail(f"outbox {a.action} BATCH")
    if a.cmd == "outbox" and a.action == "new" and not a.file:
        fail("outbox new --file DRAFTS.json")
    if a.cmd == "outbox" and a.action == "mark" and (not a.msg or not a.result):
        fail("outbox mark BATCH MSG_ID|today sent|failed|skipped")
    if a.cmd == "seq" and a.action in ("plan", "mark", "stop") and not a.id:
        fail(f"seq {a.action} LEAD_ID")
    if a.cmd == "seq" and a.action == "mark" and (a.step is None or not a.result):
        fail("seq mark LEAD_ID STEP sent|skipped")
    {"context": cmd_context, "check": cmd_check, "icp": cmd_icp, "lead": cmd_lead, "dedupe": cmd_dedupe,
     "score": cmd_score, "egrul": cmd_egrul, "hh": cmd_hh, "dadata": cmd_dadata, "hunter": cmd_hunter,
     "apollo": cmd_apollo, "mx": cmd_mx, "pattern": cmd_pattern, "seq": cmd_seq, "reply": cmd_reply, "dnc": cmd_dnc,
     "outbox": cmd_outbox, "export": cmd_export, "crm": cmd_crm, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
