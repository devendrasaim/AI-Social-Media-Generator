import os
import time
import logging

logger = logging.getLogger(__name__)

def clear_old_files(directory, days=7):
    """Delete files in a directory that are older than X days."""
    if not os.path.exists(directory):
        return

    now = time.time()
    cutoff = now - (days * 86400)
    
    count = 0
    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                if os.path.getmtime(filepath) < cutoff:
                    os.remove(filepath)
                    count += 1
        if count > 0:
            logger.info(f"Cleaned up {count} old files in {directory}")
    except Exception as e:
        logger.error(f"Cleanup failed for {directory}: {e}")
