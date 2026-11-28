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
| Priority | owner 27 Nov: by this page's Instagram views per topic (research_free/learned.json); urgent = an upcoming power cut (first) or a topic whose reels often pass 10,000 views (1 in 5) |
| Never miss news | Everything eligible is queued and written; duplicates and other-district news are skipped; nothing eligible is dropped |
| Daily cap | owner 27 Nov: 30 news a day per page on Instagram, Facebook and YouTube each (IST day; rasipalan / gold rate extra); after 30 only urgent news |
| YouTube hashtags | owner 28 Nov: 40 hashtags on every YouTube Short (YouTube allows 60) - 25 for the video (from its own keyword line; sensitive news gets general tags only), 5 for the page, 5 for the district, 5 for the area of the news (poster/yt_hashtags.py). The first line stays `#<Page> #TamilNews #Shorts`; title, hidden Tags, Instagram and Facebook are not changed. Switch off: config.json `"youtube_hashtags": false` |
| Add news (backend) | owner 28 Nov: a news typed in the News360 Backend ("Add news": content, extra details, follow-up of an earlier post, link, picture, note with extra instructions) is taken within 5-10 minutes (research_free/backend_news.py, backend_news.yml), written by the usual writer chain, and posted on Instagram, Facebook and YouTube through every usual check. Only the logins in the store setting DASH_POSTERS may add news. A follow-up is never held as a duplicate of the news it continues; the owner's own words are not fact-checked against a link |
| Campaigns (backend) | owner 28 Nov: a sponsor's ad in the bottom space of news reels, added in the News360 Backend ("Campaigns": sponsor, title, message, picture, pages, start / end date, every news or a number a day or a number in total, normal / priority / all news, notes). A SAMPLE reel is made first (poster/promo.py samples, promo.yml) and shown in the backend; the ad reaches posted reels ONLY after the owner presses Approve there. Reject, or Retry sample with points. A second source beside the Google Form promotions; caption says "Sponsored: name" |
| Posting time | owner 27 Nov: 06:00-22:00 IST every reel posts as soon as it is ready; 22:00-06:00 only urgent news. News is collected every 2 hours |
| Errors and blocks | owner 27 Nov: after an error 5 tries 10 minutes apart, then 1 try 1 hour later, then Hold - never retried at once; a temporary block waits the time the platform states, else 2 hours (owner 28 Nov: a Facebook block with no stated time waits 24 hours - retrying every 2 hours kept five pages blocked). No manual work for the owner (config.json owner_emails false) |
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
| 2026-11-28 | `d61907f` | tests: the parrot layout test reads its numbers from the file itself (the test machine has no numpy, so the reel file cannot be imported there) |
| 2026-11-28 | `0489256` | stories shared / Instagram pause |
| 2026-11-28 | `b7dd46f` | parrot rasipalan reel: the whole scene fits the area that is free on Instagram, Facebook and YouTube Shorts (owner 28 Nov) - the row of 12 cards the parrot picks from was at y 1650-1800, under the caption, and the page name under the top bar; the scene is drawn a little smaller and lower, positions unchanged |
| 2026-11-28 | `bb9076e` | stories shared / Instagram pause |
| 2026-11-28 | `9e8c84a` | stories shared / Instagram pause |
| 2026-11-28 | `a33a8bc` | stories shared / Instagram pause |
| 2026-11-28 | `d21b40d` | posting: one common posting day for every page (owner 28 Nov) - normal news 06:00-13:00 and 16:00-22:00 IST, the weakest hours 13:00-16:00 left out (time-sensitive and urgent news still post), the best news kept for 08:00-10:00 and 18:00-20:00, and the gap shrinks so every written news posts the same day; a news that waited 12 hours goes first; a news the owner starts by hand posts at once. YouTube also takes a news reel left from yesterday; the dashboard shows written / posted / waiting / not posting with the reason (the Facebook count stayed 0). Top 5: the watchdog starts it when GitHub does not (it ran on no page on its first evening). News reader: a small circle on 1 news in 4, after the headline, not on news about a death |
| 2026-11-28 | `eadc071` | stories shared / Instagram pause |
| 2026-11-28 | `0c0414b` | stories shared / Instagram pause |
| 2026-11-28 | `fe6e028` | stories shared / Instagram pause |
| 2026-11-28 | `06f3525` | stories shared / Instagram pause |
| 2026-11-28 | `5082c77` | stories shared / Instagram pause |
| 2026-11-28 | `66990be` | stories shared / Instagram pause |
| 2026-11-28 | `8f60102` | stories shared / Instagram pause |
| 2026-11-28 | `4e0861e` | stories shared / Instagram pause |
| 2026-11-28 | `7feaeed` | stories shared / Instagram pause |
| 2026-11-28 | `a10ffd8` | stories shared / Instagram pause |
| 2026-11-28 | `26816a7` | stories shared / Instagram pause |
| 2026-11-28 | `c0bf1bf` | stories shared / Instagram pause |
| 2026-11-28 | `1c38a98` | stories shared / Instagram pause |
| 2026-11-28 | `e1f9095` | stories shared / Instagram pause |
| 2026-11-28 | `775d945` | stories shared / Instagram pause |
| 2026-11-28 | `8e90467` | stories shared / Instagram pause |
| 2026-11-28 | `f79fa94` | stories shared / Instagram pause |
| 2026-11-28 | `931b940` | stories shared / Instagram pause |
| 2026-11-28 | `9f300e9` | stories shared / Instagram pause |
| 2026-11-28 | `9468123` | Backend Add news (owner 28 Nov): a news typed in the News360 Backend - content, extra details, follow-up, link, picture, note with instructions, format reel / post / carousel - is taken by the page job, written by the usual writer and posted through every usual check; only DASH_POSTERS logins may add |
| 2026-11-28 | `8e71f92` | stories shared / Instagram pause |
| 2026-11-28 | `8df5c43` | stories shared / Instagram pause |
| 2026-11-28 | `25a7fc0` | stories shared / Instagram pause |
<!-- recent-changes:end -->
