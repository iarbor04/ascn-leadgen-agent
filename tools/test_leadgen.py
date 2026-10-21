#!/usr/bin/env python3
"""Offline tests for workspace/files/scripts/leadgen.py. No network: every HTTP call is mocked.

  python3 tools/test_leadgen.py
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "workspace" / "files" / "scripts" / "leadgen.py"
DEFAULTS = REPO / "workspace" / "defaults"


def load_module():
    spec = importlib.util.spec_from_file_location("leadgen", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="leadgen-test-"))
        self.data = self.tmp / "files" / "leadgen"
        shutil.copytree(DEFAULTS, self.data)
        self.env = {"LEADGEN_DATA": str(self.data), "LEADGEN_TODAY": "2026-10-21", "PACKAGE_ROOT": str(self.tmp)}
        self.old_env = {k: os.environ.get(k) for k in list(self.env) + ["HUNTER_API_KEY", "AMO_DOMAIN", "AMO_TOKEN",
                                                                         "BITRIX_WEBHOOK_URL", "APOLLO_API_KEY", "HH_APP_TOKEN"]}
        for k in self.old_env:
            os.environ.pop(k, None)
        os.environ.update(self.env)
        self.m = load_module()
        self.calls = []
        self.responses = []
        self.m.http = self.fake_http

    def tearDown(self):
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_http(self, method, url, headers=None, body=None, form=None, timeout=25):
        self.calls.append({"method": method, "url": url, "body": body, "form": form, "headers": headers})
        for match, resp in self.responses:
            if match in url:
                return resp(url, body) if callable(resp) else resp
        return False, "cannot reach host: mocked offline"

    def run_cli(self, *args):
        sys.argv = ["leadgen.py", *args]
        buf = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(buf):
            try:
                self.m.main()
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        text = buf.getvalue()
        try:
            return code, json.loads(text)
        except ValueError:
            return code, text

    def write(self, name, content, encoding="utf-8"):
        p = self.tmp / name
        p.write_bytes(content.encode(encoding))
        return str(p)

    def add(self, **kw):
        base = {"company": "Acme", "source": "https://example.org/acme"}
        base.update(kw)
        f = self.write("lead.json", json.dumps([base], ensure_ascii=False))
        return self.run_cli("lead", "add", "--json", f)


class TestLeads(Base):
    def test_lead_needs_source(self):
        code, r = self.run_cli("lead", "add", "--company", "Нет Источника")
        self.assertEqual(r["counts"]["added"], 0)
        self.assertTrue(any("no source" in x for x in r["rejected"]))

    def test_contact_needs_source_and_valid_status(self):
        code, r = self.add(contacts=[{"name": "Ivan Petrov", "email": "ivan@acme.ru", "source": ""}])
        self.assertEqual(r["counts"]["added"], 1)
        self.assertTrue(any("contact without source" in x for x in r["rejected"]))
        code, r = self.run_cli("lead", "show", "L0001")
        self.assertEqual(r["lead"]["contacts"], [])

    def test_merge_on_domain_and_flag_same_name(self):
        self.add(company="ООО «Ромашка»", website="https://www.romashka.ru/about", city="Казань")
        code, r = self.add(company="Romashka LLC", domain="romashka.ru", inn="1655000000",
                           source="https://example.org/r2")
        self.assertEqual(r["counts"]["merged"], 1)
        self.assertIn("domain:romashka.ru", r["merged"][0]["by"])
        code, r = self.add(company="Ромашка", city="Казань", source="https://example.org/r3")
        self.assertEqual(r["counts"]["added"], 1)
        self.assertEqual(r["possible_duplicates"][0]["same_name_as"], ["L0001"])
        code, r = self.run_cli("lead", "show", "L0001")
        self.assertEqual(r["lead"]["inn"], "1655000000")
        self.assertEqual(len(r["lead"]["sources"]), 2)

    def test_import_apollo_drops_private_phones_and_labels_guesses(self):
        csv_text = ("First Name,Last Name,Title,Company,Email,Email Status,Mobile Phone,Corporate Phone,Website,City,"
                    "# Employees,Industry,Person Linkedin Url\n"
                    "Anna,Smith,Head of Sales,Northwind,anna@northwind.io,Verified,+1 555 0100,+1 555 0199,"
                    "northwind.io,Austin,51-200,Software,https://linkedin.com/in/x\n"
                    "Bob,Lee,CEO,Northwind,bob@northwind.io,Guessed,,,northwind.io,Austin,51-200,Software,\n"
                    "Carl,Ray,CTO,Contoso,carl@contoso.com,Unavailable,+1 555 0111,,contoso.com,Boston,11-50,Retail,\n")
        f = self.write("apollo.csv", csv_text)
        code, r = self.run_cli("lead", "import", f, "--format", "apollo")
        self.assertEqual(code, 0)
        self.assertEqual(r["counts"]["added"], 2)
        self.assertEqual(r["counts"]["merged"], 1)
        self.assertEqual(r["private_phones_ignored"]["rows_with_value"], 2)
        code, r = self.run_cli("lead", "show", "L0001")
        statuses = {c["email"]: c["email_status"] for c in r["lead"]["contacts"]}
        self.assertEqual(statuses, {"anna@northwind.io": "verified", "bob@northwind.io": "pattern"})
        self.assertNotIn("0100", json.dumps(r["lead"]))
        self.assertTrue(r["lead"]["sources"][0]["url"].startswith("file:apollo.csv"))

    def test_import_2gis_cp1251_semicolon(self):
        text = ("Наименование;Город;Рубрика;Телефон;E-mail;Сайт;Ссылка\n"
                "Стоматология Улыбка;Казань;Стоматологии;8 (843) 200-00-00;info@ulybka.ru;ulybka.ru;"
                "https://2gis.ru/kazan/firm/1\n")
        f = self.write("2gis.csv", text, encoding="cp1251")
        code, r = self.run_cli("lead", "import", f, "--format", "2gis")
        self.assertEqual(r["counts"]["added"], 1)
        code, r = self.run_cli("lead", "show", "L0001")
        lead = r["lead"]
        self.assertEqual(lead["phone"], "+78432000000")
        self.assertEqual(lead["email"], "info@ulybka.ru")
        self.assertEqual(lead["sources"][0]["url"], "https://2gis.ru/kazan/firm/1")

    def test_import_without_company_column(self):
        f = self.write("x.csv", "foo,bar\n1,2\n")
        code, r = self.run_cli("lead", "import", f)
        self.assertEqual(code, 1)
        self.assertIn("no company column", r["error"])

    def test_dedupe_groups_and_apply(self):
        self.add(company="Alpha", inn="7700000001", source="https://a/1")
        self.add(company="Alpha Group", source="https://a/2", phone="+7 495 000-00-01")
        self.add(company="Alpha", inn="7700000001", source="https://a/3")  # merged on add
        st = self.m.store()
        st["leads"]["L0002"]["inn"] = "7700000001"  # a duplicate that arrived by hand
        self.m.save_store(st)
        code, r = self.run_cli("dedupe")
        self.assertEqual(r["sure_groups"], [["L0001", "L0002"]])
        code, r = self.run_cli("dedupe", "--apply")
        self.assertEqual(r["merged"], [{"kept": "L0001", "removed": ["L0002"]}])
        code, r = self.run_cli("lead", "list")
        self.assertEqual(r["count"], 1)


class TestScoring(Base):
    def test_score_requires_icp(self):
        self.add()
        code, r = self.run_cli("score")
        self.assertEqual(code, 1)
        self.assertIn("ideal customer", r["error"])

    def test_fit_intent_tiers_and_exclusion(self):
        self.run_cli("icp", "set", "--industries", "стоматолог,dental", "--regions", "Казань", "--size-min", "10",
                     "--size-max", "200", "--roles", "директор,owner", "--exclude", "сеть федеральная")
        self.add(company="Улыбка", industry="Стоматологии", city="Казань", size="20-50",
                 contacts=[{"name": "И. Иванов", "title": "Главный директор", "source": "https://ulybka.ru/team"}],
                 signals=[{"type": "hiring", "detail": "ищут администратора", "source": "https://hh.ru/vacancy/1",
                           "date": "2026-10-10"}])
        self.add(company="Зуб", industry="Стоматологии", city="Москва", source="https://example.org/zub",
                 signals=[{"type": "tender", "detail": "old tender", "source": "https://zakupki.gov.ru/x",
                           "date": "2026-01-01"}])
        self.add(company="Сеть федеральная Дент", industry="стоматология", source="https://example.org/fed")
        code, r = self.run_cli("score", "--all")
        by = {x["id"]: x for x in r["leads"]}
        self.assertEqual(by["L0001"]["score"], 60 + 15)
        self.assertEqual(by["L0001"]["tier"], "A")
        self.assertEqual(by["L0002"]["tier"], "C")
        self.assertIn("size", by["L0002"]["not_known"])
        self.assertTrue(any("half weight" in x for x in by["L0002"]["reasons"]))
        self.assertEqual(by["L0003"]["tier"], "DQ")


class TestOutreach(Base):
    def setUp(self):
        super().setUp()
        self.add(company="Northwind", domain="northwind.io", contacts=[
            {"name": "Anna", "email": "anna@northwind.io", "email_status": "public", "source": "https://northwind.io/team"},
            {"name": "Bob", "email": "bob@northwind.io", "email_status": "pattern", "source": "https://northwind.io/team"}])
        self.add(company="Contoso", domain="contoso.com", source="https://contoso.com", contacts=[
            {"name": "Carl", "email": "carl@contoso.com", "email_status": "verified", "source": "https://contoso.com/about"}])
        self.opt = " If this isn't relevant, just reply \"no\" and I won't write again."

    def drafts(self, items):
        return self.write("drafts.json", json.dumps(items, ensure_ascii=False))

    def test_gates_block_pattern_optout_placeholders_dnc(self):
        self.run_cli("dnc", "add", "contoso.com", "--reason", "asked to stop")
        f = self.drafts([
            {"lead": "L0001", "to": "anna@northwind.io", "subject": "Hi", "body": "Saw your new office in Austin." + self.opt},
            {"lead": "L0001", "to": "bob@northwind.io", "subject": "Hi", "body": "Saw your new office in Austin." + self.opt},
            {"lead": "L0002", "to": "carl@contoso.com", "subject": "Hi", "body": "Saw your launch last week, nice." + self.opt},
            {"lead": "L0001", "to": "anna@northwind.io", "subject": "Hi", "body": "Hello [NAME], about your [PAIN]." + self.opt},
        ])
        code, r = self.run_cli("outbox", "new", "--file", f)
        self.assertEqual(r["ready"], 1)
        why = {b["id"]: " ".join(b["why"]) for b in r["blocked"]}
        self.assertIn("pattern", why["B0001-02"])
        self.assertIn("do-not-contact", why["B0001-03"])
        self.assertIn("placeholders", why["B0001-04"])
        f2 = self.drafts([{"lead": "L0001", "to": "anna@northwind.io", "subject": "Hi", "body": "Saw your new office in Austin."}])
        code, r = self.run_cli("outbox", "new", "--file", f2)
        self.assertIn("opt-out", " ".join(r["blocked"][0]["why"]))

    def test_no_send_without_approval_and_daily_limit(self):
        s = json.loads((self.data / "settings.json").read_text())
        s["limits"]["email"] = 1
        (self.data / "settings.json").write_text(json.dumps(s))
        f = self.drafts([
            {"lead": "L0001", "to": "anna@northwind.io", "subject": "Austin office", "body": "Saw your new office in Austin." + self.opt},
            {"lead": "L0002", "to": "carl@contoso.com", "subject": "Launch", "body": "Saw your launch last week, nice." + self.opt}])
        self.run_cli("outbox", "new", "--file", f)
        code, r = self.run_cli("outbox", "mark", "B0001", "B0001-01", "sent")
        self.assertEqual(code, 1)
        self.assertIn("approve", r["hint"])
        code, r = self.run_cli("outbox", "approve", "B0001")
        self.assertEqual(code, 1)
        code, r = self.run_cli("outbox", "approve", "B0001", "--by", "owner in chat")
        self.assertEqual(r["approved"], 2)
        self.assertEqual(r["send_today"], ["B0001-01"])
        self.assertEqual(r["later_days"], ["B0001-02"])
        code, r = self.run_cli("outbox", "mark", "B0001", "today", "sent")
        self.assertEqual(r["marked"], ["B0001-01"])
        code, r = self.run_cli("outbox", "mark", "B0001", "B0001-02", "sent")
        self.assertEqual(code, 1)
        self.assertIn("limit", r["error"])
        code, r = self.run_cli("lead", "show", "L0001")
        self.assertEqual(r["lead"]["stage"], "contacted")
        self.assertEqual(r["sequence"]["status"], "active")
        code, r = self.run_cli("check")
        self.assertTrue(r["ok"], r)

    def test_sequence_dates_and_opt_out_stops_everything(self):
        code, r = self.run_cli("seq", "plan", "L0001", "--to", "anna@northwind.io", "--start", "2026-10-20")
        self.assertEqual([x["due"] for x in r["sequence"]["steps"]], ["2026-10-20", "2026-10-23", "2026-10-27", "2026-11-03"])
        self.run_cli("seq", "mark", "L0001", "1", "sent", "--date", "2026-10-21")
        code, r = self.run_cli("seq", "due", "--days", "2")
        self.assertEqual(r["due"], [])
        code, r = self.run_cli("seq", "due", "--date", "2026-10-24")
        self.assertEqual(r["due"][0]["step"], 2)
        code, r = self.run_cli("reply", "L0001", "--class", "opt_out")
        self.assertEqual(r["stage"], "dnc")
        self.assertIn("email:anna@northwind.io", r["dnc_added"])
        code, r = self.run_cli("seq", "due", "--date", "2026-12-31")
        self.assertEqual(r["due"], [])
        f = self.drafts([{"lead": "L0001", "to": "anna@northwind.io", "body": "Following up on my note." + self.opt}])
        code, r = self.run_cli("outbox", "new", "--file", f)
        self.assertEqual(r["ready"], 0)
        code, r = self.run_cli("seq", "plan", "L0001")
        self.assertEqual(code, 1)

    def test_reply_after_approval_skips_send(self):
        f = self.drafts([{"lead": "L0002", "to": "carl@contoso.com", "subject": "Launch",
                          "body": "Saw your launch last week, nice." + self.opt}])
        self.run_cli("outbox", "new", "--file", f)
        self.run_cli("outbox", "approve", "B0001", "--by", "owner")
        self.run_cli("reply", "L0002", "--class", "no")
        code, r = self.run_cli("outbox", "mark", "B0001", "B0001-01", "sent")
        self.assertIn("skipped", r["marked"][0])

    def test_not_now_revisit(self):
        code, r = self.run_cli("reply", "L0002", "--class", "not_now")
        self.assertEqual(r["revisit"], "2027-01-19")
        os.environ["LEADGEN_TODAY"] = "2027-01-20"
        code, r = self.run_cli("seq", "due")
        self.assertEqual(r["revisit_not_now"][0]["lead"], "L0002")

    def test_export_formats_keep_unverified_out_of_email_column(self):
        st = self.m.store()
        st["leads"]["L0001"]["contacts"] = st["leads"]["L0001"]["contacts"][1:]  # only the pattern address left
        self.m.save_store(st)
        self.run_cli("dnc", "add", "contoso.com")
        code, r = self.run_cli("export", "--format", "amocrm")
        self.assertEqual(r["rows"], 1)
        text = Path(r["file"]).read_text(encoding="utf-8-sig")
        self.assertIn(";", text.splitlines()[0])
        row = text.splitlines()[1]
        self.assertIn("bob@northwind.io (pattern, not verified)", row)
        self.assertNotIn(";bob@northwind.io;", row)
        code, r = self.run_cli("export", "--format", "xlsx")
        self.assertTrue(r["file"].endswith((".xlsx", ".csv")))

    def test_weekly_report(self):
        f = self.drafts([{"lead": "L0001", "to": "anna@northwind.io", "subject": "Austin office",
                          "body": "Saw your new office in Austin." + self.opt}])
        self.run_cli("outbox", "new", "--file", f)
        self.run_cli("outbox", "approve", "B0001", "--by", "owner")
        self.run_cli("outbox", "mark", "B0001", "today", "sent")
        self.run_cli("reply", "L0001", "--class", "meeting")
        code, r = self.run_cli("report", "weekly")
        self.assertEqual(r["found"], 2)
        self.assertEqual(r["first_messages"], 1)
        self.assertEqual(r["replies"], 1)
        self.assertEqual(r["meetings"], 1)
        self.assertEqual(r["reply_rate"], 1.0)
        self.assertEqual(r["forecast_health"]["status"], "too little data")


class TestConnectors(Base):
    def test_egrul_ok_captcha_and_offline(self):
        self.responses = [("search-result", (True, {"rows": [{"n": "ООО \"ТЕСТ\"", "i": "7707083893", "o": "1027700132195",
                                                               "a": "г. Москва", "g": "Директор: Иванов", "r": "01.01.2002",
                                                               "k": "ul"}]})),
                          ("egrul.nalog.ru", (True, {"t": "abc", "captchaRequired": False}))]
        code, r = self.run_cli("egrul", "7707083893")
        self.assertEqual(r["status"], "checked")
        self.assertEqual(r["rows"][0]["ogrn"], "1027700132195")
        self.responses = [("egrul.nalog.ru", (True, {"captchaRequired": True}))]
        code, r = self.run_cli("egrul", "7707083893")
        self.assertEqual(r["status"], "not checked")
        self.responses = []
        code, r = self.run_cli("egrul", "7707083893")
        self.assertEqual(r["status"], "not checked")
        self.assertIn("never report it as zero", r["note"])

    def test_hh_groups_employers(self):
        items = [{"name": "SDR", "employer": {"id": "1", "name": "Альфа", "alternate_url": "https://hh.ru/employer/1"},
                  "published_at": "2026-10-19T10:00:00+0300", "area": {"name": "Москва"},
                  "alternate_url": "https://hh.ru/vacancy/11"},
                 {"name": "Head of Sales", "employer": {"id": "1", "name": "Альфа"}, "published_at": "2026-10-20T10:00:00+0300",
                  "area": {"name": "Казань"}, "alternate_url": "https://hh.ru/vacancy/12"},
                 {"name": "SDR", "employer": {"id": "2", "name": "Бета"}, "published_at": "2026-10-01T10:00:00+0300",
                  "area": {"name": "Москва"}, "alternate_url": "https://hh.ru/vacancy/21"}]
        self.responses = [("api.hh.ru", (True, {"found": 3, "items": items}))]
        code, r = self.run_cli("hh", "менеджер по продажам", "--area", "1")
        self.assertEqual(r["employers"][0]["employer"], "Альфа")
        self.assertEqual(r["employers"][0]["vacancies"], 2)
        self.assertEqual(r["employers"][0]["latest"], "2026-10-20")
        self.assertEqual(r["employers"][0]["areas"], ["Казань", "Москва"])
        self.assertIn("HH-User-Agent", self.calls[0]["headers"])
        self.responses = [("api.hh.ru", (False, "HTTP 403 from api.hh.ru. access refused"))]
        code, r = self.run_cli("hh", "x")
        self.assertEqual(r["status"], "not checked")

    def test_mx_and_offline(self):
        self.add(company="Northwind", domain="northwind.io", contacts=[
            {"name": "Bob", "email": "bob@northwind.io", "email_status": "pattern", "source": "https://n/team"}])
        self.responses = [("cloudflare-dns.com", (True, {"Status": 0, "Answer": [{"type": 15, "data": "10 mx.northwind.io."}]}))]
        code, r = self.run_cli("mx", "bob@northwind.io", "--update")
        self.assertTrue(r["has_mx"])
        self.assertIn("does NOT prove", r["meaning"])
        code, r = self.run_cli("lead", "show", "L0001")
        self.assertEqual(r["lead"]["contacts"][0]["email_status"], "pattern")
        self.responses = []
        code, r = self.run_cli("mx", "northwind.io")
        self.assertEqual(r["status"], "not checked")

    def test_paid_sources_need_keys_and_never_print_them(self):
        code, r = self.run_cli("hunter", "verify", "bob@northwind.io")
        self.assertEqual(r["status"], "needs key")
        self.assertIn("Settings → Secrets", r["hint"])
        code, r = self.run_cli("apollo", "people", "--domain", "northwind.io")
        self.assertEqual(r["status"], "needs key")
        os.environ["HUNTER_API_KEY"] = "sekret-hunter-key-123"
        self.add(company="Northwind", domain="northwind.io", contacts=[
            {"name": "Bob", "email": "bob@northwind.io", "email_status": "pattern", "source": "https://n/team"}])
        self.responses = [("email-verifier", (True, {"data": {"status": "valid"}}))]
        code, r = self.run_cli("hunter", "verify", "bob@northwind.io", "--update")
        self.assertEqual(r["store_status"], "verified")
        code, r = self.run_cli("lead", "show", "L0001")
        self.assertEqual(r["lead"]["contacts"][0]["email_status"], "verified")
        self.responses = [("email-verifier", (False, "HTTP 401 for url ...api_key=sekret-hunter-key-123"))]
        sys.argv = ["leadgen.py", "hunter", "verify", "bob@northwind.io"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit):
                self.m.main()
        self.assertNotIn("sekret-hunter-key-123", buf.getvalue())

    def test_pattern_is_labeled_and_transliterated(self):
        code, r = self.run_cli("pattern", "romashka.ru", "--first", "Иван", "--last", "Петров")
        emails = [c["email"] for c in r["candidates"]]
        self.assertIn("ivan.petrov@romashka.ru", emails)
        self.assertTrue(all(c["email_status"] == "pattern" for c in r["candidates"]))
        code, r = self.run_cli("pattern", "gmail.com", "--first", "a", "--last", "b")
        self.assertEqual(code, 1)

    def test_crm_push_dry_run_then_write_with_read_back(self):
        os.environ.update({"AMO_DOMAIN": "test.amocrm.ru", "AMO_TOKEN": "tok-amo-999"})
        self.add(company="Northwind", domain="northwind.io", contacts=[
            {"name": "Anna", "email": "anna@northwind.io", "email_status": "public", "source": "https://n/team"}])
        self.add(company="Contoso", domain="contoso.com", source="https://contoso.com")
        self.responses = [("/api/v4/companies?", lambda url, body: (True, {"_embedded": {"companies": [{"id": 5}]}})
                           if "contoso" in url else (True, {})),
                          ("/api/v4/leads/complex", (True, [{"id": 777}])),
                          ("/api/v4/leads/777/notes", (True, {})),
                          ("/api/v4/leads/777", (True, {"id": 777}))]
        code, r = self.run_cli("crm", "push", "--to", "amocrm")
        self.assertTrue(r["dry_run"])
        self.assertEqual([x["lead"] for x in r["would_create"]], ["L0001"])
        self.assertEqual([x["lead"] for x in r["would_skip"]], ["L0002"])
        self.assertFalse(any(c["method"] == "POST" for c in self.calls))
        code, r = self.run_cli("crm", "push", "--to", "amocrm", "--yes")
        self.assertEqual(r["created"], [{"lead": "L0001", "crm_id": 777, "read_back": True}])
        code, r = self.run_cli("crm", "push", "--to", "amocrm", "--ids", "L0001")
        self.assertEqual(code, 1)  # already pushed: never twice

    def test_bitrix_needs_webhook(self):
        self.add()
        code, r = self.run_cli("crm", "push", "--to", "bitrix")
        self.assertEqual(r["status"], "needs key")
        self.assertIn("BITRIX_WEBHOOK_URL", r["missing"])


class TestContext(Base):
    def test_context_on_fresh_data(self):
        code, r = self.run_cli("context")
        self.assertEqual(code, 0)
        self.assertFalse(r["profile_filled"])
        self.assertEqual(r["leads"], 0)
        self.assertFalse(r["routines"]["lead_batch"]["on"])
        self.assertFalse(any(r["keys_present"].values()))

    def test_check_flags_contact_without_source(self):
        self.add(company="X", contacts=[{"name": "Y", "source": "https://x/team"}])
        st = self.m.store()
        st["leads"]["L0001"]["contacts"][0]["source"] = None
        self.m.save_store(st)
        code, r = self.run_cli("check")
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
