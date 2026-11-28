"""owner 28 Nov: NEWS CAMPAIGNS added in the News360 Backend - a sponsor's ad in the bottom space of news reels. They are a second
source for poster/promo.py (the backend's store): chosen pages, start and end date, on every news / a number a day / a number in
total, on normal / priority / all news. A sample reel is made first; only an APPROVED campaign reaches a posted reel.
The same test file is in all 7 page repositories."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
sys.path.insert(0, str(ROOT / "research_free"))
import backend_news as bn      # noqa: E402
import promo      # noqa: E402

DAY = "2026-11-28"


def camp(**kw):
    return dict({"id": "CP-1", "brand": "Sri Lakshmi Silks", "title": "விற்பனை", "message": "ஈரோடு", "pages": "erode,salem", "start": "2026-11-20", "end": "2026-12-05",
                 "per_day": "all", "total": "", "news": "mixed", "status": "approved", "_src": "backend"}, **kw)


class ChoosingTheCampaign(unittest.TestCase):
    def test_only_approved_on_its_pages_and_dates(self):
        self.assertEqual(promo.choose([camp()], {}, "erode", DAY)["id"], "CP-1")
        self.assertIsNone(promo.choose([camp()], {}, "karur", DAY))      # not one of its pages
        self.assertIsNone(promo.choose([camp(start="2026-11-29")], {}, "erode", DAY))      # not started
        self.assertIsNone(promo.choose([camp(end="2026-11-27")], {}, "erode", DAY))      # over
        for st in ("sample_needed", "sample_ready", "changes", "rejected", "paused"):      # the sample is not approved: never on a posted reel
            self.assertIsNone(promo.choose([camp(status=st)], {}, "erode", DAY), st)

    def test_a_number_of_news_a_day(self):
        c = camp(per_day="2")
        self.assertIsNotNone(promo.choose([c], {"CP-1|erode|" + DAY: 1}, "erode", DAY))
        self.assertIsNone(promo.choose([c], {"CP-1|erode|" + DAY: 2}, "erode", DAY))
        self.assertIsNotNone(promo.choose([c], {"CP-1|erode|" + DAY: 2}, "salem", DAY))      # each page has its own count
        self.assertIsNotNone(promo.choose([c], {"CP-1|erode|2026-11-27": 2}, "erode", DAY))      # a new day starts again

    def test_a_number_of_news_in_total(self):
        c = camp(total="50")
        self.assertIsNotNone(promo.choose([c], {"CP-1|total": 49}, "erode", DAY))
        self.assertIsNone(promo.choose([c], {"CP-1|total": 50}, "erode", DAY))
        self.assertIsNone(promo.choose([c], {"CP-1|total": 50}, "salem", DAY))      # the total is for all its pages together

    def test_normal_priority_or_mixed_news(self):
        for kind, urgent, normal in (("mixed", True, True), ("normal", False, True), ("priority", True, False)):
            c = camp(news=kind)
            self.assertEqual(promo.choose([c], {}, "erode", DAY, True) is not None, urgent, kind)
            self.assertEqual(promo.choose([c], {}, "erode", DAY, False) is not None, normal, kind)
            self.assertIsNotNone(promo.choose([c], {}, "erode", DAY, None), kind)      # the kind of news is unknown: the ad still goes
            self.assertIsNotNone(promo.choose([c], {}, "erode", DAY), kind)      # callers that do not say (the old way) are unchanged

    def test_a_full_campaign_gives_way_to_the_next(self):
        rows = [camp(id="CP-1", per_day="1"), camp(id="CP-2")]
        self.assertEqual(promo.choose(rows, {"CP-1|erode|" + DAY: 1}, "erode", DAY)["id"], "CP-2")

    def test_safe_bool(self):
        self.assertIs(promo.safe_bool(lambda r: 1, {}), True)
        self.assertIs(promo.safe_bool(lambda r: "", {}), False)
        self.assertIsNone(promo.safe_bool(lambda r: 1 / 0, {}))


class TwoSources(unittest.TestCase):
    def setUp(self):
        promo._CACHE.clear()
        self.addCleanup(promo._CACHE.clear)

    def env(self, hub=True, backend=True):
        e = {"PROMO_URL": "https://hub" if hub else "", "PROMO_KEY": "pk" if hub else "", "DASH_URL": "https://store" if backend else "", "DASH_WRITE_KEY": "dk" if backend else ""}
        return mock.patch.dict(os.environ, e)

    def test_hub_and_backend_rows_together(self):
        with self.env(), mock.patch.object(promo, "hub_get", return_value={"ok": True, "promos": [{"id": "P1", "status": "approved"}], "used": {"P1|erode|" + DAY: 1}}), \
                mock.patch.object(promo, "dash", return_value={"ok": True, "promos": [{"id": "CP-1", "status": "approved"}], "used": {"CP-1|total": 4}}) as d:
            rows, used = promo.promos(fresh=True)
        self.assertEqual([(r["id"], promo.from_backend(r)) for r in rows], [("P1", False), ("CP-1", True)])
        self.assertEqual(used, {"P1|erode|" + DAY: 1, "CP-1|total": 4})
        d.assert_called_once_with("camp_feed")

    def test_backend_alone_and_a_silent_store(self):
        with self.env(hub=False), mock.patch.object(promo, "hub_get", side_effect=AssertionError("no hub")), mock.patch.object(promo, "dash", return_value={"ok": True, "promos": [camp()], "used": {}}), \
                mock.patch.object(promo, "today", return_value=DAY):
            self.assertEqual(promo.active_for("erode")["id"], "CP-1")
            self.assertEqual(promo.active_for("erode", priority=True)["id"], "CP-1")      # a mixed campaign also goes on priority news
        promo._CACHE.clear()
        with self.env(), mock.patch.object(promo, "hub_get", return_value={"ok": True, "promos": [{"id": "P1", "status": "approved", "pages": "erode", "start": "2026-01-01", "end": "2099-01-01"}], "used": {}}), \
                mock.patch.object(promo, "dash", side_effect=RuntimeError("store down")), mock.patch.object(promo, "today", return_value=DAY):
            self.assertEqual(promo.active_for("erode")["id"], "P1")      # a store that does not answer never hides the form's promotions

    def test_nothing_set_up_nothing_happens(self):
        with self.env(hub=False, backend=False), mock.patch.object(promo, "hub_get", side_effect=AssertionError), mock.patch.object(promo, "dash", side_effect=AssertionError):
            self.assertIsNone(promo.active_for("erode"))
            self.assertEqual(promo.samples(), 0)

    def test_the_key_goes_in_the_body_never_in_the_link(self):
        seen = {}

        class R:
            def raise_for_status(self): pass
            def json(self): return {"ok": True, "promos": [], "used": {}}

        def post(url, data=None, headers=None, timeout=0, **kw):
            seen.update(url=url, body=data.decode("utf-8"), kw=kw)
            return R()
        with self.env(), mock.patch.object(promo.requests, "post", post):
            promo.dash("camp_feed")
        self.assertEqual(seen["url"], "https://store")
        self.assertIn('"key": "dk"', seen["body"])
        self.assertNotIn("params", seen["kw"])

    def test_a_use_is_counted_in_the_right_place_and_in_this_run(self):
        promo._CACHE["p"] = ([camp(per_day="1")], {})
        with self.env(), mock.patch.object(promo, "dash", return_value={"ok": True}) as d, mock.patch.object(promo, "hub_post") as h, mock.patch.object(promo, "today", return_value=DAY):
            promo.mark_used(camp(), "erode", "RN-5")
            d.assert_called_once_with("camp_used", id="CP-1", page="erode", date=DAY, story="RN-5")
            h.assert_not_called()
            self.assertIsNone(promo.active_for("erode"))      # the next reel of the same run sees the count (1 a day)
            promo.mark_used({"id": "P1"}, "erode", "RN-6")      # a promotion of the form still goes to the hub
            h.assert_called_once()

    def test_the_ad_picture_comes_from_the_backend(self):
        import base64
        with self.env(), tempfile.TemporaryDirectory() as t, mock.patch.object(promo, "dash", return_value={"ok": True, "mime": "image/png", "data": base64.b64encode(b"PNGDATA").decode()}) as d, \
                mock.patch.object(promo, "hub_get", side_effect=AssertionError):
            f = promo.asset(camp(file_ids="CP-1"), t)
            self.assertEqual(f.read_bytes(), b"PNGDATA")
            self.assertEqual(f.suffix, ".png")
            d.assert_called_once_with("camp_file", id="CP-1")
            self.assertIsNone(promo.asset(camp(file_ids=""), t))      # no picture: the box shows the words only


class TheSample(unittest.TestCase):
    def setUp(self):
        promo._CACHE.clear()
        self.addCleanup(promo._CACHE.clear)

    def run_samples(self, rows, fail=False):
        calls = []
        fake_post = mock.Mock(LABEL={"erode": "ஈரோடு 360"}, upload=mock.Mock(return_value="https://media.example/sample.mp4"))

        def dash(action, **kw):
            calls.append((action, kw))
            return {"ok": True, "promos": rows, "used": {}}

        def make(post_, p, page, work):
            if fail:
                raise RuntimeError("no posted news reel found")
            return Path("x.mp4"), "ஒரு செய்தி"
        env = {"PROMO_URL": "", "PROMO_KEY": "", "DASH_URL": "https://store", "DASH_WRITE_KEY": "dk"}
        with mock.patch.dict(os.environ, env), mock.patch.object(promo, "dash", dash), mock.patch.object(promo, "make_sample", make), mock.patch.dict(sys.modules, {"post": fake_post}), \
                mock.patch.object(promo, "apply_points", return_value=("புதிய தலைப்பு", "புதிய செய்தி", "colour")):
            n = promo.samples()
        return n, [c for c in calls if c[0] != "camp_feed"]

    def test_first_sample_goes_to_the_backend_not_to_e_mail(self):
        n, calls = self.run_samples([camp(status="sample_needed", pages="erode,salem")])
        self.assertEqual(n, 1)
        self.assertEqual(calls[0][0], "camp_sample")
        self.assertEqual((calls[0][1]["id"], calls[0][1]["page"], calls[0][1]["video_url"]), ("CP-1", "erode", "https://media.example/sample.mp4"))

    def test_retry_with_points_changes_the_words_then_makes_a_new_sample(self):
        _, calls = self.run_samples([camp(status="changes", owner_points="shorter title")])
        self.assertEqual([c[0] for c in calls], ["camp_update", "camp_sample"])
        self.assertEqual((calls[0][1]["title"], calls[0][1]["status"]), ("புதிய தலைப்பு", "sample_needed"))
        self.assertEqual((calls[1][1]["title"], calls[1][1]["not_applied"]), ("புதிய தலைப்பு", "colour"))

    def test_the_first_page_repository_makes_it_and_approved_ones_need_none(self):
        self.assertEqual(self.run_samples([camp(status="sample_needed", pages="salem,erode")]), (0, []))      # Salem's repository makes this one
        self.assertEqual(self.run_samples([camp(status="approved"), camp(status="sample_ready"), camp(status="rejected")]), (0, []))

    def test_a_sample_that_cannot_be_made_says_so_in_the_backend(self):
        n, calls = self.run_samples([camp(status="sample_needed")], fail=True)
        self.assertEqual(n, 0)
        self.assertEqual(calls[0][0], "camp_problem")
        self.assertIn("no posted news reel", calls[0][1]["msg"])


class TheWiring(unittest.TestCase):
    def test_posting_job_tells_the_kind_of_news_and_reads_the_store(self):
        src = (ROOT / "poster" / "post.py").read_text(encoding="utf-8")
        self.assertIn("PROMO_NOW = promo.active_for(PAGE, priority=promo.safe_bool(is_priority_news, row))", src)
        y = (ROOT / ".github" / "workflows" / "post.yml").read_text(encoding="utf-8").replace("\r\n", "\n")
        top = y[:y.index("\njobs:")]
        self.assertIn("\n  DASH_URL: ${{ secrets.DASH_URL }}", top)
        self.assertIn("\n  DASH_WRITE_KEY: ${{ secrets.DASH_WRITE_KEY }}", top)

    def test_sample_workflow_looks_at_both_sources(self):
        y = (ROOT / ".github" / "workflows" / "promo.yml").read_text(encoding="utf-8")
        for k in ("DASH_URL: ${{ secrets.DASH_URL }}", "DASH_WRITE_KEY: ${{ secrets.DASH_WRITE_KEY }}", "camp_feed", "action=promos", "python poster/promo.py samples"):
            self.assertIn(k, y)

    def test_the_posting_run_starts_the_sample_job_at_once(self):
        started = []
        with mock.patch.object(bn, "STORE", "https://store"), mock.patch.object(bn, "KEY", "k"), mock.patch.object(bn, "store", return_value={"ok": True, "waiting": 0, "open": [], "camp": 1}), \
                mock.patch.object(bn, "start_workflow", lambda name=bn.WORKFLOW: started.append(name) or True):
            self.assertEqual(bn.peek(), 0)
        self.assertEqual(started, ["promo.yml"])
        started.clear()
        with mock.patch.object(bn, "STORE", "https://store"), mock.patch.object(bn, "KEY", "k"), mock.patch.object(bn, "store", return_value={"ok": True, "waiting": 0, "open": []}), \
                mock.patch.object(bn, "start_workflow", lambda name=bn.WORKFLOW: started.append(name) or True):
            bn.peek()
        self.assertEqual(started, [])      # an older store that knows no campaigns: nothing is started

    def test_the_ad_starts_at_the_fifth_second_never_at_the_start_of_the_video(self):      # owner 29 Nov
        reel = (ROOT / "reel" / "promo360.py").read_text(encoding="utf-8")
        self.assertIn("t>=5&&t<e", reel)
        self.assertIn("cl((t-5)/0.4)", reel)
        self.assertNotIn("t>=3", reel)
        sample = (ROOT / "poster" / "promo.py").read_text(encoding="utf-8")
        self.assertIn("enable='between(t,5,{end:.2f})'", sample)      # the sample shows it exactly as the posted reels will
        self.assertNotIn("between(t,3,", sample)

    def test_the_caption_still_says_it_is_an_ad(self):
        self.assertIn("🤝 Sponsored: Sri Lakshmi Silks", promo.with_line("தலைப்பு\nசெய்தி", camp()))


if __name__ == "__main__":
    unittest.main()
