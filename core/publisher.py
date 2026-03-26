import os
import csv
import logging
from datetime import datetime
from .blotato_client import request_api, poll_until_done, get_instagram_account

logger = logging.getLogger(__name__)

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

TRUSTED_HOSTS = ("blotato.io", "catbox.moe")

def _filter_publishable_urls(visual_urls):
    """Filter to trusted hosts only (blotato.io + catbox.moe). Others cause publish failures."""
    trusted = [u for u in visual_urls if any(h in u for h in TRUSTED_HOSTS)]
    if trusted:
        if len(trusted) < len(visual_urls):
            dropped = len(visual_urls) - len(trusted)
            logger.warning(f"Filtered {dropped} untrusted URLs (only blotato.io / catbox.moe publish reliably)")
        return trusted
    # No trusted URLs — send everything and hope for the best
    logger.warning("No trusted URLs found. Publishing with all URLs (may fail).")
    return visual_urls


def publish_instagram(caption_data, visual_urls):
    """Publish to Instagram and return results."""
    logger.info("Starting publication process...")
    results = []

    account_id, username = get_instagram_account()
    if not account_id:
        return results

    # Only send Blotato-hosted URLs — external URLs cause failures
    publishable_urls = _filter_publishable_urls(visual_urls)
    logger.info(f"Publishing with {len(publishable_urls)}/{len(visual_urls)} images")

    # Instagram hard limit: 2200 characters
    caption = caption_data.get("caption", "")
    if len(caption) > 2200:
        logger.warning(f"Caption too long ({len(caption)} chars), trimming to 2200...")
        # Trim at last newline before 2197 to avoid cutting mid-sentence
        trimmed = caption[:2197]
        cut = trimmed.rfind("\n")
        caption = (trimmed[:cut] if cut > 1800 else trimmed) + "..."
        logger.info(f"Caption trimmed to {len(caption)} chars")

    try:
        payload = {
            "post": {
                "accountId": account_id,
                "content": {
                    "text": caption,
                    "mediaUrls": publishable_urls if publishable_urls else [],
                    "platform": "instagram"
                },
                "target": {
                    "targetType": "instagram"
                }
            }
        }

        logger.info("Submitting post to Blotato API...")
        data = request_api("POST", "/posts", payload)
        
        post_id = data.get("postSubmissionId", data.get("id", "unknown"))
        logger.info(f"Post submitted (ID: {post_id}). Waiting for confirmation...")

        final = poll_until_done(
            f"/posts/{post_id}",
            done_statuses=["published", "live", "completed", "done"],
            interval=3,
            timeout=120,
        )
        post_url = final.get("url", final.get("postUrl", "N/A"))
        status = final.get("status", "submitted")
        
        logger.info(f"Instagram Post Published: {post_url} (status: {status})")
        results.append({
            "platform": "instagram",
            "post_url": post_url,
            "post_id": post_id,
            "status": status,
        })
    except Exception as e:
        logger.error(f"Failed to publish to Instagram: {e}")
        results.append({
            "platform": "instagram",
            "post_url": "FAILED",
            "post_id": "N/A",
            "status": str(e),
        })

    return results
