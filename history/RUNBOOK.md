# On This Day USA: scheduled run (3 per day)

Facebook page: On This Day USA (connector page key `onthisdayusa`).
Audience: US. All times are New York time (America/New_York).
Runs: 6:52 AM, 8:52 AM, 10:52 AM NY (all morning: "on this day" posts go stale after the day ends). Each run publishes ONE story: one vintage motion-graphics
Reel (about 35-45 sec) AND one matching image post. No asking, no waiting.

## 0. Setup (every run starts in a fresh cloud session)
1. If `/home/claude/the30sbrief-media` is missing, attach `absayyed4-design/the30sbrief-media`
   with push access and clone it there. `cd` into it and `git pull`.
2. ToolSearch-load: FB Pages connector tools (`list_pages`, `post_reel`, `set_reel_thumbnail`,
   `video_status`, `post_photo`, `list_posts`), ElevenLabs `creative_generate_speech` +
   `creative_get_flow_run_status`, WebSearch, WebFetch.
   If the FB Pages connector or the `onthisdayusa` page is missing, render the story, then stop and report it.
3. `W=$(mktemp -d)`. Read `state/history_posted.json` (stories already covered; create `[]` if missing).

## 1. Pick today's story
- Today's NY date (month + day). Candidates are US events that happened on this date in any year.
- Sources: WebFetch `https://en.wikipedia.org/wiki/<Month>_<day>` (Events section, US items),
  plus WebSearch "on this day <Month> <day> American history" (History.com, Britannica,
  Library of Congress "Today in History", National Archives).
- Never repeat an event already in `state/history_posted.json` (same event in an earlier year counts too).
- Vary across the three runs: 6:52 AM run = a big famous milestone (wars, presidents, inventions, landmarks);
  8:52 AM run = a surprising or little-known story (odd firsts, inventions, sports, culture, business);
  10:52 AM run = a human/emotional story (heroes, disasters with respect, achievements, music, movies).
  A run outside these times (manual test) picks whichever type today's log is missing.
- Avoid: graphic violence focus, partisan political takes on recent events (after 2000 keep it neutral
  and factual), anything that cannot be verified.

## 2. Facts and copyright
- Confirm every fact in 2+ reliable sources (Britannica, History.com, Library of Congress, National
  Archives, Smithsonian, NPS, Wikipedia + its cited source). Own words only; no quotes over 10 words.
- Note source names for the caption.

## 3. Photos (100% legally safe only)
- Wikimedia Commons public domain / CC0 / CC BY / CC BY-SA via `brief/commons.py`, or US government
  public domain (Library of Congress, National Archives, NASA, NPS, military).
- Old paintings, period photos and portraits of the people involved work best. Prefer 2-3 different photos.
- Collect every credit line ("Photo: <artist> / Wikimedia Commons (<license>)").

      python3 brief/commons.py search "Battle of Yorktown painting"
      python3 brief/commons.py get "File:<exact title>" $W/<name>.jpg

## 4. Script and voiceover (calm, slow, documentary)
- 55-75 spoken words (about 35-45 sec with pauses).
- Opening line ALWAYS: "On this day, in <year in words>..." then the hook. Never read the full
  date out loud (the date is shown on screen and in the caption).
- Structure: hook, 2-3 key facts (numbers, names, places), a "what happened next / why it matters"
  line, a gentle question (skip it for tragedies), then always end:
  "Follow On This Day USA... for a new story from history, every day."
- Tags: calm and serious only: [calmly] [solemnly] [softly] [thoughtfully] [gravely] [gently] [warmly].
  Never [excited], [chuckles], [laughs]. Use "..." for short pauses (1-3 per script).
- Years and numbers in words ("seventeen eighty-one", "eight thousand").
- Generate with `creative_generate_speech`: model `eleven_v4`, voice `ppLqTilh7rH7fbUVlXsf`
  (David, older documentary narrator), `generations_count: 1`. Never call it twice for one story.
  Poll `creative_get_flow_run_status`, then curl `content_url` to `$W/<slug>.mp3`.
- The prompt = the scene "text" fields joined with single spaces, in order.

## 5. Story file and render
Write `$W/<slug>.json` (see the docstring at the top of `history/render.py`):
- `date` ("October 19"), `year` (1781), `headline` (max ~8 words), `post_facts` (2-3 short lines),
  `mood` (one of: emotional, proud, tense, mysterious, hopeful, tragic, nostalgic, adventure),
  `voice_mp3`, `scenes`.
- Mood guide: wars/battles = tense; victories, independence, firsts, space = proud;
  inventions, explorations = adventure; disasters, deaths = tragic; heroes, rescues, love = emotional;
  unsolved, strange = mysterious; civil rights, recoveries, new beginnings = hopeful;
  old culture, music, movies, everyday life = nostalgic.
- Scenes: `intro` -> `photo` -> `stat` (key number) -> `photo` or `text` -> `text` (what next)
  -> `question` (skip for tragedies) -> `cta`.
- slug: `<event>-<year>` lowercase with dashes.

      python3 history/render.py $W/<slug>.json $W/out

Look at the cover and post images and 2-3 video frames before publishing
(`ffmpeg -i <mp4> -vf "select='eq(n\,90)+eq(n\,500)',scale=360:-1,tile=2x1" -frames:v 1 $W/f.jpg`).
Fix overlapping or cut text by shortening it.

## 6. Caption

    <Hook line with 1 fitting emoji> 📜

    On <Month day, year>, <2-3 sentences in own words: what happened, key numbers, what came next.>

    <Gentle question> (skip on tragedies)

    Sources: <Name>, <Name>
    <Photo credit lines>

    Follow On This Day USA for a new story from American history, every day.
    #onthisday #history #americanhistory #ushistory #todayinhistory #<3-4 story tags>

No em dashes anywhere.

## 7. Publish (page key `onthisdayusa`)
1. `python3 brief/host.py $W/out/<slug>.mp4 $W/out/<slug>-cover.jpg $W/out/<slug>-post.jpg`
2. `post_reel` (video_url, description = caption) -> video_id.
3. `set_reel_thumbnail` (video_id, cover URL).
4. `post_photo` (post image URL, same caption).
5. `video_status` once after ~60 seconds.
If a step fails, retry that step once; check `list_posts` first so nothing is posted twice.

## 8. Record and finish
Append to `state/history_posted.json`:
`{"time": "<ISO NY time>", "date": "<Month day>", "year", "slug", "headline", "mood", "reel_id", "photo_post_id"}`,
keep the last 1000, then `git add state/history_posted.json && git commit && git push`.
Final message: headline + year + reel id + photo post id.

## Hard rules
- Never reply to comments or post corrections on the page; report concerns in the final message only.
- No em dashes in on-screen text or captions.
- Never put access tokens or secrets in files, captions or logs.
