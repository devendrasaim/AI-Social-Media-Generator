#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import logging
from core.config import setup_logging, validate_environment, LOG_FILE
from core.content_engine import extract_youtube, fetch_from_perplexity, generate_captions
from core.visual_engine import VisualEngine
from core.publisher import publish_instagram, log_to_csv

def main():
    parser = argparse.ArgumentParser(
        description="Repurpose YouTube Video -> Instagram post using Gemini and instagrapi.",
        epilog="Requires INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, and GEMINI_API_KEY in .env file."
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
        slide_paths = ve.generate_carousel_slides(content_data.get("slides", []))

        # Append hashtags to caption if not already included
        caption = content_data.get("caption", "")
        hashtags = " ".join(content_data.get("hashtags", []))
        if hashtags and hashtags not in caption:
            caption = f"{caption}\n\n{hashtags}"
        content_data["caption"] = caption
    except Exception as e:
        logger.error(f"Pipeline failed during extraction/generation: {e}")
        sys.exit(1)

    # 3. Copy slides to review folder
    logger.info("\n" + "=" * 60)
    logger.info("   POST REVIEW (CAROUSEL)")
    logger.info("=" * 60)
    print(f"\nCaption:\n{content_data.get('caption', 'N/A')}\n")

    review_dir = os.path.join(os.getcwd(), "carousel_review")
    os.makedirs(review_dir, exist_ok=True)
    logger.info(f"Copying {len(slide_paths)} slides for your review to: {review_dir}")

    for i, path in enumerate(slide_paths):
        try:
            dest = os.path.join(review_dir, f"slide_{i+1}{os.path.splitext(path)[1]}")
            shutil.copy(path, dest)
            print(f"Slide {i+1}: {dest}")
        except Exception as e:
            logger.warning(f"Failed to copy slide {i+1} for review: {e}")

    logger.info("=" * 60)

    # 4. Publish Confirmation
    if not args.publish:
        try:
            confirm = input("\nPublish post? (yes/no): ").strip().lower()
            if confirm not in ("yes", "y"):
                logger.info("Cancelled by user. No post published.")
                _cleanup_slides(slide_paths)
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            logger.info("\nCancelled by user.")
            _cleanup_slides(slide_paths)
            sys.exit(0)

    # 5. Publish & Log
    results = publish_instagram(content_data, slide_paths)
    _cleanup_slides(slide_paths)

    if results:
        log_to_csv(LOG_FILE, source_url, results)
        logger.info(f"\nDone! Post log saved to: {LOG_FILE}")
        all_failed = all(r.get("post_url") == "FAILED" for r in results)
        if all_failed:
            logger.error("All publish attempts failed. Check logs above for details.")
            sys.exit(1)
    else:
        logger.error("No results returned. Ensure Instagram credentials are set in .env.")
        sys.exit(1)


def _cleanup_slides(slide_paths):
    """Delete temp slide files after publish (or cancel)."""
    for path in slide_paths:
        try:
            if path and os.path.exists(path) and "temp" in path.lower():
                os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
