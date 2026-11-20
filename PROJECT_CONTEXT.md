# karur360-autopost - project context

Automatic Karur-district news reels for the Instagram page **கரூர் 360** (`@karur360.official`, placeholder; hashtag `#Karur360`;
`post_to` value in the Sheet: `Karur 360`). A separate, fully independent copy of the Namakkal project `news360-autopost`:
own GitHub repository, own Google account / Sheet / Apps Script, own Instagram token, own Cloudinary account and own free API keys.
Namakkal 360 / Rasipuram 360 are never touched. Same file structure and function names as Namakkal, so Namakkal fixes can be
ported by diff. Everything runs on GitHub Actions; the Google Sheet (through the Apps Script bridge) is the working store.

**Status: live** (the `LIVE` file is present and posting runs on GitHub Actions; checked 19 Nov 2026). News is collected by `pick.yml`.
Note: this file was first copied from Coimbatore 360 - where a line below still names Coimbatore places, sources or schedules,
the code and workflow files of this repo are what actually runs.

## How it works (end to end)

```
every 2 h    research_free.yml  collect news (newspaper sites incl. Dinamalar Coimbatore page, Google/Bing News, Coimbatore searches)
                                 -> open + check each article -> only Coimbatore-district news of today/yesterday
                                 -> queue by priority (research_free/archive/queue.json)
every 20 min write_stories.yml  write each queued news by priority (free LLM chain only) -> ONE AI image of the main scene
                                 (Cloudflare FLUX schnell -> NVIDIA FLUX -> paid FAL only if both fail) -> story saved in the Sheet
                                 -> starts posting at once
every 5 min  post.yml           checks (Coimbatore only, not stale, no duplicate, daily cap 50; posts at once) -> reel (reel/reel4.py,
                                 Valluvar voice) -> Instagram (one page, no collab)
daily        insights.yml       Instagram insights -> learned topic weights (writer priority)
```

## Rules the owner decided (keep them)

