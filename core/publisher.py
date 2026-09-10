import os
import csv
import logging
from datetime import datetime
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
from .config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

logger = logging.getLogger(__name__)

SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instagram_session.json")


def _get_client():
    """Return an authenticated instagrapi Client, reusing a cached session when possible."""
    if not os.path.exists(SESSION_FILE):
        raise RuntimeError(
            "No Instagram session file found. Run 'python setup_instagram.py' once "
            "to complete the security challenge and create a cached session."
        )

    cl = Client()
    cl.delay_range = [2, 5]

    try:
        cl.load_settings(SESSION_FILE)
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        cl.get_timeline_feed()  # verify session is alive
        logger.info("Reused existing Instagram session.")
        cl.dump_settings(SESSION_FILE)  # refresh session file
        return cl
    except (LoginRequired, ChallengeRequired) as e:
        raise RuntimeError(
            f"Instagram session expired or challenge required ({e}). "
            "Run 'python setup_instagram.py' to reauthenticate."
        )
    except Exception as e:
        raise RuntimeError(f"Instagram login failed: {e}")


def log_to_csv(log_file, youtube_url, results):
    """Append published post results to the CSV log."""
    file_exists = os.path.isfile(log_file)
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "youtube_url", "platform", "post_url", "post_id", "status"])
        for r in results:
            writer.writerow([
                datetime.now().isoformat(),
                youtube_url,
                r["platform"],
                r["post_url"],
                r["post_id"],
                r["status"],
            ])
    logger.info(f"Log updated at {log_file}")


def publish_instagram(caption_data, slide_paths):
    """Publish carousel (or single image) to Instagram via instagrapi."""
    logger.info("Starting publication process...")
    results = []

    valid_paths = [p for p in slide_paths if p and os.path.exists(p)]
    if not valid_paths:
        logger.error("No valid slide files found. Skipping publish.")
        results.append({"platform": "instagram", "post_url": "FAILED", "post_id": "N/A", "status": "No slide files"})
        return results

    # Instagram hard limit: 2200 characters
    caption = caption_data.get("caption", "")
    if len(caption) > 2200:
        logger.warning(f"Caption too long ({len(caption)} chars), trimming to 2200...")
        trimmed = caption[:2197]
        cut = trimmed.rfind("\n")
        caption = (trimmed[:cut] if cut > 1800 else trimmed) + "..."
        logger.info(f"Caption trimmed to {len(caption)} chars")

    try:
        cl = _get_client()

        if len(valid_paths) == 1:
            logger.info(f"Uploading single photo: {valid_paths[0]}")
            media = cl.photo_upload(Path(valid_paths[0]), caption=caption)
        else:
            logger.info(f"Uploading carousel with {len(valid_paths)} slides...")
            media = cl.album_upload([Path(p) for p in valid_paths], caption=caption)

        post_url = f"https://www.instagram.com/p/{media.code}/"
        post_id = str(media.pk)
        logger.info(f"Instagram post published: {post_url}")

        results.append({
            "platform": "instagram",
            "post_url": post_url,
            "post_id": post_id,
            "status": "published",
        })

    except Exception as e:
        logger.error(f"Failed to publish to Instagram: {e}")
        results.append({"platform": "instagram", "post_url": "FAILED", "post_id": "N/A", "status": str(e)})

    return results
