# Gentle Little Reminders: scheduled loop reel run (5 per day)

Facebook page: Gentle Little Reminders (connector page key `gentlereminders`).
Audience: US and English-speaking adults who want soft, kind self-care reminders.
Runs: 7:23 AM, 10:23 AM, 1:23 PM, 4:23 PM, 7:23 PM New York time. Each run publishes ONE
6-second seamless loop reel. NO voiceover. No asking, no waiting.

The approved look (Format "06 gentle loop"): warm watercolor-paper background, one whimsical
hand-drawn illustration in the center that gently moves (float, swing, sway, breathe or spin),
a 2-3 line quote below it in the handwritten Caveat font with one word in coral, a small
"Gentle Little Reminders" watermark, soft instrumental music. Text is static from frame 0 and
everything repeats exactly every 6 s, so viewers cannot see where the video restarts.

## 0. Setup (fresh cloud session)
1. If `/home/claude/the30sbrief-media` is missing, attach `absayyed4-design/the30sbrief-media`
   with push access and clone it there. `cd` into it and `git pull`.
2. ToolSearch-load: FB Pages tools (`list_pages`, `post_reel`, `set_reel_thumbnail`,
   `video_status`, `list_posts`), and the ElevenLabs tools for images and music
   (`creative_create_flow`, `creative_generate_image`, `creative_get_flow_run_status`). If the FB Pages connector or the `gentlereminders` page is
   missing, render the reel, commit it to `quotes/pending/`, then stop and report it.
3. `W=$(mktemp -d)`. Read `state/gentle_posted.json` (create `[]` if missing).
   If 5 or more entries already have today's NY date, stop: "Daily maximum reached".

## 1. Music (reuse the library, never generate in a daily run)
`quotes/music/` holds 20+ soft instrumental tracks made once with ElevenLabs Music
(list and prompts in `quotes/music/README.md`). Daily runs NEVER generate music.
Pick the track used least recently in `state/gentle_posted.json` (never the same track as the
previous 3 reels), and set `music_start` to a random value between 0 and (track length - 8 s)
so each reel sounds different. If the folder is empty, use `history/music/hopeful.mp3`.

## 2. The reminder (the words)
- Write an ORIGINAL short reminder in your own words. Never copy or attribute quotes to famous
  people, books, songs or other pages.
- 2 or 3 lines, max ~9 words per line, 12-24 words total. Simple, warm, kind, second person
  ("you"). One word gets the coral highlight (the heart of the message, e.g. "gentle", "rest",
  "enough", "bloom").
- Rotate themes and never repeat a theme used in the last 10 entries of `state/gentle_posted.json`:
  rest, self-kindness, slow progress, healing, letting go, small joys, hard days, growth, being
  enough, boundaries, gratitude, hope, morning calm, night calm, friendship, patience, change,
  courage, softness, self-worth.
- Nothing medical, no therapy advice, no crisis content, no politics or religion.
- Every reminder must be NEW: never reuse or lightly reword any line already in
  `state/gentle_posted.json` or in `quotes/used_lines.txt` (lines from earlier sample reels).
  Before writing, read both files and make sure the new lines say something different.

## 3. The illustration
- One new image per reel with ElevenLabs `creative_generate_image`, model `gpt-image-2.5-sunburst`,
  square, generate 1 image only (one flow per run).
- Subject matches the reminder: e.g. a girl napping on a crescent moon (rest), a small plant
  pushing through a crack (growth), a cat in a teacup (small joys), a girl reading on a cloud,
  a paper boat on calm water, a snail with a flower on its shell (slow progress), a bear holding
  a balloon. Vary subjects; avoid repeating the last 10.
- Prompt template (keep the style words exactly):
  "Whimsical children's-book illustration of <subject>, seen <angle>. Loose scribbly black ink
  linework with visible pen strokes, filled with alcohol-marker and watercolor coloring in soft
  pastel colors, slightly messy hand-drawn edges, cozy and gentle mood. Single centered subject,
  compact composition. Plain flat pure white background, no shadow, no text, no border."
- Never draw known characters, mascots, logos or real people.
- Download the image promptly (signed URLs expire) to `$W/art.png`.

## 4. Render
Motion: match the subject (floating things = float, hanging things = swing, plants/grass = sway,
sleeping or calm = breathe, round top-down things = spin). Do not use the same motion as the
previous reel.

    cat > $W/story.json   # {"slug","art","lines","highlight","motion","music","music_start"}
    python3 quotes/render_loop.py $W/story.json $W/out

slug: `<2-4-words>-<YYYYMMDD>-<HHMM>` lowercase with dashes.
Check before posting: `ffmpeg -i $W/out/<slug>.mp4 -vf "select='eq(n\,0)+eq(n\,90)+eq(n\,179)',scale=270:-1,tile=3x1" -frames:v 1 $W/f.jpg`
and Read it. The art must not touch or cover the text; text must not be cut off. If it does,
set `"art_size"` (default 820) smaller or `"art_y"` (default 820) higher and render again.

## 5. Caption

    <The reminder as one or two short sentences> <1 soft emoji: 🌼 🌙 💛 🌱 ☁️ 🌷>

    <One gentle extra line, e.g. "Save this for the days you need it." or "Send this to someone who needs it today.">

    #GentleLittleReminders #SelfCare #DailyReminder #<2-3 theme tags>

No em dashes. Keep it under 300 characters before the hashtags.

## 6. Publish (page key `gentlereminders`)
1. `python3 brief/host.py $W/out/<slug>.mp4 $W/out/<slug>-cover.jpg`
2. `post_reel` (video_url, description = caption) -> video_id.
3. `set_reel_thumbnail` (video_id, cover URL).
4. `video_status` once after ~60 seconds.
If a step fails, retry that step once; check `list_posts` first so nothing is posted twice.

## 7. Record and finish
Append to `state/gentle_posted.json`:
`{"time": "<ISO NY time>", "slug", "lines", "theme", "subject", "motion", "music", "reel_id"}`,
keep the last 1000, commit with any new music track, push.
Final message: the reminder text + reel id.

## Hard rules
- No voiceover. One reel per run, max 5 per NY day.
- Never reply to comments. Never post anything that is not an original gentle reminder.
- No em dashes. Never put tokens or secrets in files, captions or logs.
