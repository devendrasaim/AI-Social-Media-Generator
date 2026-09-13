# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this project is

A Python command-line tool that turns a topic or a YouTube video into a 3-slide
Instagram carousel and publishes it. No web framework, no GUI, no dashboard —
CLI only. See [README.md](README.md) for the user-facing instructions.

## Setup

1. Secrets live in `.env` (copy from `.env.example`). **Never ask the user to
   paste API keys or passwords into the chat.** If a key is missing, tell them
   which line of `.env` to edit.
   - `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` — required; `main.py` exits if absent
   - `GEMINI_API_KEY` — optional but expected; without it, captions fall back to a
     template and images fall back to Pollinations or a plain gradient
   - `PERPLEXITY_API_KEY` — required for `--perplexity` mode (raises if missing)
   - `IMAGEN_MODEL` — optional; note `visual_engine` rewrites any value containing
     "imagen" to `gemini-2.5-flash-image`
   - `DISCORD_WEBHOOK_URL`, `SMTP_*`, `NOTIFICATION_EMAIL` — optional; the notifier
     silently no-ops when unset
2. `pip install -r requirements.txt`
3. `python setup_instagram.py` once — it solves the login challenge and writes
   `instagram_session.json`. `publisher._get_client()` **raises** if that file is
   missing; it never logs in cold.
4. Optional: put a 1080×1080 `resources/last_slide_cta.jpg` in place and the third
   slide uses it directly instead of generating one.

## Running

```
python main.py <youtube-url>                        # review prompt, then publish
python main.py --perplexity "AI tools 2026"         # topic instead of a video
python main.py --perplexity "topic" --tone casual --publish --verbose
python automate.py                                  # unattended: queue -> publish
```

Claude Code skill: `/repurpose-youtube-video <youtube-url>`

## Architecture

Pipeline: **source → captions → visuals → review → publish → log**

| File | Role |
|---|---|
| `main.py` | argparse CLI; orchestrates the whole pipeline; handles the review prompt and temp cleanup |
| `automate.py` | unattended runner: PID lock → queue refill → maintenance → pop topic → subprocess `main.py --publish` → notify |
| `core/config.py` | env vars, logging setup, all shared paths, `validate_environment()` |
| `core/content_engine.py` | `extract_youtube()`, `fetch_from_perplexity()`, `generate_captions()` |
| `core/visual_engine.py` | `VisualEngine` — composes 1080×1080 slides with Pillow |
| `core/publisher.py` | instagrapi session reuse, carousel/photo upload, CSV log |
| `core/brainstormer.py` | Gemini-generated topics when `topics_queue.txt` drops below 3 |
| `core/notifier.py` | Discord webhook + SMTP alerts |
| `core/maintenance.py` | age-based file cleanup |

**Publishing is instagrapi, not Blotato.** `BLOTATO_API_KEY` and `BLOTATO_BASE`
still sit in `config.py` but nothing reads them — there is no `blotato_client.py`.
Don't reintroduce Blotato without being asked.

## Fallback chains — always preserve these

The user's standing preference is *fallbacks over failures*. Every one of these
degrades instead of raising:

| Step | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|---|---|---|---|---|
| Captions | gemini-2.5-flash | gemini-2.0-flash | gemini-2.0-flash-lite | `_generate_template_caption()` |
| Caption JSON | `json.loads` | brace-slice repair | template caption | — |
| Images | `gemini-2.5-flash-image` | `generate_images` (Vertex) | Pollinations.ai (3 retries) | `_make_gradient_fallback()` |
| Fonts | `fonts/GoogleSans-*.ttf` | `ImageFont.load_default()` | — | — |

YouTube extraction is the one step with no fallback: transcript missing → hard error.

## Slide structure (3 slides)

Gemini is asked for exactly three: two content slides whose `key_point` must open
with a question, and a third fixed "FOLLOW FOR MORE" CTA.

## Visual layout (1080×1080 — see design.md)

- **Header 15%** (0–162px): ALL CAPS headline, Google Sans Bold 62px, purple
  `(147,51,234)` → cyan `(0,200,255)` gradient fill, centered
- **Image zone 55%** (162–756px): rounded card, 50px pad, 20px radius, blurred drop shadow
- **Body zone 30%** (756–1080px): Google Sans Medium 34px white, 1.4 line spacing;
  text before the first `?` is drawn in red `(255,60,60)`
- Background: black with 45 sine-wave "topographic" lines in `(18,18,32)`

Slides are written to `temp/_slide_N.jpg`, copied to `carousel_review/` for review,
and the temp copies are deleted after publish or cancel.

## Gotchas

- Uses the `google-genai` SDK, not the older `google-generativeai`.
- `automate.py` redefines `QUEUE_FILE`/`LOG_FILE`/`LOCK_FILE` locally, shadowing the
  `core.config` imports at the top. Change both if you move those paths.
- `run_generator.bat` contains a hardcoded path from a different machine and is broken
  as committed — the user must edit it for Task Scheduler.
- Instagram captions are hard-capped at 2200 chars; `publisher` trims on a newline.
- Windows UTF-8 stdout is patched in both `config.setup_logging()` and `automate.py`.
- `workflow.md`, `per_asst.md`, and `.claude/skills/repurpose-youtube-video/SKILL.md`
  still describe the old Blotato flow and a `repurpose.py` that no longer exists.
  Treat the code as the source of truth, not those files.

## Output

`published_posts.csv` — append-only:
`timestamp, youtube_url, platform, post_url, post_id, status`
(the `youtube_url` column also holds `perplexity:<topic>` for topic runs)
