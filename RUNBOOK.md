# The 30s Brief: hourly news run

Facebook page: The 30s Brief (connector page key `the30sbrief`).
Audience: US. All times below are New York time (America/New_York).
Goal: each run finds the hottest NEW US news and publishes, for every story,
one ~30-second motion-graphics Reel AND one matching image post. No asking, no waiting.

## 0. Setup (every run starts in a fresh cloud session)
1. Repo: if `/home/claude/the30sbrief-media` is missing, attach `absayyed4-design/the30sbrief-media`
   with push access and clone it there. `cd` into it and `git pull`.
2. Load the tools you need with ToolSearch: the FB Pages connector tools
   (`list_pages`, `post_reel`, `set_reel_thumbnail`, `video_status`, `post_photo`, `list_posts`),
   ElevenLabs `creative_generate_speech` + `creative_get_flow_run_status`, WebSearch, WebFetch (article pages only, see section 2).
   If the FB Pages connector is not available, render everything, then stop and report it.
3. Work dir: `W=$(mktemp -d)`. Read `state/posted.json` (stories already covered).

## 1. Which window to cover
- Any run between midnight and 7 AM New York time (the 5:49 AM scheduled run, or a manual
  "Run now" test at night): cover the biggest stories from the last ~10 hours that are not in
  `state/posted.json`. Up to 3 stories for the 5-7 AM run; exactly 1 story for a run before 5 AM
  (manual test). Always publish at least 1 story in this window if any solid story exists.
- Every other run: stories that broke, moved or blew up in the last ~4 hours. Publish 1-2 stories.
- DAILY TARGET: at least 20 stories per New York day (5:49 AM to 11:49 PM, 19 runs).
  Count today's entries in `state/posted.json`. Pace = 20 x (runs done today / 19).
  If today's count is behind pace, publish 2 stories this run (3 if far behind).
  Every run should publish at least 1 story: if there is no big breaking story, cover the
  next-best verified US story of the day not yet posted (politics, economy, weather, crime,
  courts, tech, health, sports news with a real news angle, viral human-interest).
- Only skip a run if there is truly no verified, unposted US story from the last ~12 hours.
  Never publish anything unverified just to hit the number.
- Never repeat a story already in `state/posted.json` unless there is a big new development
  (then make it clearly an "UPDATE").

## 2. Finding trending stories (use several signals, prefer stories hit by 2+)
IMPORTANT: never WebFetch trends.google.com, trends24.in, x.com or news.google.com. Those
domains need a manual approval that nobody is there to give, so the run stalls. Use WebSearch
for all trend discovery, and WebFetch only on normal news article pages (AP, Reuters, NPR, etc.).
1. Google Trends signal: WebSearch "Google Trends US trending now today" and
   "trending searches US today".
2. X/Twitter signal: WebSearch "trending on X today US" / "trending topics twitter US today".
3. Top stories: WebSearch "top news today", "AP news today", "Reuters US news today",
   "breaking news <today's date>".
4. Competitor signal: WebSearch for what Fox News, CNN, NBC News, ABC News, NY Post are
   leading with today; a topic covered by 3+ of them is hot.
Pick stories that are US-relevant, factual, and fit motion graphics (numbers, places, people,
maps, timelines). Skip celebrity gossip with no facts, sports scores only, and anything you
cannot verify from at least 2 reliable outlets.

## 3. Research and copyright safety
- Confirm every fact in 2+ reliable sources (AP, Reuters, NPR, NYT, WSJ, WaPo, CNN, Fox, NBC, ABC,
  CBS, local outlets, official statements). Write everything in your own words. No quotes over
  10 words; never copy sentences.
- Note the outlets you used: their names go in the caption as "Sources: ..." (names only, no links needed).
- Never say something is confirmed if it is not. Use "police say", "officials said" where needed.

## 4. Photos (100% legally safe only)
- ONLY: Wikimedia Commons (public domain, CC0, CC BY, CC BY-SA) via `brief/commons.py`,
  or US government / official release photos that are public domain.
- NEVER news-site, agency (AP/Getty/Reuters/AFP) or social media photos.
- Show the named person or place on screen when they are mentioned (give that scene the photo).
- Any photo not from the actual event is labeled FILE PHOTO (`"file_photo": true`).
- Collect every credit line for the caption ("Photo: <artist> / Wikimedia Commons (<license>)").

    python3 brief/commons.py search "Lake Apopka Florida"
    python3 brief/commons.py get "File:<exact title>" $W/<name>.jpg

- PEOPLE WHO APPEAR OFTEN (Trump first): never reuse the same photo again and again. If the
  person has a folder in `library/` (`python3 brief/library.py list`), ALWAYS take their photos
  from the library with the rotating picker. It hands out the least recently used photo and
  logs the use, so every story looks different:

      python3 brief/library.py pick trump $W/trump.jpg           # one photo
      python3 brief/library.py pick trump $W/trump.jpg --n 2     # two different photos (cover + 2nd scene)

  Use the credit line it prints in the caption, and set `"file_photo": true` for these photos.
  When the same person is in several scenes of one reel, use different library photos per scene.
  For other people who keep showing up (a new library folder is worth it after ~3 stories),
  pick a Commons photo that is NOT the one used in their last story (check state/posted.json).
  Commit state/photo_usage.json together with state/posted.json at the end of the run.

