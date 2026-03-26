import json
import random
import urllib.parse
import logging
import requests
from google import genai
from google.genai import types
from .config import GEMINI_API_KEY, PERPLEXITY_API_KEY, PERPLEXITY_BASE
from .blotato_client import request_api, poll_until_done

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# YouTube Extraction (with fallback)
# ──────────────────────────────────────────────

def _normalize_youtube_url(url):
    """Normalize YouTube URL to standard format. Returns (url, video_id)."""
    parsed = urllib.parse.urlparse(url)
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://www.youtube.com/watch?v={video_id}", video_id
    params = urllib.parse.parse_qs(parsed.query)
    video_id = params.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}", video_id
    return url, None


def _extract_via_blotato(url):
    """Try extracting content via Blotato API."""
    data = request_api("POST", "/source-resolutions-v3", {
        "source": {"sourceType": "youtube", "url": url}
    })
    submission_id = data["id"]
    logger.debug(f"Submission ID: {submission_id}")

    result = poll_until_done(
        f"/source-resolutions-v3/{submission_id}",
        done_statuses=["completed"],
    )
    title = result.get("title", "")
    content = result.get("content", "")
    if not content:
        msg = result.get("message", "No content extracted")
        raise RuntimeError(f"Blotato returned no content: {msg}")
    return {"title": title, "content": content}


def _extract_via_transcript(video_id, url):
    """Fallback: extract transcript directly using youtube-transcript-api."""
    from youtube_transcript_api import YouTubeTranscriptApi
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id)
    content = " ".join([t.text for t in transcript])
    if not content:
        raise RuntimeError("Transcript is empty")

    # Get title via oEmbed (free, no API key)
    title = ""
    try:
        oembed = requests.get(
            f"https://www.youtube.com/oembed?url={url}&format=json", timeout=10
        ).json()
        title = oembed.get("title", "")
    except Exception:
        pass

    return {"title": title or "Untitled Video", "content": content}


def extract_youtube(url):
    """Extract video content — tries Blotato first, then direct transcript."""
    logger.info("Extracting content from YouTube video...")
    url, video_id = _normalize_youtube_url(url)
    logger.info(f"URL: {url}")

    # Try Blotato first
    logger.info("Trying Blotato extraction...")
    try:
        result = _extract_via_blotato(url)
        logger.info(f"Done! (Blotato) Title: {result['title'][:60]}")
        return result
    except Exception as e:
        logger.warning(f"Blotato failed: {e}")

    # Fallback: direct transcript extraction
    if video_id:
        logger.info("Trying direct transcript extraction...")
        try:
            result = _extract_via_transcript(video_id, url)
            logger.info(f"Done! (Direct) Title: {result['title'][:60]}")
            return result
        except Exception as e:
            logger.warning(f"Direct extraction also failed: {e}")

    raise RuntimeError("Could not extract content from this YouTube video.")


# ──────────────────────────────────────────────
# Perplexity Content Source
# ──────────────────────────────────────────────

