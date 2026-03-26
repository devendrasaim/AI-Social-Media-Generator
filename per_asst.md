# Personal Assistant Profile

## Who You're Working With

A builder who ships fast. Ideas come rapid-fire — your job is to translate them into working code without friction.

## Communication Style

| Signal | Meaning |
|--------|---------|
| Short messages | They know what they want. Don't ask 10 clarifying questions. |
| "do the rest" | Handle everything: code, deps, edge cases, testing. |
| Pasted terminal output | This is a bug report. Fix it. Don't explain what went wrong first. |
| "I have one idea" | They've already decided. Implement it. |
| No punctuation, casual grammar | Normal. Match their energy. Don't over-formalize. |
| "recheck everything once" | Run a full validation pass — syntax, deps, API connectivity. |
| "continue" | They interrupted something. Pick up where you left off, no recap needed. |

## Working Preferences

- **Python CLI only** — no web frameworks, no GUIs, no dashboards
- **`.env` for secrets** — never ask for API keys in chat, ever
- **Fallbacks over failures** — if something is down, work around it. Ship > perfect.
- **One question at a time** — when you must ask, ask one thing. Not a numbered list of 5.
- **Show, don't tell** — run the code, show the output. Don't describe what you're "about to do."
- **Review before publish** — they always want to see before it goes live
- **Auto-handle deps** — if something needs `pip install`, just do it

## How They Iterate

1. Describe idea (1-2 sentences)
2. Expect you to build it
3. Run it immediately
4. Paste errors if any
5. Expect fix, not explanation
6. Run again
7. Move to next idea

Average cycle time: fast. They don't take breaks between asks.

## Project Logs & Health

### Active Architecture
Modular Python CLI. Entry: `python main.py <url> --tone casual`

| File | Role |
|------|------|
| `main.py` | argparse entrypoint, orchestrates pipeline |
| `core/config.py` | env vars, logging, `IMAGEN_MODEL` constant |
| `core/content_engine.py` | YouTube/Perplexity extraction, Gemini caption (2-slide JSON) |
| `core/visual_engine.py` | Pillow slide composition (3-zone layout), catbox.moe upload |
| `core/blotato_client.py` | Blotato API wrapper (request, poll, accounts) |
| `core/publisher.py` | Instagram publish + CSV log |
| `fonts/` | GoogleSans-Bold.ttf, GoogleSans-Medium.ttf |
| `resources/` | Optional static assets (e.g. `last_slide_cta.jpg`) |
| `.env` | BLOTATO_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY, IMAGEN_MODEL |
| `published_posts.csv` | Append-only publish log |

### Current Slide Structure
- **2 slides per post** — slide 1 (content) + slide 2 (CTA)
- Gemini outputs: `slides[0]` has headline + key_point + image_prompt; `slides[1]` has only image_prompt
- CTA slide: if `resources/last_slide_cta.jpg` exists, used statically (no API call)

### Visual Layout (design.md — active)
- Header 15%: gradient headline purple→cyan, Google Sans Bold
- Image zone 55%: rounded card with drop shadow, Imagen 3 → Pollinations → gradient fallback
- Body zone 30%: key_point white, 1.4 line spacing

### Image Source Chain
1. Gemini Imagen 3 (`IMAGEN_MODEL` env var, requires billing)
2. Pollinations.ai (free, 401 in some regions — add Referer header)
3. Dark gradient fallback (always works)

### Known Gotchas
- Gemini text: 403/429/404 all skip to next model → template fallback. Never hard-crashes.
- Imagen 3: 404 if API not enabled or no billing. Falls to Pollinations automatically.
- Pollinations: 401 in some regions. Falls to gradient automatically.
- Catbox.moe: retries 3× with 3s delay. Upload failure skips that slide, pipeline continues.
- Publishing: catbox.moe AND blotato.io URLs are both trusted by publisher.
- `rounded_rectangle` (Pillow ≥ 8.2) required for card corners — in requirements.txt.

## Audit Command

Run `/per_asst_audit` to get a full project health report covering:
- Script validity & dependency check
- Run history stats (success rate, failure patterns)
- API status probes (Blotato, Gemini, Catbox, Pollinations)
- Fallback chain health
- Actionable recommendations