| Area | Rule |
|---|---|
| News scope | Only Coimbatore-district news, published today or yesterday (Coimbatore city, Pollachi, Mettupalayam, Sulur, Annur, Valparai, Kinathukadavu, Madukkarai, Perur, Thondamuthur, Anaimalai, Karamadai ...). Tiruppur, Nilgiris, Erode, Palakkad and every other district are not ours, even when close. "Avinashi Road" is a Coimbatore city road: a headline that also names a Coimbatore place is ours |
| One page | Only கரூர் 360. No second page, no collaborator, no Rasipuram routing |
| Priority | power cut (TNEB) > crime > accident > civic > the rest |
| Never miss news | Everything eligible is queued and written; duplicates and other-district news are skipped; nothing eligible is dropped |
| Daily cap | 50 reels a day (Instagram's limit) (`DAILY_CAP` in post.yml, also in the collector / writer); urgent news first |
| Posting time | No fixed times (owner 29 Oct): every reel posts the moment it is made (`poster/config.json` `prime_time.enabled: false`) |
| Format | Reel only (no carousel) |
| Voice | **Valluvar only** (free edge-tts `ta-IN-ValluvarNeural`). Google voices are never used, even if a Google key exists |
| Follow line | Spoken: மேலும் செய்திகளுக்கு கோயம்புத்தூர் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள். Caption: கோயம்புத்தூர் செய்திகளைத் தவறவிடாமல் இருக்க Save செய்து Follow செய்யுங்கள் 📌 |
| Images | ONE new photo-realistic AI image per reel (main scene of THIS news, no text/logos); the reel uses different camera moves / crops of it. Free first: Cloudflare FLUX schnell -> NVIDIA FLUX; paid FAL `flux/schnell` -> `flux/dev` only as the last fallback. Picture check (free Gemini) as in Namakkal |
| Writing | Free LLM chain only; Claude backup OFF (`CLAUDE_MAX_CALLS=0`, no `ANTHROPIC_API_KEY`) |
| Reel language | Formal news Tamil, no slang; everyday Tamil Nadu words in voice, subtitles and cards (பஸ், டூவீலர், போலீசார், கலெக்டர் ...); dates always with the month |
| Website | Off for now (later). `poster/website.py` does nothing without `WEBSITE_INGEST_KEY`; workflows do not pass it |
| Separation | Own accounts and keys, so Namakkal's free API limits are never used; bridge e-mails tagged `KARUR360` |
| Privacy | Personal project; bot commits as `news360-bot`; no office account, office email or Claude lines in commits |

## Main files

| Path | What |
|---|---|
| `research_free/collect.py`, `allnews.py`, `sources.py` | collection, Coimbatore district checks, queue, writer, image |
| `research_free/rules.md`, `examples.json`, `names.py` | writing rules and spoken-word fixes |
| `poster/post.py` | posting checks, prime time, daily cap, Instagram publishing |
| `poster/freshness.py` | stale / duplicate / power-cut timing rules |
| `poster/config.json` | voice (Valluvar), prime time, design switches |
| `reel/reel4.py` | reel renderer (one image, camera moves, voice, opening, dates) |
| `apps_script/Code.gs` | Google Sheet bridge for the Karur 360 account (set the `..._HERE` values; redeploy after changes) |
| `tests/test_regressions.py` | regression tests (run before every push) |

## Sheet bridge (apps_script/Code.gs)

- Page key `karur`, label `கரூர் 360`, `post_to` `Karur 360`, token property `IG_TOKEN_KARUR` (refreshed weekly).
- Columns: same 31 as Namakkal; column 25 `spare_link` (unused), column 26 `coimbatore_link` (carousel link, unused while reel only),
  27 `reel_link`.
- GET actions: `queue`, `posted_rows`, `token`, `voice`, `recent`, `ping`, `autoPending`.
  POST actions: `posted`, `error`, `addStories`, `archiveNews`, `reoffer`, `setImages`, `repost`.
- E-mail subjects: `KARUR360 STORY`, `KARUR360 REEL`, `[KARUR360 IMAGES NEEDED]` ...

## Secrets (GitHub -> Settings -> Secrets -> Actions; values never in the repo)

BRIDGE_URL, BRIDGE_KEY, GEMINI_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID,
CLOUDINARY_CLOUD, CLOUDINARY_PRESET; optional MISTRAL_API_KEY, OPENROUTER_API_KEY, GH_MODELS_TOKEN, FAL_KEY (paid image fallback).
Not used: ANTHROPIC_API_KEY, GOOGLE_TTS_API_KEY, WEBSITE_INGEST_KEY. Local copies live only in `.env` (git-ignored).

## Run and check

```
python3 -m unittest discover -s tests        # regression tests (also run by tests.yml on every code push)
python3 tools/repost.py RN-158               # (Actions: repost) post a reel again after it was removed from Instagram
```

## Recent changes
<!-- recent-changes:start (updated automatically by .github/workflows/context.yml - do not edit by hand) -->
| Date | Commit | Change |
|---|---|---|
| 2026-11-20 | `869c4a3` | News reels: 360 clock branding layer (logo progress ring, opening ring, clock-hand picture change, end-card ring) |
| 2026-11-20 | `039b14d` | goldrate posted |
| 2026-11-20 | `78abb6e` | pick: written and posted |
| 2026-11-20 | `89fac98` | pick: picked news saved |
| 2026-11-20 | `99515ed` | pick: picked news saved |
| 2026-11-20 | `841da7f` | pick: list sent |
| 2026-11-20 | `9634747` | pick: written and posted |
| 2026-11-20 | `8813c60` | pick: picked news saved |
| 2026-11-20 | `6eab9e6` | pick: picked news saved |
| 2026-11-20 | `4e912ef` | pick: list sent |
| 2026-11-20 | `f1757f7` | Reel length back to the full news (at most 90 s, 70-160 words); captions always fit Instagram's 2,200 |
| 2026-11-20 | `1fda0a9` | rasipalan posted |
| 2026-11-19 | `3dc094d` | pick: written and posted |
| 2026-11-19 | `2e868fa` | pick: picked news saved |
| 2026-11-19 | `ee85632` | pick: picked news saved |
| 2026-11-19 | `696ddb8` | pick: list sent |
| 2026-11-19 | `9176f78` | Posting time first: news posts 06:00-12:00 and 15:00-21:00 IST; collection fitted to it (04:00, 08:30, 13:00, 16:30, 18:30) |
| 2026-11-19 | `c445483` | 19 Nov owner changes: reel length / wording, source first comment, 360 gold reel, posting windows, rasipalan before 9 AM |
| 2026-11-19 | `f4540e6` | powercut: notices written |
| 2026-11-19 | `8bec0d6` | powercut: notices written |
| 2026-11-19 | `2882571` | pick: written and posted |
| 2026-11-19 | `ed936fa` | pick: picked news saved |
| 2026-11-19 | `239d8c2` | pick: list sent |
| 2026-11-19 | `0f4fe2b` | pick: written and posted |
| 2026-11-19 | `756704c` | pick: picked news saved |
| 2026-11-19 | `12a979b` | pick: picked news saved |
| 2026-11-19 | `84e7059` | pick: list sent |
| 2026-11-19 | `629f22d` | rasipalan + goldrate: publish again when Instagram says 'media not ready' (9007, nothing posted - Erode 19 Nov); Cloudinary upload tried 3 times with its reason in the log (Rasipuram rasipalan posted 18:43 on 18 Nov after 3 refusals) |
| 2026-11-19 | `99ade31` | PROJECT_CONTEXT.md: wording ('<district>-district news') |
| 2026-11-19 | `7711408` | PROJECT_CONTEXT.md: page names with a space (Salem 360 style), not an underscore |
<!-- recent-changes:end -->
