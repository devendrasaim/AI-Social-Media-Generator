import os
import sys
import logging
from dotenv import load_dotenv

# Environment Variables
load_dotenv()
BLOTATO_API_KEY = os.getenv("BLOTATO_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
BLOTATO_BASE = "https://backend.blotato.com/v2"
PERPLEXITY_BASE = "https://api.perplexity.ai"
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")

# Notifications
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(SCRIPT_DIR, "published_posts.csv")
RESOURCES_DIR = os.path.join(SCRIPT_DIR, "resources")
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
REVIEW_DIR = os.path.join(SCRIPT_DIR, "carousel_review")
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp")
QUEUE_FILE = os.path.join(SCRIPT_DIR, "topics_queue.txt")
LOCK_FILE = os.path.join(SCRIPT_DIR, "automation.lock")

# Logging setup
def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Windows UTF-8 Terminal Fix
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def validate_environment():
    if not BLOTATO_API_KEY:
        logging.error("BLOTATO_API_KEY not set. Add it to your .env file.")
        sys.exit(1)
    if not GEMINI_API_KEY:
        logging.warning("GEMINI_API_KEY not set. Will use template-based captions.")
        logging.warning("  For AI-generated captions, add GEMINI_API_KEY to your .env file.")
