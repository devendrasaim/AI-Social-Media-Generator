import logging
import os
from google import genai
from google.genai import types
from .config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def brainstorm_fresh_topics(niche_description, count=5):
    """Use Gemini to generate a list of trending, evergreen topics for the given niche."""
    if not GEMINI_API_KEY:
        logger.warning("No Gemini API key found for brainstorming. Skipping refill.")
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are a social media content strategist specializing in these niches:
    {niche_description}
    
    Generate {count} specific, attention-grabbing topics for Instagram Carousel posts.
    Each topic should be:
    1.  Actionable (not "how AI works" - but "how to automate X in 5 mins").
    2.  Targeted toward creators, tech job seekers, and AI enthusiasts.
    3.  Short and punchy (one sentence each).
    
    Examples:
    - How to use ChatGPT to optimize your Resume for ATS in the USA.
    - Latest breaking updates for Claude Code and Computer Use.
    - Top 5 secrets to crack a technical interview with Gemini.

    Return only the list of topics, one per line, with no numbers, no bullet points, and no introductions.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8),
        )
        topics = [t.strip() for t in response.text.strip().split("\n") if t.strip()]
        logger.info(f"Brainstormed {len(topics)} new topics for the queue.")
        return topics
    except Exception as e:
        logger.error(f"Brainstorming failed: {e}")
        return []

def refill_queue_if_needed(queue_file, min_count=3, refill_count=7):
    """Check queue length and append fresh AI-brainstormed topics if needed."""
    if not os.path.exists(queue_file):
        # Create empty file if missing
        with open(queue_file, "w") as f: f.write("")

    with open(queue_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]

    if len(lines) < min_count:
        logger.info(f"Queue is low ({len(lines)} items). Refilling...")
        niche = "Latest AI tools (Claude, ChatGPT, Gemini), USA Job Market tips for tech seekers, and Breaking CEO news from Nvidia/OpenAI."
        new_topics = brainstorm_fresh_topics(niche, count=refill_count)
        
        if new_topics:
            with open(queue_file, "a", encoding="utf-8") as f:
                f.write("\n# Automated AI Refill\n")
                for t in new_topics:
                    f.write(f"{t}\n")
            return True
    return False
