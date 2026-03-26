# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

1. Add API keys to `.env` (never ask for keys in chat):
   - `BLOTATO_API_KEY` — required, from [Blotato dashboard](https://app.blotato.com)
   - `GEMINI_API_KEY` — optional (template captions if missing), from [Google AI Studio](https://aistudio.google.com)
   - `PERPLEXITY_API_KEY` — required only for `--perplexity` mode
   - `IMAGEN_MODEL` — optional, defaults to `imagen-4.0-generate-001`
2. Install dependencies: `pip install -r requirements.txt`
3. Optional: place `resources/last_slide_cta.jpg` (1080×1080) to use a static CTA slide instead of generating one

## Running

```
python main.py <youtube-url> --tone casual
python main.py --perplexity "AI tools 2026" --tone casual
python main.py <youtube-url> --tone casual --publish   # skip review prompt
```

Claude Code skill: `/repurpose-youtube-video <youtube-url>`

## Architecture

Modular pipeline in `core/`: Extract → Captions → Visuals → Review → Publish → Log

| Module | Role |
|--------|------|
| `main.py` | argparse CLI entrypoint |
| `core/config.py` | env vars, logging, constants |
| `core/blotato_client.py` | Blotato API wrapper (request, poll, accounts) |
| `core/content_engine.py` | YouTube/Perplexity extraction + Gemini caption generation |
| `core/visual_engine.py` | Pillow slide composition + catbox.moe upload |
| `core/publisher.py` | Instagram publishing + CSV logging |

Fallback chains — always preserve:

| Step | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|------|---------|------------|------------|------------|
| Extract | Blotato `/source-resolutions-v3` | youtube-transcript-api + oEmbed | — | — |
| Captions | gemini-2.5-flash | gemini-2.0-flash | gemini-2.0-flash-lite | Template-based |
| Visuals | Gemini Imagen 3 | Pollinations.ai | Dark gradient (Pillow) | — |
| Publish | Blotato `/posts` | — | — | — |

## Slide Structure (2 slides per post)

- **Slide 1** — content: Gemini headline + key point + concept image
- **Slide 2** — CTA: bold scroll-stopping image + "Follow @myaiguru9 for more AI tips"
  - If `resources/last_slide_cta.jpg` exists, it is used directly (saves API tokens)

## Visual Layout (1080×1080 — design.md)

- **Header 15%** (0–162px): ALL CAPS headline, Google Sans Bold, purple→cyan gradient fill
- **Image zone 55%** (162–756px): AI image as rounded card (50px pad, 20px corners, drop shadow)
- **Body zone 30%** (756–1080px): key_point text, white, Google Sans Medium, 1.4 line spacing

Fonts: `fonts/GoogleSans-Bold.ttf`, `fonts/GoogleSans-Medium.ttf` (fallback: PIL default)

## Blotato API Quirks

- Base URL: `https://backend.blotato.com/v2`, auth header: `blotato-api-key`
- Responses wrapped in `{"item": {...}}` — always unwrap via `data.get("item", data)`
- Post ID: try `postSubmissionId` first, fallback to `id`
- Publishing works with Blotato-hosted URLs **and** catbox.moe URLs

## Gemini API

- Uses `google-genai` SDK (not the older `google-generativeai`)
- Text: model fallback chain (2.5-flash → 2.0-flash → 2.0-flash-lite) handles 429/403/404
- Images: `IMAGEN_MODEL` env var (default `imagen-4.0-generate-001`), requires billing or API access

## Output

`published_posts.csv` — append-only log: `timestamp, youtube_url, platform, post_url, post_id, status`
