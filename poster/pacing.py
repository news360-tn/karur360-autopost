"""owner 28 Nov ("i needed the common for all best time only, very worst time only ignore" / "creating all the video must post"):
ONE posting day for every page, and every news that is written is posted.

  06:00-13:00 and 16:00-22:00 IST   normal news posts (poster/config.json prime_time.windows)
  13:00-16:00                       the weakest hours of the pages' own views: only urgent news posts; the others are made ready
  08:00-10:00 and 18:00-20:00       the best hours (prime_time.pace.best): news goes out closer together, the best news first

Nothing waits for "a best time" and can then be missed. A news reel is posted at every turn; only two things change with the clock:
  * the gap between two normal news reels (gap): wide in the ordinary hours, closer in the best hours - and never wider than what
    still lets EVERY waiting news go out before the posting day ends. With many news waiting and little time left the gap shrinks
    down to min_gap_min, so the evening empties the queue (the "sweep") instead of leaving news for a tomorrow it may not have.
  * the order (order): in the lead_min minutes before a best block the weaker news goes first, so the best news is still there
    when the block opens; at every other time the best news goes first, as before. Urgent news is always first, at any hour.

Numbers come from prime_time.pace; with "enabled": false (or no pace block) posting is exactly as before (posting.spacing_min)."""
import os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def pace(config):
    """the pace settings, {} when switched off: "enabled": false, or posting.spacing_min 0 ("no gap at all", owner 19 Nov)"""
    p = ((config or {}).get("prime_time") or {}).get("pace") or {}
    if float(((config or {}).get("posting") or {}).get("spacing_min", 12)) <= 0:
        return {}
    return p if p.get("enabled") else {}


def _m(hm):
    h, m = str(hm).split(":")
    return int(h) * 60 + int(m)


def _now_m(now):
    if now is None and os.environ.get("PACING_CLOCK"):      # tests only: run the whole suite as if it were this IST time ("07:00")
        return _m(os.environ["PACING_CLOCK"])
    now = now or datetime.now(IST)
    return now.hour * 60 + now.minute


def inside(now, blocks):
    """is the IST clock inside one of the [["HH:MM", "HH:MM"], ...] blocks"""
    t = _now_m(now)
    return any(_m(a) <= t < _m(b) for a, b in blocks or [])


def minutes_left(now, windows):
    """posting minutes left today, from now to the end of the last window (the hours between two windows are not counted)"""
    t = _now_m(now)
    return sum(max(0, _m(b) - max(t, _m(a))) for a, b in windows or [])


def gap(now, waiting, config):
    """minutes that must lie between two normal news reels of a page right now"""
    cfg = config or {}
    p = pace(cfg)
    old = float((cfg.get("posting") or {}).get("spacing_min", 12))
    if not p:
        return old
    lowest = float(p.get("min_gap_min", old))
    g = float(p.get("best_gap_min", 15)) if inside(now, p.get("best")) else float(p.get("gap_min", 26))
    left = minutes_left(now, (cfg.get("prime_time") or {}).get("windows"))
    if waiting and left > 0:      # every waiting news must still fit into the rest of the posting day
        g = min(g, left / float(waiting))
    return max(lowest, g)


def lead(now, config):
    """True in the minutes before a best block opens (the weaker news goes first then)"""
    p = pace(config)
    if not p or inside(now, p.get("best")):
        return False
    t, n = _now_m(now), float(p.get("lead_min", 120))
    return any(0 < _m(a) - t <= n for a, _ in p.get("best") or [])


def order(stories, now, config, first=lambda r: False, age=None):
    """the ready news in the order they are tried now. `stories` comes best first (post.pick_all); `first(r)` marks urgent news,
    which always stays in front. In the lead time before a best block the other news is turned round: the weakest goes now, the
    best is kept for the block. A news that has waited max_wait_hours (`age(r)` = hours since it was written) goes right after
    the urgent ones, the oldest first - a weak news is never pushed back all day by better ones.
    Nothing is left out - the list only changes its order."""
    stories = list(stories)
    p = pace(config)
    if not p:
        return stories
    late = float(p.get("max_wait_hours", 12))
    front = [r for r in stories if first(r)]
    rest = [r for r in stories if not first(r)]
    old = sorted((r for r in rest if age and (age(r) or 0) >= late), key=lambda r: -(age(r) or 0))
    if not old and not lead(now, config):
        return stories      # the usual case: exactly the order post.pick_all gave
    rest = [r for r in rest if r not in old]
    return front + old + (rest[::-1] if lead(now, config) else rest)


def between(now, windows):
    """True in the daytime pause: after the first window opened and before the last one closes, but inside none of them"""
    ws = sorted(windows or [])
    t = _now_m(now)
    return bool(ws) and _m(ws[0][0]) <= t < _m(ws[-1][1]) and not inside(now, ws)


def why_outside(now, windows):
    """the words for a normal news that waits outside the posting hours: 'night' or, between two windows, 'pause'"""
    ws = sorted(windows or [])
    spans = " / ".join(f"{a}-{b}" for a, b in ws)
    if between(now, ws):
        return f"pause: these are the weakest hours - only urgent news posts outside {spans} IST (owner 28 Nov); it is made ready and posts when the pause ends"
    return f"night: only urgent news posts outside {spans} IST (owner 27 Nov)"
