"""owner 28 Nov ("daily top 5 news ... verify all the pages that works or not"): on its first evening the Top 5 reel ran on none of
the 7 pages - GitHub never started its 21:00 / 21:30 schedule. The watchdog starts it, as it does for the rasipalan and gold rate."""
import datetime as d
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
import watchdog  # noqa: E402

IST = d.timezone(d.timedelta(hours=5, minutes=30))


def at(h, m):
    return d.datetime(2026, 11, 29, h, m, tzinfo=IST).astimezone(d.timezone.utc)


def decide(now, top5=False, top5_runs=(), paused=False):
    # everything else posted / nothing else due: only the Top 5 decision is looked at
    return watchdog.decide(now, True, True, [], [], "", None, pm=True, yt_runs=None, clean_runs=None, paused=paused, rep_runs=None,
                           top5=top5, top5_runs=list(top5_runs) if top5_runs is not None else None)


class TopFiveWatchdog(unittest.TestCase):
    def test_started_when_github_did_not(self):
        for h, m in ((21, 5), (21, 20), (21, 49)):
            self.assertEqual(decide(at(h, m)), ["top5.yml"], (h, m))

    def test_only_in_its_evening_time(self):
        for h, m in ((20, 59), (21, 4), (21, 50), (22, 30), (9, 0), (2, 0)):      # 21:00-21:05 is GitHub's own time; after 21:50 it is too late
            self.assertEqual(decide(at(h, m)), [], (h, m))

    def test_never_twice(self):
        self.assertEqual(decide(at(21, 20), top5=True), [])      # today's Top 5 is posted
        self.assertEqual(decide(at(21, 20), top5=None), [])      # not known (GitHub did not answer / no Top 5 job in this repo)
        self.assertEqual(decide(at(21, 20), top5_runs=[("in_progress", at(21, 1))]), [])      # GitHub's own run is working
        self.assertEqual(decide(at(21, 40), top5_runs=[("completed", at(21, 2))]), [])      # one ran 38 minutes ago
        self.assertEqual(decide(at(21, 20), top5_runs=None), [])      # unknown = busy: never start blind
        self.assertEqual(decide(at(21, 20), top5_runs=[("completed", at(5, 45))]), ["top5.yml"])      # this morning's test run does not count

    def test_not_while_instagram_has_paused_the_page(self):
        self.assertEqual(decide(at(21, 20), paused=True), [])

    def test_wired_in(self):
        src = (ROOT / "poster" / "watchdog.py").read_text(encoding="utf-8")
        for k in ('top5_runs = runs("top5.yml")', 'posted_today("poster/top5_state", "", today)', 'start(wf, "dry=0")', "top5, top5_runs)"):
            self.assertIn(k, src, k)
        wf = (ROOT / ".github" / "workflows" / "top5.yml").read_text(encoding="utf-8")
        self.assertIn("inputs.dry", wf)      # dry=0 from the watchdog = a real post
        self.assertIn('cron: "30 15 * * *"', wf)      # GitHub's own 21:00 IST start stays


if __name__ == "__main__":
    unittest.main()
