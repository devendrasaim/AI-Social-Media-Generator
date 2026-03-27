#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import requests
from core.config import setup_logging, validate_environment, LOG_FILE
from core.content_engine import extract_youtube, fetch_from_perplexity, generate_captions
from core.visual_engine import VisualEngine
from core.publisher import publish_instagram, log_to_csv

def main():
    parser = argparse.ArgumentParser(
        description="Repurpose YouTube Video -> Instagram post using Gemini and Blotato.",
        epilog="Requires BLOTATO_API_KEY and GEMINI_API_KEY in .env file."
    )

    parser.add_argument("youtube_url", nargs="?", default=None,
                        help="YouTube video URL to repurpose. Omit when using --perplexity.")
    parser.add_argument("--perplexity", "-P", nargs="?", const="recent AI tools and productivity tips for creators",
                        metavar="TOPIC",
                        help="Use Perplexity as content source instead of YouTube. "
                             "Optionally specify a topic (default: recent AI tools and tips).")
    parser.add_argument("--tone", "-t", default="professional and engaging",
                        help="Tone/style for the post (e.g., 'casual and fun', 'witty').")
    parser.add_argument("--publish", "-p", action="store_true",
                        help="Auto-publish without prompting for review.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging.")

    args = parser.parse_args()

    # Validate source
    if args.perplexity is None and not args.youtube_url:
        parser.error("Provide a YouTube URL or use --perplexity [topic]")

    # 1. Config & Validation
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")
    validate_environment()

    logger.info("=" * 60)
    logger.info("  YouTube -> Instagram Repurposer CLI")
    logger.info("=" * 60)

    # 2. Pipeline Execution
    try:
        if args.perplexity is not None:
            logger.info(f"Source: Perplexity — {args.perplexity}")
            logger.info(f"Tone : {args.tone}")
            video_data = fetch_from_perplexity(args.perplexity)
            source_url = f"perplexity:{args.perplexity}"
        else:
            logger.info(f"Source: YouTube — {args.youtube_url}")
            logger.info(f"Tone  : {args.tone}")
            video_data = extract_youtube(args.youtube_url)
            source_url = args.youtube_url
        content_data = generate_captions(video_data["title"], video_data["content"], args.tone)

        ve = VisualEngine()
        visual_urls = ve.generate_carousel_urls(content_data.get("slides", []))

        # Append hashtags to caption if not already included
        caption = content_data.get("caption", "")
        hashtags = " ".join(content_data.get("hashtags", []))
        if hashtags and hashtags not in caption:
            caption = f"{caption}\n\n{hashtags}"
        content_data["caption"] = caption
    except Exception as e:
        logger.error(f"Pipeline failed during extraction/generation: {e}")
        sys.exit(1)

    # 3. Download & Review
    logger.info("\n" + "=" * 60)
    logger.info("   POST REVIEW (CAROUSEL)")
    logger.info("=" * 60)
    print(f"\nCaption:\n{content_data.get('caption', 'N/A')}\n")

    review_dir = os.path.join(os.getcwd(), "carousel_review")
    os.makedirs(review_dir, exist_ok=True)
    logger.info(f"Downloading {len(visual_urls)} images for your review to: {review_dir}")

    local_files = []
    for i, url in enumerate(visual_urls):
        try:
            resp = requests.get(url, stream=True, timeout=30,
                               headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            file_path = os.path.join(review_dir, f"slide_{i+1}.jpg")
            with open(file_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            local_files.append(file_path)
            print(f"Slide {i+1}: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to download image {i+1}: {e}")

    logger.info("=" * 60)

    # 4. Publish Confirmation
    if not args.publish:
        try:
            confirm = input("\nPublish post? (yes/no): ").strip().lower()
            if confirm not in ("yes", "y"):
                logger.info("Cancelled by user. No post published.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            logger.info("\nCancelled by user.")
            sys.exit(0)

    # 5. Publish & Log
    results = publish_instagram(content_data, visual_urls)
    if results:
        log_to_csv(LOG_FILE, source_url, results)
        logger.info(f"\nDone! Post log saved to: {LOG_FILE}")
        all_failed = all(r.get("post_url") == "FAILED" or r.get("status", "").startswith("FAILED") or r.get("status") == "failed" for r in results)
        if all_failed:
            logger.error("All publish attempts failed. Check logs above for details.")
            sys.exit(1)
    else:
        logger.error("No results returned. Ensure Instagram is connected.")
        sys.exit(1)

if __name__ == "__main__":
    main()
