"""owner 28 Nov: ONE common posting day for every page - normal news 06:00-13:00 and 16:00-22:00 IST, the weakest hours 13:00-16:00
left out, the best news in the best hours, and every news that is written is posted (the gap shrinks so the queue empties)."""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
import pacing  # noqa: E402
import post  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
CFG = json.loads((ROOT / "poster" / "config.json").read_text(encoding="utf-8"))
SRC = (ROOT / "poster" / "post.py").read_text(encoding="utf-8")


def at(hm, day=28):
    h, m = hm.split(":")
    return datetime(2026, 11, day, int(h), int(m), tzinfo=IST)


class CommonPostingDay(unittest.TestCase):
    def test_settings(self):
        pt = CFG["prime_time"]
        self.assertEqual(pt["windows"], [["06:00", "13:00"], ["16:00", "22:00"]])
        self.assertEqual(pt["immediate"], "priority")
        p = pt["pace"]
        self.assertTrue(p["enabled"])
        self.assertEqual(p["best"], [["08:00", "10:00"], ["18:00", "20:00"]])
        self.assertEqual((p["gap_min"], p["best_gap_min"], p["min_gap_min"], p["lead_min"], p["max_wait_hours"]), (26, 15, 5, 120, 12))
        self.assertEqual(CFG["posting"]["spacing_min"], 5)
        # 30 news a day fit: 4 best hours at 15 minutes + 9 ordinary hours at 26 minutes
        self.assertGreaterEqual(4 * 60 // p["best_gap_min"] + 9 * 60 // p["gap_min"], 30)

    def test_normal_news_waits_in_the_weakest_hours_and_at_night(self):
        row = {"headline_ta": "பள்ளி ஆண்டு விழா", "category": "கல்வி"}
        with mock.patch.object(post, "CONFIG", CFG), mock.patch.object(post, "is_priority_news", lambda r: False):
            for hm in ("06:00", "09:30", "12:59", "16:00", "19:00", "21:59"):
                self.assertEqual(post.prime_wait(row, at(hm)), "", hm)
            for hm in ("13:00", "14:30", "15:59"):
                self.assertTrue(post.prime_wait(row, at(hm)).startswith("pause: "), hm)
            for hm in ("22:00", "23:30", "02:00", "05:59"):
                self.assertTrue(post.prime_wait(row, at(hm)).startswith("night: "), hm)
        with mock.patch.object(post, "CONFIG", CFG), mock.patch.object(post, "is_priority_news", lambda r: True):
            for hm in ("14:30", "23:30", "03:00"):      # urgent news: at any hour
                self.assertEqual(post.prime_wait(row, at(hm)), "", hm)

    def test_gap_wide_in_ordinary_hours_closer_in_the_best_hours(self):
        self.assertEqual(pacing.gap(at("06:30"), 1, CFG), 26)
        self.assertEqual(pacing.gap(at("11:00"), 2, CFG), 26)
        self.assertEqual(pacing.gap(at("08:00"), 1, CFG), 15)
        self.assertEqual(pacing.gap(at("19:59"), 1, CFG), 15)
        self.assertEqual(pacing.gap(at("20:00"), 1, CFG), 26)

    def test_gap_shrinks_so_that_every_waiting_news_posts_today(self):
        self.assertEqual(pacing.minutes_left(at("06:00"), CFG["prime_time"]["windows"]), 13 * 60)
        self.assertEqual(pacing.minutes_left(at("12:00"), CFG["prime_time"]["windows"]), 60 + 360)      # the pause is not counted
        self.assertEqual(pacing.minutes_left(at("14:00"), CFG["prime_time"]["windows"]), 360)
        self.assertEqual(pacing.minutes_left(at("21:00"), CFG["prime_time"]["windows"]), 60)
        self.assertEqual(pacing.minutes_left(at("22:30"), CFG["prime_time"]["windows"]), 0)
        self.assertEqual(pacing.gap(at("21:00"), 2, CFG), 26)      # 2 news, an hour left: no hurry
        self.assertEqual(pacing.gap(at("21:00"), 6, CFG), 10)      # 6 news in the last hour: every 10 minutes
        self.assertEqual(pacing.gap(at("21:00"), 30, CFG), 5)      # never closer than 5 minutes (Instagram blocked bursts)
        self.assertEqual(pacing.gap(at("19:00"), 20, CFG), 9)      # the evening empties the queue: 180 minutes / 20 news
        for hm, n in (("06:00", 30), ("10:00", 22), ("16:00", 14), ("20:30", 8)):      # whatever waits, it fits into the rest of the day
            g = pacing.gap(at(hm), n, CFG)
            self.assertTrue(g * n <= pacing.minutes_left(at(hm), CFG["prime_time"]["windows"]) or g == 5, (hm, n, g))

    def test_switched_off_is_the_old_gap(self):
        off = json.loads(json.dumps(CFG))
        off["prime_time"]["pace"]["enabled"] = False
        self.assertEqual(pacing.gap(at("09:00"), 9, off), 5)
        self.assertEqual(pacing.order([1, 2, 3], at("07:00"), off), [1, 2, 3])
        self.assertEqual(pacing.gap(at("09:00"), 9, {"posting": {"spacing_min": 5}}), 5)
        none = json.loads(json.dumps(CFG))
        none["posting"]["spacing_min"] = 0      # owner 19 Nov: 0 = no gap at all - that still switches everything off
        self.assertEqual(pacing.gap(at("09:00"), 9, none), 0)
        self.assertEqual(pacing.order([1, 2, 3], at("07:00"), none), [1, 2, 3])

    def test_best_news_is_kept_for_the_best_hours(self):
        news = ["best", "good", "urgent", "weak"]      # as post.pick_all gives them: best first
        first = lambda r: r == "urgent"      # noqa: E731
        for hm in ("06:00", "07:59", "16:00", "17:30"):      # the 2 hours before a best block: the weaker news goes first
            self.assertEqual(pacing.order(news, at(hm), CFG, first), ["urgent", "weak", "good", "best"], hm)
        for hm in ("08:00", "09:59", "10:00", "12:00", "18:00", "19:30", "20:00", "21:30", "14:00", "23:00"):      # else: the best first
            self.assertEqual(pacing.order(news, at(hm), CFG, first), news, hm)      # exactly the order post.pick_all gave
        self.assertEqual(sorted(pacing.order(news, at("07:00"), CFG, first)), sorted(news))      # only the order changes - nothing is left out

    def test_a_news_that_waited_12_hours_goes_to_the_front(self):      # a weak news is never pushed back all day by better ones
        age = {"best": 1, "good": 13, "urgent": 0.2, "weak": 15, "new": 0.5}.get
        news = ["best", "good", "urgent", "new", "weak"]
        first = lambda r: r == "urgent"      # noqa: E731
        self.assertEqual(pacing.order(news, at("11:00"), CFG, first, age), ["urgent", "weak", "good", "best", "new"])      # the oldest first
        self.assertEqual(pacing.order(news, at("07:00"), CFG, first, age), ["urgent", "weak", "good", "new", "best"])      # lead time: then the weaker first
        self.assertEqual(pacing.order(news, at("11:00"), CFG, first), news)      # ages not known: as before

    def test_wired_into_the_posting_check(self):
        for k in ("import pacing", "spacing = pacing.gap(None, n, CONFIG)",
                  "pacing.order(pick_all(rows), None, CONFIG, lambda x: is_urgent(x) or is_priority_news(x) or is_manual(x), age_hours)",
                  "return pacing.why_outside(now, pt.get(\"windows\", []))", "minutes_since_last_post(p) < spacing",
                  "waits for the {spacing:.0f}-minute gap after the last post on"):
            self.assertIn(k, SRC, k)
        wf = (ROOT / ".github" / "workflows" / "post.yml").read_text(encoding="utf-8")
        if "waiting=" in wf:      # where the job comes back sooner for news that waits for the gap, it reads this line
            self.assertIn("waits for the [0-9]+-minute gap", wf)


class StartedByHand(unittest.TestCase):      # owner 28 Nov: "manually trigger news only immediate create and post it"
    def test_marked_only_when_the_owner_gives_the_link(self):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        self.assertIn('("manual link (started by hand) - " if art.get("manual") and not PICK_ONLY else "")', src)
        self.assertTrue(post.is_manual({"notes": "28 Nov 2026 14:10 manual link (started by hand) - free-model draft x, 1 attempt(s)"}))
        self.assertFalse(post.is_manual({"notes": "28 Nov 2026 14:10 free-model draft x, 1 attempt(s), 0 validator problem(s)"}))      # a round's own pick
        self.assertFalse(post.is_manual({"source": "https://example.com/manual-link-news", "notes": ""}))      # the link's own words do not count
        self.assertFalse(post.is_manual({}))

    def test_posts_at_once_in_the_pause_and_at_night(self):
        hand = {"headline_ta": "பள்ளி ஆண்டு விழா", "notes": "manual link (started by hand) - free-model draft"}
        auto = {"headline_ta": "பள்ளி ஆண்டு விழா", "notes": "free-model draft"}
        with mock.patch.object(post, "CONFIG", CFG), mock.patch.object(post, "is_priority_news", lambda r: False):
            for hm in ("14:00", "23:30", "03:00", "09:00"):
                self.assertEqual(post.prime_wait(hand, at(hm)), "", hm)
            self.assertTrue(post.prime_wait(auto, at("14:00")).startswith("pause: "))
        self.assertIn("if busy and not (is_urgent(r) or is_manual(r)):", SRC)      # no gap either
        self.assertEqual(pacing.order(["best", "hand", "weak"], at("07:00"), CFG, lambda r: r == "hand"), ["hand", "weak", "best"])      # always in front


class EveryWrittenNewsIsCounted(unittest.TestCase):
    def test_written_posted_waiting_and_why_not(self):
        now = datetime(2026, 11, 28, 15, 0, tzinfo=timezone.utc)
        rows = [{"story_id": f"RN-{i}", "k": k} for i, k in enumerate(("posted", "posted", "waiting", "held", "old"), 1)]
        filed = lambda r: None if r["k"] == "none" else (now - timedelta(days=2 if r["k"] == "old" else 0, hours=3))      # noqa: E731
        with mock.patch.object(post, "filed_at", filed), mock.patch.object(post, "pages_of", lambda r: ["pg"]), \
                mock.patch.object(post, "page_done", lambda r, p: r["k"] == "posted"), mock.patch.object(post, "ready", lambda r: r["k"] == "waiting"), \
                mock.patch.object(post, "skip_reason", lambda r: "held: fact-check problems - x"):
            c = post.day_count(rows, "pg", now)
        self.assertEqual((c["written"], c["posted"], c["waiting"]), (4, 2, 1))      # the 2-day-old one is not today's
        self.assertEqual(c["not_posting"], [{"id": "RN-4", "why": "held: fact-check problems - x"}])
        self.assertEqual(c["written"], c["posted"] + c["waiting"] + len(c["not_posting"]))
        self.assertIsNone(post.day_count(None, "pg", now))
        self.assertIn('"written_today": day_count(rows, pg, now)', SRC)
        self.assertIn("dashboard_status(n, rows)", SRC)
        self.assertIn('>= day_iso', SRC)      # the Facebook count of the day (it stayed 0: a date compared in another form)

    def test_youtube_takes_yesterdays_news_reel_too(self):
        yt = (ROOT / "poster" / "ytupload.py").read_text(encoding="utf-8")
        self.assertIn("youtube.pick(news, 1) or youtube.pick(late, 1)", yt)      # today's news first, then what was left from yesterday
        self.assertIn("== yday", yt)
        import ytupload
        for cap in ("நாளை மின்தடை: லால்குடி பகுதிகள்", "🔥 இன்றைய டாப் 5 | திருச்சி 360", "Power cut tomorrow"):
            self.assertTrue(ytupload.LATE_SKIP.search(cap), cap)      # a day later these are over: never uploaded late
        self.assertFalse(ytupload.LATE_SKIP.search("ஊரக மகளிருக்கு இலவச கறவை மாடு"))


if __name__ == "__main__":
    unittest.main()
