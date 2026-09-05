# Creator Engine — Analytics & Strategy Console (Trial Build)

A Streamlit app that analyzes a creator's own historical post performance
to recommend **when**, **what format**, **how long**, and **what topic**
to post next — plus a content idea generator with a prioritization board.

This trial build runs entirely on **generated mock data** shaped to look
like realistic engagement patterns, so you can see the full experience
today without needing OAuth credentials yet.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

The app will auto-create a SQLite database at `data/creator_engine.db`
and seed it with ~180 sample posts across Instagram and YouTube on first
run. Use the "Reset & regenerate sample data" button in the sidebar to
get a fresh random sample anytime.

## Project structure

```
app.py                        # entry point, nav, sidebar
pages/
  1_Console.py                 # today's task list + top recommendation
  2_Calendar.py                 # suggested weekly posting schedule across all platforms
  2_Post_Analytics.py          # time/format/topic/financial performance charts, segmented by platform
  3_Idea_Generator.py          # generates new content ideas w/ projected outcomes
  4_Prioritization_Board.py    # impact/effort matrix + status tracking
utils/
  db.py                        # schema + connection helper (auto-migrates new columns in place)
  mock_data.py                 # realistic fake historical post generator, 5 platforms
  analysis.py                  # the "smart" logic — best time/format/topic + predict_outcome()
  calendar_engine.py            # builds the suggested weekly schedule
  idea_engine.py                # idea generation + priority scoring + projected outcomes
data/
  creator_engine.db            # created automatically on first run
```

## Platforms & format segments

Five mock-connected accounts are seeded: Instagram, YouTube, TikTok,
LinkedIn, and Facebook. Where a platform has more than one content format,
the Post Analytics page lets you drill into each segment separately:

| Platform  | Segments                          |
|-----------|------------------------------------|
| Instagram | Photos, Reels                      |
| YouTube   | Full-Length Videos, Shorts          |
| TikTok    | (single format — short video only) |
| LinkedIn  | Posts, Video                        |
| Facebook  | Posts, Video                        |

Each platform also has a *different* baked-in "best posting window" in
the mock data (e.g. Instagram peaks Tue/Thu evenings, LinkedIn peaks
weekday mornings, YouTube peaks Fri/Sat evenings) — this is intentional,
so the segmentation and calendar features have real signal to surface
per platform rather than one flat pattern repeated everywhere.

## Financial & audience-growth data

Every mock post now includes:
- **estimated_revenue** — modeled ad-revenue share + attributable
  sponsorship value (illustrative rates, not real ad-rate data — see
  `BASE_RATE_PER_1000_VIEWS` in `utils/mock_data.py` to adjust)
- **new_viewers** — reach beyond the account's existing followers
- **new_followers** — of those new viewers, how many converted to a follow

`utils/analysis.py`'s `predict_outcome()` function uses these fields to
project views/revenue/new-followers for any platform + format + time +
topic combination, based on how similar past posts performed. This
powers the numbers shown in the Idea Generator and the Weekly Calendar.

## The Weekly Calendar page

This is the "what should my week look like as a full-time creator" view.
`utils/calendar_engine.py` pulls each connected platform's own
best-performing day/time windows, pairs them with that platform's best
format + topic, and lays the result out across a 7-day tabbed view —
with a projected weekly total (views, revenue, new followers) at the top.

## How the analysis logic works

Everything in `utils/analysis.py` computes patterns **from the account's
own post history** — there's no generic "post at 7pm, everyone knows
that" advice baked in. Specifically:

- **Best time to post**: groups posts into day + 3-hour windows, ranks by
  engagement rate, and only surfaces windows with ≥3 historical posts so
  you're not trusting a fluke.
- **Best format/length**: buckets posts by type + duration, correlates
  against engagement rate and (for video) average watch retention.
- **Best topics**: same idea, grouped by content theme tag.
- **Engagement rate formula**: weighted composite of likes/comments/
  shares/saves normalized by views, weighting saves & shares higher since
  they're stronger "this mattered" signals than a like.

## Roadmap: swapping mock data for real accounts

The mock data generator (`utils/mock_data.py`) exists purely to unblock
you from OAuth setup during the trial. Nothing in `analysis.py` or
`idea_engine.py` needs to change when you wire up real data — they just
read from the `posts` table, however it got populated.

**To connect real accounts:**

1. **YouTube (start here — smoothest OAuth)**
   - Create a project in Google Cloud Console, enable the YouTube Data
     API v3, set up an OAuth consent screen + client credentials.
   - Use `google-auth-oauthlib` to handle the OAuth flow, then pull video
     stats via the API and insert rows into the `posts` table matching
     the existing schema.

2. **Instagram (Graph API)**
   - Requires the creator's account to be a Business/Creator account
     linked to a Facebook Page.
   - Standard Access works for your own connected test accounts
     immediately; going live for other users' accounts requires Meta App
     Review (business verification + screencast) before advanced
     permissions like insights work.
   - Free, but budget calendar time for the review cycle.

3. **TikTok**
   - Official Login Kit + Display API exists but is more limited for
     analytics access than YouTube/Instagram. May need a paid
     third-party API if you need deeper TikTok analytics sooner.

**Architecture note:** Streamlit isn't built to be a secure multi-tenant
OAuth app on its own (token storage, refresh, callback handling). For a
real multi-user product, put a small backend (FastAPI works well) in
front to handle the OAuth dance and token storage, with Streamlit reading
from the same database. For a single-creator trial or internal tool,
you can get away with storing tokens locally, but don't ship that as-is
to multiple external users.

## Upgrading idea generation with a real AI agent

`idea_engine.py`'s `generate_ideas()` currently recombines the creator's
own top-performing topic/format/length combos using simple templates —
zero external API calls needed for the trial.

To upgrade it: call the Anthropic API from inside that function, passing
in the same analysis summary (`top_recommendation_summary()` output) as
context, and ask Claude to propose genuinely novel content ideas grounded
in that data. The `score_priority()` function and the rest of the
pipeline (saving, status tracking, the prioritization board) don't need
to change at all — that's an intentional seam in the code.

## Known limitations in this trial build

- Mock data occasionally surfaces noisy top time-slots alongside the
  intended signal when sample sizes are small (e.g. n=3-4) — this is
  realistic behavior, and real data with more volume will sharpen it.
- Idea generation can occasionally repeat a topic/format combo in one
  batch — fine for a trial, worth de-duplicating before real use.
- Financial figures are illustrative placeholder rates, not real
  platform ad-rate data — adjust `BASE_RATE_PER_1000_VIEWS` in
  `utils/mock_data.py` once you have real numbers to calibrate against.
- The Weekly Calendar currently suggests each platform's top 1-2
  historical windows only — it doesn't yet check for scheduling
  conflicts (e.g. two platforms both suggesting Tuesday 7pm).
- No authentication/user accounts yet — this is single-tenant, meant to
  run locally for your own trial.

## Editing the mock data directly

If you'd rather hand-edit the fake data than regenerate it, you can open
`data/creator_engine.db` directly with a SQLite browser tool. In VS Code,
the **SQLTools** extension works well: add a new SQLite connection and
point it at the exact file path (get the full path by running
`(Get-Item .\data\creator_engine.db).FullName` in PowerShell, or
`realpath data/creator_engine.db` on Mac/Linux, if the file browser
dialog won't let you select it directly). Once connected, you can browse
and edit the `posts`, `accounts`, and `content_ideas` tables like a
spreadsheet. Note: clicking "Reset & regenerate sample data" in the
app's sidebar will overwrite any manual edits.
