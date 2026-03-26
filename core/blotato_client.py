import time
import json
import requests
import logging
from .config import BLOTATO_API_KEY, BLOTATO_BASE

logger = logging.getLogger(__name__)

def get_headers():
    return {
        "Content-Type": "application/json",
        "blotato-api-key": BLOTATO_API_KEY,
    }

def request_api(method, path, json_data=None):
    """Make an authenticated request to the Blotato API."""
    url = f"{BLOTATO_BASE}{path}"
    logger.debug(f"{method} {url}")
    resp = requests.request(
        method,
        url,
        headers=get_headers(),
        json=json_data,
    )
    if not resp.ok:
        logger.error(f"API Error ({resp.status_code}): {resp.text}")
        resp.raise_for_status()
    return resp.json()

def poll_until_done(path, done_statuses, fail_keywords=None, interval=5, timeout=300):
    """Poll a Blotato endpoint until a terminal status is reached."""
    if fail_keywords is None:
        fail_keywords = ["fail", "error"]

    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        data = request_api("GET", path)
        # Blotato wraps many responses in {"item": {...}} — unwrap
        inner = data.get("item", data)
        status = inner.get("status", data.get("status", ""))

        if status in done_statuses:
            return data

        if any(kw in status.lower() for kw in fail_keywords):
            logger.error(f"Task Failed. Status Data: {json.dumps(data, indent=2)}")
            raise RuntimeError(f"Failed with status: {status}")

        dots = "." * min(elapsed // interval, 20)
        logger.info(f"   {dots} ({elapsed}s) status={status}")

    raise TimeoutError(f"Timed out after {timeout}s polling {path}")

def get_instagram_account():
    """Fetch the connected Instagram account ID from Blotato."""
    logger.info("Fetching connected Instagram account...")
    data = request_api("GET", "/users/me/accounts")
    for item in data.get("items", []):
        if item.get("platform", "").lower() == "instagram":
            logger.info(f"Found Instagram account: @{item.get('username')}")
            return item["id"], item.get("username")

    logger.error("Instagram account not connected in Blotato.")
    return None, None

def generate_visual_from_template(prompt):
    """Generate a visual via Blotato's template engine. Returns image URL or empty string."""
    # Fetch available templates and pick an image-based one
    templates = request_api("GET", "/videos/templates").get("items", [])
    # Prefer non-base templates (UUID format = image infographics)
    image_templates = [t for t in templates if not t["id"].startswith("/base/")]
    if not image_templates:
        image_templates = templates
    template_id = image_templates[0]["id"] if image_templates else None
    if not template_id:
        return ""

    logger.info(f"Using template: {template_id}")
    data = request_api("POST", "/videos/from-templates", {
        "templateId": template_id,
        "prompt": prompt,
        "inputs": {},
        "render": True,
    })
    # Response is wrapped: {"item": {"id": "..."}}
    item = data.get("item", data)
    creation_id = item.get("id", data.get("id"))
    if not creation_id:
        return ""

    result = poll_until_done(
        f"/videos/creations/{creation_id}",
        done_statuses=["done"],
        interval=5,
        timeout=120,
    )
    # Poll response is also wrapped in "item"
    item = result.get("item", result)
    media_url = item.get("mediaUrl") or ""
    image_urls = item.get("imageUrls") or []
    return media_url or (image_urls[0] if image_urls else "")
