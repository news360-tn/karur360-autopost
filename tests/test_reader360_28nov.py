"""owner 28 Nov: the NEWS360-TN news reader in a round window on every news reel, on every page - the owner's own 9 drawings, the
mouth chosen from the reel's voice (closed in every pause, open while the news is read). A layer over the finished page: never fails."""
import json
import math
import os
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reel"))
import clock360  # noqa: E402
import live360  # noqa: E402
import reader360  # noqa: E402

LEVEL = {f: lv for lv, fs in reader360.MOUTH.items() for f in fs}
LEVEL[reader360.BLINK] = 0


def page(total=6.0):
    D = {"shots": [{"a": 0, "b": 9, "img": 0}], "sents": [], "caps": [], "hook_end": 2.0, "end_t": total - 1, "total": total, "n": 1, "single": True}
    return ('<!doctype html><html><head><style>body{}</style></head><body><img id="plogo" src="x"><div id="pin"><span>x</span></div>'
            '<div id="hook"></div><div id="mini"></div><div class="card" id="c1"></div><div id="cap"></div><div id="end"><img src="x"></div>'
            f'<script>const D={json.dumps(D)};window.renderAt=function(t){{}};</script></body></html>')


def voice(folder, parts=((1.0, 0), (2.0, 9000), (1.0, 0), (1.5, 14000), (0.5, 0)), sr=24000, name="voice.wav"):
    """a test voice: (seconds, loudness) parts - loudness 0 is a pause; the spoken parts pulse 6 times a second like syllables"""
    frames = bytearray()
    for secs, amp in parts:
        for i in range(int(secs * sr)):
            t = i / sr
            syll = 0.55 + 0.45 * math.sin(2 * math.pi * 6 * t)
            frames += struct.pack("<h", int(amp * syll * math.sin(2 * math.pi * 180 * t)))
    with wave.open(str(Path(folder) / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))
    return Path(folder)


def cfg(**k):
    return mock.patch.object(live360, "config", lambda: dict(k))


