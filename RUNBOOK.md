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
   ElevenLabs `creative_generate_speech` + `creative_get_flow_run_status`, WebSearch, WebFetch.
   If the FB Pages connector is not available, render everything, then stop and report it.
3. Work dir: `W=$(mktemp -d)`. Read `state/posted.json` (stories already covered).

## 1. Which window to cover
- Any run between midnight and 7 AM New York time (the 5:49 AM scheduled run, or a manual
  "Run now" test at night): cover the biggest stories from the last ~10 hours that are not in
  `state/posted.json`. Up to 3 stories for the 5-7 AM run; exactly 1 story for a run before 5 AM
  (manual test). Always publish at least 1 story in this window if any solid story exists.
- Every other run: only stories that broke or blew up in the last ~2 hours. Up to 2 stories.
- If nothing new is strong enough, publish nothing and end the run. Never force a weak story.
- Never repeat a story already in `state/posted.json` unless there is a big new development
  (then make it clearly an "UPDATE").

## 2. Finding trending stories (use several signals, prefer stories hit by 2+)
1. Google Trends US: WebFetch `https://trends.google.com/trending/rss?geo=US`
   (search interest + traffic numbers + related headlines).
2. X/Twitter US trends: WebFetch `https://trends24.in/united-states/` (look at the latest hours).
3. Google News US top stories: WebSearch "top news today" and WebFetch Google News when needed.
4. Competitor signal: recent posts on big US news pages (Fox News, CNN, NBC News, ABC News, NY Post)
   with 500+ reactions mean the topic is hot.
If Google Trends or trends24 cannot be fetched, do not stop: use WebSearch for
"Google Trends US trending now", "trending on X today US", AP/Reuters "news roundup today",
and the competitor pages instead.
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

## 5. Script and voiceover
- 60-80 spoken words (about 25-35 seconds). Simple US English, punchy, no jargon.
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

## 6. Build the story file and render
Write `$W/<slug>.json` (see the docstring at the top of `brief/render.py`). Typical scenes:
`photo` (hook + place/person) -> `stat` (key number) -> `photo` or `text` (2nd fact, ideally
with another photo) -> `text` (what's next) -> `question` (skip for tragic news) -> `cta`.
- `headline`: max ~10 words, explains the story at a glance (used on cover and image post).
- `tag`: BREAKING, UPDATE, DEVELOPING, JUST IN, or a topic like WEATHER / POLITICS / MONEY.
- `post_facts`: 2-3 short fact lines for the image post.
- slug: lowercase-dashes + `-HHMM` (NY time) so file names are unique.

    python3 brief/render.py $W/<slug>.json $W/out

Look at the cover and post images (Read them) and 2-3 video frames
(`ffmpeg -i <mp4> -vf "select='eq(n\,90)+eq(n\,400)',scale=360:-1,tile=2x1" -frames:v 1 $W/f.jpg`)
before publishing. Fix overlapping/cut text by shortening it.

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
