import os
import subprocess
import logging
import sys
import io
from core.config import QUEUE_FILE, LOCK_FILE, REVIEW_DIR, TEMP_DIR
from core.brainstormer import refill_queue_if_needed
from core.notifier import notify_all
from core.maintenance import clear_old_files
import time
import shutil

# Windows UTF-8 Terminal Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(SCRIPT_DIR, "topics_queue.txt")
LOG_FILE = os.path.join(SCRIPT_DIR, "automation_log.txt")
LOCK_FILE = os.path.join(SCRIPT_DIR, "automation.lock")

def acquire_lock():
    """Simple file-based PID lock to prevent overlapping automation runs."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Check if process is actually running
            if os.name == 'nt':
                # Windows check
                subprocess.check_output(f'tasklist /fi "PID eq {old_pid}"', shell=True)
            else:
                # Unix check
                os.kill(old_pid, 0)
            print(f"⚠️ Automation already running (PID: {old_pid}). Skipping.")
            return False
        except (ValueError, subprocess.CalledProcessError, ProcessLookupError, OSError):
            # Process not found, lock is stale
            pass
            
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("automate")

def get_next_topic():
    """Read the first non-comment, non-empty topic from the queue file."""
    if not os.path.exists(QUEUE_FILE):
        return None
    
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    
    # Separate topics from comments/empty lines
    topics = []
    others = []
    found_first_topic = False
    target_topic = None

    for line in all_lines:
        clean = line.strip()
        if not found_first_topic and clean and not clean.startswith("#"):
            target_topic = clean
            found_first_topic = True
        else:
            others.append(line)
    
    if not target_topic:
        return None
    
    # Save the remaining lines back (maintaining comments)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        f.writelines(others)
        
    return target_topic

def run_generator(topic):
    """Invoke main.py with the given topic and --publish flag."""
    logger.info(f"Starting automation for topic: {topic}")
    
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, "main.py"),
        "--perplexity", topic,
        "--publish",
        "--verbose"
    ]
    
    try:
        # Run subprocess and capture output
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        logger.info("Successfully published automated post.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Generator failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def main():
    if not acquire_lock():
        sys.exit(0)

    try:
        logger.info("--- Automation Run Started ---")
        notify_all("Starting Automation...", "Checking queue and preparing to publish.")
        
        # Refill queue if running low (< 3 topics)
        refill_queue_if_needed(QUEUE_FILE)

        # Maintenance: Clear 7-day old review files
        clear_old_files(os.path.join(os.getcwd(), "carousel_review"), days=7)
        # Clear temp directory completely every run
        clear_old_files(os.path.join(os.getcwd(), "temp"), days=0)

        topic = get_next_topic()
        
        if not topic:
            logger.warning("No topics found in queue. Add topics to topics_queue.txt to automate.")
            return

        success = run_generator(topic)
        
        if success:
            logger.info(f"Automation Run Completed Successfully for: {topic}")
            notify_all("Post Published Successfully!", f"Topic: {topic}\nCheck your Instagram feed.")
        else:
            logger.error("Automation Run Failed.")
            notify_all("Post Failed!", f"The automation run for '{topic}' failed. Check automation_log.txt for details.")
    finally:
        release_lock()

if __name__ == "__main__":
    main()