## 5. Script and voiceover
- 75-95 spoken words (about 30-37 seconds). Simple US English, punchy, no jargon.
- Structure: hook line, 3-4 key facts with numbers, a "why it matters / what's next" line,
  engagement question (skip it for deaths, disasters, violence or other tragic news),
  then always end with: "Follow The 30s Brief, for your daily news in thirty seconds."
- Natural human delivery with ElevenLabs v4 audio tags matched to the story:
  [excited] [curious] [serious] [softly] [surprised] [chuckles] [dramatically] [warmly] etc.
  Laugh or chuckle only on light stories. Serious/soft tone on tragic stories. Vary it.
- Generate with `creative_generate_speech`: model `eleven_v4`, voice `aJW1epKKEUPPLZULtMRW`
  (Alex King, news narration), `generations_count: 1`. Never call it twice for one story.
  Poll `creative_get_flow_run_status`, then download `content_url` with curl to `$W/<slug>.mp3`.
- The prompt you send = the scene "text" fields joined with single spaces, in order.

## 6. Build the story file and render (TEMPLATE = Oct 17 "press secretary" reel)
The look Abdullah approved: white header bar with date and red progress line, light grid
background, a NEW visual beat every 2-4 seconds built from REAL photos, every element
popping in when the voice says it, big UPPERCASE captions. Never a frame with just one
line of text. Read the docstring at the top of `brief/render.py` (all scene types) and copy
`examples/story-template.json` as the starting point.
- 5-7 scenes per story. Start with `hero` (tag pill + photo card of the main person/place,
  name pill, subtitle, big navy + red two-line text like "OUT AFTER" / "5 DAYS").
- Then mix `cards` (1-2 photos with date pills, e.g. "OCT 9 • HIRED", optional counting badge),
  `person` (each named person gets their own photo card; add a quote card with a SHORT real
  quote or a plain label), `stamp` (photo + tilted stamp text), `bars` (comparison numbers,
  with photo thumbnails when they are people), `number` (big counting number, optional
  people-icon grid), `icons` (homes/people hit), `status` (check / search / alert),
  `time` (time card + photo), `question` (skip on tragic news), and always `cta` last.
- Every person or place mentioned gets a real photo on screen while it is spoken.
- Use the `*_at` word numbers so elements pop in on the matching word.
- `head_top` / `head_red` / `stats` (exactly 3 short stat cards) / `cover_label` drive the
  cover and the image post (same look as the original cover with WATCH IN 30 SECONDS).
- slug: lowercase-dashes + `-HHMM` (NY time).

    python3 brief/render.py $W/<slug>.json $W/out

Check it before publishing: make a contact sheet
(`ffmpeg -i <mp4> -vf "fps=1,scale=216:-1,tile=8x4" -frames:v 1 $W/sheet.jpg`) and Read it,
plus the cover and post images. Fix cut-off text, wrong timing, or a beat with no visual.
If the Commons API returns 429, wait a little and download the thumbnail directly from
upload.wikimedia.org (md5 path); the license comes from the search result.

## 7. Captions
Reel caption (also used, slightly shorter, for the image post):

    <Hook line with 1 relevant emoji>

    <2-3 sentences: what happened, key numbers, what's next. Own words.>

    <Engagement question> (skip on tragic news)

    Sources: <Outlet>, <Outlet>, <Outlet>
    <Photo credit lines>

    Follow The 30s Brief for your daily news in 30 seconds.
    #news #breakingnews #usnews #<story tags x3-5> #the30sbrief

Hashtags: mix of tags big US news pages use (#news #breakingnews #usnews #worldnews #politics
when relevant) plus 3-5 story-specific ones. No em dashes in captions.

## 8. Publish (page key `the30sbrief`)
1. `python3 brief/host.py $W/out/<slug>.mp4 $W/out/<slug>-cover.jpg $W/out/<slug>-post.jpg`
   (one call per run with ALL files of the run; it prints public URLs).
2. `post_reel` (video_url, description = reel caption) -> returns video_id.
3. `set_reel_thumbnail` (video_id, cover URL).
4. `post_photo` (image_url = post image URL, caption = image post caption).
5. `video_status` once after ~60 seconds to confirm the reel is processing/published.
If a step fails, retry that step once; do not re-post something that already went up
(check `list_posts` first).

## 9. Record and finish
Append each published story to `state/posted.json`
(`{"time": "<ISO NY time>", "slug", "headline", "keywords": [...], "reel_id", "photo_post_id"}`),
keep only the last 300 entries, then `git add state/posted.json && git commit && git push`.
Final message: one line per story (headline + reel id + photo post id), or "No new strong story this hour".

## Hard rules
- Never reply to comments or post corrections/apologies on the page. If you think an earlier
  post was wrong, say so in the run's final message only.
- No em dashes in any on-screen text or caption.
- Never put access tokens or secrets in files, captions or logs.