class Reader360(unittest.TestCase):
    def setUp(self):
        os.environ.pop("REEL_READER", None)
        os.environ.pop("REEL_READER_EVERY", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.work = voice(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_nine_drawings_are_in_the_repo(self):
        fs = reader360.drawings()
        self.assertEqual([f.name for f in fs], [f"r{i}.jpg" for i in range(9)])
        for f in fs:
            self.assertEqual(f.read_bytes()[:3], b"\xff\xd8\xff", f.name)      # a JPEG picture
        self.assertEqual(sorted(f for fs_ in reader360.MOUTH.values() for f in fs_) + [reader360.BLINK], list(range(9)))      # every drawing is used

    def test_mouth_closed_in_every_pause_and_moving_while_the_news_is_read(self):
        env = reader360.loudness(self.work / "voice.wav", 6.0)
        pose = reader360.poses(env)
        self.assertGreaterEqual(len(pose), int(6.0 * reader360.FPS))
        fr = lambda a, b: pose[int(a * 30) + 3:int(b * 30) - 3]      # noqa: E731  (3 frames = 0.1 s off the edges)
        for a, b in ((0, 1.0), (3.0, 4.0), (5.5, 6.0)):      # the pauses: mouth closed (or the eyes shut for a moment)
            self.assertTrue(all(LEVEL[f] == 0 for f in fr(a, b)), (a, b))
        for a, b in ((1.0, 3.0), (4.0, 5.5)):      # the spoken parts: the mouth opens and it changes shape (it does not stay on one drawing)
            part = fr(a, b)
            self.assertGreater(sum(LEVEL[f] >= 1 for f in part) / len(part), 0.9, (a, b))
            self.assertGreaterEqual(len(set(part)), 3, (a, b))
        for i in range(0, len(pose) - 1, 2):      # one mouth shape lasts 2 frames: no flicker
            self.assertEqual(pose[i], pose[i + 1])
        self.assertTrue(all(0 <= f <= 8 for f in pose))

    def test_no_open_mouth_while_the_voice_is_silent(self):
        env = reader360.loudness(self.work / "voice.wav", 6.0)
        pose = reader360.poses(env)
        self.assertEqual([i for i, (e, f) in enumerate(zip(env, pose)) if e < 0.05 and LEVEL[f] > 1], [])

    def test_layer_added_once_with_the_nine_drawings(self):
        with cfg():
            out = reader360.add(page(), {}, self.work)
            self.assertEqual(reader360.add(out, {}, self.work), out)      # never twice
        self.assertEqual(out.count('id="rdr"'), 1)
        self.assertEqual(out.count("<img src=\"file:"), 9)
        for k in ("</style>", "</body>", "const old=window.renderAt"):
            self.assertEqual(out.count(k), 1, k)
        for k in ('<img id="plogo" src="x">', '<div id="hook"></div>', '<div id="cap"></div>'):
            self.assertIn(k, out)      # the design's own parts are untouched
        data = json.loads(out.split("const old=window.renderAt, X=")[1].split(";\n")[0])
        self.assertEqual(data["end"], 5.0)
        self.assertEqual(data["hook_end"], 2.0)
        self.assertEqual(data["size"], reader360.SIZE)
        self.assertEqual(len(data["pose"]), len(reader360.loudness(self.work / "voice.wav", 6.0)))

    def test_works_with_the_other_layers(self):
        with cfg():
            base = live360.add(clock360.add(page()), {"mini": "விபத்தில் 3 பேர் பலி", "hook": ["விபத்து", "பலி"], "location": ""})
            out = reader360.add(base, {}, self.work)
        for k in ('id="cklogo"', 'id="lvbrk"', 'id="rdr"'):
            self.assertEqual(out.count(k), 1, k)
        self.assertEqual(out.count("</style>"), 1)

    def test_inside_the_shared_safe_area(self):      # owner 28 Nov: one video for Instagram, Facebook and YouTube Shorts
        for k in ("#rdr{position:absolute;left:48px", "border-radius:50%", "capTop=1600", "if(s<0.6)s=0", "bottomOf($('hook'))", "bottomOf($('sum'))",
                  "base=y+24", "t>=X.hook_end"):      # the last one: he comes in only after the big headline
            self.assertIn(k, reader360.CSS + reader360.JS, k)
        self.assertLessEqual(48 + reader360.SIZE, 950)

    def test_window_shows_head_and_shoulders(self):      # owner 28 Nov evening: the face bigger, the mouth easy to see
        cx, cy, r = reader360.CROP
        self.assertTrue(r <= cx <= reader360.PIC - r and r <= cy <= reader360.PIC - r)      # the shown circle is inside the drawing
        self.assertTrue(cx - r < 120 and cx + r > 255 and cy - r < 60 and cy + r > 300)      # hair to mic: the whole face and the NEWS360-TN mic
        self.assertGreaterEqual(reader360.PIC / (2 * r), 1.4)      # at least 1.4 times closer than the whole drawing
        k = reader360.SIZE / (2 * r)
        self.assertIn("left:%.1fpx;top:%.1fpx;width:%.1fpx" % (-(cx - r) * k, -(cy - r) * k, reader360.PIC * k), reader360.CSS)

    def test_never_fails_the_reel(self):
        with cfg():
            for bad in ("", None, "<html></html>", page().replace("const D=", "const E="), page().replace('id="cap"', 'id="x"'),
                        page().replace("</style>", "</style><style></style>"), page().replace("</body>", '<div id="fxloop"></div></body>')):
                self.assertEqual(reader360.add(bad, {}, self.work), bad)
            empty = tempfile.TemporaryDirectory()
            self.assertEqual(reader360.add(page(), {}, empty.name), page())      # no voice file
            voice(empty.name, parts=((2.0, 0),))
            self.assertEqual(reader360.add(page(), {}, empty.name), page())      # a silent voice file: no silent reader
            empty.cleanup()
            self.assertEqual(reader360.add(page(), {}, None), page())
            with mock.patch.object(reader360, "drawings", lambda: []):
                self.assertEqual(reader360.add(page(), {}, self.work), page())      # a drawing is missing

    def test_switches(self):
        with cfg(reel_reader=False):
            self.assertEqual(reader360.add(page(), {}, self.work), page())
        death = {"mini": "விபத்தில் 3 பேர் பலி", "hook": ["விபத்து", "பலி"]}
        for c in (cfg(), cfg(reel_reader_serious=False)):      # owner 28 Nov evening: the smiling reader is left out of news about a death
            with c:
                self.assertEqual(reader360.add(page(), death, self.work), page())
                self.assertIn('id="rdr"', reader360.add(page(), {"mini": "பள்ளி ஆண்டு விழா"}, self.work))
        with cfg(reel_reader_serious=True):
            self.assertIn('id="rdr"', reader360.add(page(), death, self.work))      # the switch shows him there too

    def test_on_a_few_news_only(self):      # owner 28 Nov night: "use few news only, do not use all the news"
        os.environ.pop("REEL_READER_EVERY", None)
        self.assertEqual(reader360.EVERY, 4)
        with cfg():
            shown = [n for n in range(200, 220) if 'id="rdr"' in reader360.add(page(), {"story": f"RN-{n}", "mini": "பள்ளி விழா"}, self.work)]
        self.assertEqual(shown, [200, 204, 208, 212, 216])      # 1 reel in 4, always the same stories
        with cfg(reel_reader_every=1):
            self.assertIn('id="rdr"', reader360.add(page(), {"story": "RN-201"}, self.work))      # 1 = every news
        with cfg(reel_reader_every=2):
            self.assertIn('id="rdr"', reader360.add(page(), {"story": "RN-202"}, self.work))
            self.assertEqual(reader360.add(page(), {"story": "RN-203"}, self.work), page())
        os.environ["REEL_READER_EVERY"] = "1"      # a test run can show him on any story
        with cfg():
            self.assertIn('id="rdr"', reader360.add(page(), {"story": "RN-203"}, self.work))
        os.environ.pop("REEL_READER_EVERY")
        self.assertTrue(reader360.turn({}, 4) and reader360.turn({"story": "x"}, 4))      # no story number: he is shown

    def test_small_round_window(self):      # owner 28 Nov night: "small size is okay ... reduce the size also that circular"
        self.assertLessEqual(reader360.SIZE, 200)
        self.assertIn("border-radius:50%", reader360.CSS)
        self.assertIn(f"width:{reader360.SIZE}px;height:{reader360.SIZE}px", reader360.CSS)
        os.environ["REEL_READER"] = "0"
        with cfg():
            self.assertEqual(reader360.add(page(), {}, self.work), page())
        os.environ.pop("REEL_READER")

    def test_reel_uses_it(self):
        src = (ROOT / "reel" / "reel4.py").read_text(encoding="utf-8")
        self.assertIn("import reader360", src)
        self.assertIn("reader360.add(live360.add(clock360.add(new_page or build_html(spec, shots, sents, caps, hook_end, end_t, total, R.PAGE)), spec), spec, work)", src)


if __name__ == "__main__":
    unittest.main()
