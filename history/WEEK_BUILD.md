# Week build instructions (manual scheduling, nothing is posted)

You build finished "On This Day USA" reels for stories assigned to you. NOTHING is posted to
Facebook: Abdullah schedules them by hand. Repo: /home/claude/the30sbrief-media (already cloned,
do NOT git commit or push; the lead does that).

For EACH assigned story:
1. Read history/RUNBOOK.md sections 2 to 6 (facts, photos, script/voiceover, story file and
   render, caption) and follow them exactly. Ignore sections about scheduling, daily counts,
   publishing and state files.
2. Facts: confirm every number, name and date with WebSearch in 2+ reliable sources. Own words only.
3. Photos: ONLY via `python3 brief/commons.py search/get` (Wikimedia Commons free licenses or US
   government public domain). 2-3 different photos. If Commons returns 429, wait 20-60 s and retry
   (max 5 tries); never use photos from news sites. Record every credit line.
4. Voiceover: ToolSearch-load the ElevenLabs tools. `creative_generate_speech`, model `eleven_v4`,
   voice `ppLqTilh7rH7fbUVlXsf` (David), generations_count 1, called ONCE per story. Poll
   `creative_get_flow_run_status`, then curl the content_url promptly. Opening line always
   "On this day, in <year in words>..." and never read the date aloud. 55-75 spoken words.
   End with "Follow On This Day USA... for a new story from history, every day."
5. Render: `python3 history/render.py <story.json> <outdir>` with outdir
   `/home/claude/the30sbrief-media/history/week/<slug>/`. Keep only these files there:
   `<slug>.mp4`, `<slug>-cover.jpg`, `<slug>.json` (story), `caption.txt`. Delete any `-post.jpg`
   (this page is reels only). Put the voice mp3 and photos in your own temp dir, not in the repo.
6. Check: contact sheet `ffmpeg -i <mp4> -vf "fps=1/4,scale=270:-1,tile=4x3" -frames:v 1 sheet.jpg`
   and Read it, plus the cover. Fix cut or overlapping text by shortening it and re-render (re-render
   does not need a new voiceover unless the spoken text changed; if you must change spoken text,
   you may call speech ONE more time for that story).
7. caption.txt: the reel caption per RUNBOOK section 6 (hook with emoji, "On <Month day, year>, ...",
   question unless tragic, Sources line, photo credit lines, follow line, hashtags). No em dashes.

Final report per story: slug, schedule date, mp4 duration, mood, the spoken script, sources used,
and any fact you could not confirm in 2 sources (do not put unconfirmed facts in the reel).