def fetch_from_perplexity(topic="recent AI tools and productivity tips for creators"):
    """Query Perplexity's sonar model for fresh, web-searched content on a topic."""
    if not PERPLEXITY_API_KEY:
        raise RuntimeError(
            "PERPLEXITY_API_KEY not set. Add it to your .env file "
            "(get one at https://www.perplexity.ai/settings/api)"
        )

    logger.info(f"Querying Perplexity for: {topic}")

    query = (
        f"Give me a detailed, factual breakdown of the most recent and valuable {topic}. "
        f"Focus on specific tools, techniques, or insights that are genuinely useful to Instagram "
        f"audiences interested in AI and productivity. Include concrete examples, use cases, and "
        f"actionable tips. Be specific — name actual tools, features, or updates from the past week."
    )

    resp = requests.post(
        f"{PERPLEXITY_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar",
            "messages": [{"role": "user", "content": query}],
            "return_citations": True,
        },
        timeout=30,
    )

    if not resp.ok:
        raise RuntimeError(f"Perplexity API error ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # Extract citations as a source reference line
    citations = data.get("citations", [])
    if citations:
        sources = " | ".join(citations[:3])
        content += f"\n\nSources: {sources}"

    title = f"Latest {topic.title()}"
    logger.info(f"Perplexity returned {len(content)} chars of content")
    return {"title": title, "content": content}


# ──────────────────────────────────────────────
# Caption Generation (with model chain + template fallback)
# ──────────────────────────────────────────────

def _generate_template_caption(title, content, tone):
    """Generate captions without AI when Gemini quota is exhausted."""
    words = content.split()
    summary = " ".join(words[:200]) if len(words) > 200 else content
    for end_char in [".", "!", "?"]:
        idx = summary.rfind(end_char)
        if idx > 100:
            summary = summary[:idx + 1]
            break

    hooks = [
        "This changed how I think about everything.",
        "Most people don't know this yet.",
        "Here's what nobody's talking about.",
        "Save this for later.",
        "This is worth your time.",
    ]
    hook = random.choice(hooks)

    title_words = [w.strip(".,!?:;'\"").lower() for w in title.split() if len(w) > 3]
    hashtags = ["#" + w for w in title_words[:3]]
    hashtags.extend(["#viral", "#mustwatch"])

    # Build carousel-style output with 2 slides
    caption = f"{hook}\n\n{title}\n\n{summary[:500]}\n\n{' '.join(hashtags[:5])}"

    logger.info("Done! Template-based caption generated.")
    return {
        "slides": [
            {"headline": title.upper()[:80], "key_point": "", "image_prompt": f"A person using {title.lower()} in a modern office, cinematic lighting, professional gear"},
            {"headline": "KEY FEATURES", "key_point": summary[:100], "image_prompt": f"A professional workspace with {title.lower()} visible on a high-end screen"},
            {"headline": "FOLLOW FOR MORE", "key_point": "Get the latest AI tips daily", "image_prompt": "vibrant abstract AI pattern, neon colors"}
        ],
        "hashtags": hashtags[:5],
        "caption": caption,
        "image_prompt": f"{title}, {tone} style",
    }


def generate_captions(title, content, tone):
    """Generate platform-optimized carousel data using Gemini, with fallbacks."""
    logger.info(f"Generating Instagram carousel data (Tone: {tone})...")

    if not GEMINI_API_KEY:
        logger.info("No Gemini API key — using template-based caption.")
        return _generate_template_caption(title, content, tone)

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    Repurpose the following YouTube video content into a high-retention Instagram Carousel post.
    The tone should be {tone}. Act as an engaging "Social Speaker" who is mysterious, questioning, and holds the audience's attention with storytelling.
 
    CRITICAL INSTRUCTIONS:
    1. Write a compelling Instagram caption (max 1800 characters total) that:
       - Opens with a mysterious hook that makes people stop scrolling.
       - Summarizes information as if you are telling an interesting story.
       - Uses line breaks and emojis for readability.
       - Ends with a call-to-action.
    2. Create exactly 3 slides:
       SLIDE 1 (Informative):
       - 'headline': A punchy, short, all-caps headline (max 8 words).
       - 'key_point': MUST start with a "Do you know..." question (ending with a ?) that hooks the user, immediately followed by 1-2 sentences of factual answer.
       - 'image_prompt': Cinematic real-world action scene.
       SLIDE 2 (Informative):
       - 'headline': A punchy headline different from Slide 1.
       - 'key_point': MUST also start with a mysterious question (ending with a ?) about a new fact, followed by 1-2 sentences of answer.
       - 'image_prompt': Different cinematic action scene.
       SLIDE 3 (CTA):
       - 'headline': "FOLLOW FOR MORE"
       - 'key_point': "Get daily AI insights & productivity tips"
       - 'image_prompt': High-energy abstract visual.
    3. Generate exactly 5 relevant hashtags about the VIDEO'S TOPIC.

    You MUST return the output as a clean JSON object with this exact structure:
    {{
      "caption": "The full Instagram caption text here",
      "slides": [
        {{"headline": "HEADLINE 1", "key_point": "INSIGHT 1", "image_prompt": "ACTION PHOTO 1"}},
        {{"headline": "HEADLINE 2", "key_point": "INSIGHT 2", "image_prompt": "ACTION PHOTO 2"}},
        {{"headline": "FOLLOW FOR MORE", "key_point": "CTA TEXT", "image_prompt": "VIVID VISUAL"}}
      ],
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
    }}

    Video Title: {title}
    Video Content: {content[:8000]}
    """

    # Try models in order — each has its own separate free tier quota
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    response = None
    for model_name in models:
        try:
            logger.info(f"Using model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7),
            )
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                logger.warning(f"{model_name} quota exhausted, trying next model...")
                continue
            elif "404" in err_str or "NOT_FOUND" in err_str:
                logger.warning(f"{model_name} not available, trying next model...")
                continue
            elif "403" in err_str or "PERMISSION_DENIED" in err_str:
                logger.warning(f"{model_name} permission denied (API not enabled or invalid key), trying next model...")
                continue
            else:
                raise

    if response is None:
        logger.warning("All Gemini models exhausted. Using template-based caption...")
        return _generate_template_caption(title, content, tone)

    text = response.text.strip()
    # JSON cleanup in case of markdown wrapping
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        if text.endswith("```"):
            text = text[:-3]

    text = text.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed ({e}), attempting repair...")
        # Try to extract JSON object from the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
            except json.JSONDecodeError:
                logger.warning("JSON repair failed. Falling back to template caption.")
                return _generate_template_caption(title, content, tone)
        else:
            logger.warning("No JSON found in response. Falling back to template caption.")
            return _generate_template_caption(title, content, tone)

    logger.info(f"Generated {len(result.get('slides', []))} carousel slides.")
    return result
