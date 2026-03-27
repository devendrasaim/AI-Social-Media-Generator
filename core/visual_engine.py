import os
import math
import random
import textwrap
import urllib.parse
import logging
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from google import genai
from google.genai import types
from .config import GEMINI_API_KEY, IMAGEN_MODEL, FONTS_DIR, RESOURCES_DIR, TEMP_DIR

logger = logging.getLogger(__name__)

# Canvas
W, H = 1080, 1080

# Zone boundaries
HEADER_H     = int(H * 0.15)                  # 162px
IMAGE_ZONE_Y = HEADER_H                        # 162
IMAGE_ZONE_H = int(H * 0.55)                   # 594px
BODY_ZONE_Y  = IMAGE_ZONE_Y + IMAGE_ZONE_H     # 756
BODY_ZONE_H  = H - BODY_ZONE_Y                 # 324px

# Image card (50px padding inside image zone)
CARD_PAD    = 50
CARD_X      = CARD_PAD                         # 50
CARD_Y      = IMAGE_ZONE_Y + CARD_PAD          # 212
CARD_W      = W - 2 * CARD_PAD                 # 980
CARD_H      = IMAGE_ZONE_H - 2 * CARD_PAD      # 494
CARD_RADIUS = 20

# Colors
BG_COLOR   = (0, 0, 0)
TOPO_COLOR = (18, 18, 32)       # dark grey/muted blue
GRAD_START = (147, 51, 234)     # purple
GRAD_END   = (0, 200, 255)      # cyan
BODY_COLOR = (255, 255, 255)


class VisualEngine:
    """Composes carousel slides: topographic bg + gradient headline + image card + body text."""

    def generate_carousel_urls(self, slide_data):
        """Generate catbox.moe URLs for each carousel slide."""
        urls = []
        total = len(slide_data)
        for i, slide in enumerate(slide_data):
            headline    = slide.get("headline", "")
            key_point   = slide.get("key_point", "")
            image_prompt = slide.get("image_prompt", headline)
            is_last     = (i == total - 1)
            logger.info(f"Composing slide {i+1}/{total}: {headline or '(CTA)'}")

            url = self._compose_slide(i, headline, key_point, image_prompt, is_last)
            if url:
                urls.append(url)
                logger.info(f"  Slide {i+1} ready: {url}")
            else:
                logger.error(f"  Slide {i+1}: failed to generate, skipping")

        return urls

    def _compose_slide(self, idx, headline, key_point, image_prompt, is_last):
        """Compose a single 1080x1080 slide and upload to catbox.moe."""
        # 0. Optimization for Last Slide (Static CTA)
        if is_last:
            static_cta_path = os.path.join(RESOURCES_DIR, "last_slide_cta.jpg")
            if os.path.exists(static_cta_path):
                logger.info("  Using static CTA slide from resources (saving API tokens)")
                try:
                    return self._upload_to_catbox(static_cta_path)
                except Exception as e:
                    logger.warning(f"  Static CTA upload failed ({e}), composing CTA slide dynamically...")

        # 1. Get image: Imagen 3 → Pollinations → gradient fallback
        top_img = None
        try:
            top_img = self._download_imagen_image(image_prompt)
            logger.info(f"  Imagen image downloaded ({top_img.size})")
        except Exception as e:
            logger.warning(f"  Imagen failed ({e}), trying Pollinations...")
        if top_img is None:
            try:
                top_img = self._download_pollinations_image(image_prompt)
                logger.info(f"  Pollinations image downloaded ({top_img.size})")
            except Exception as e:
                logger.warning(f"  Pollinations failed ({e}), using gradient fallback")
                top_img = self._make_gradient_fallback()

        # 2. Black RGB canvas + topographic texture
        canvas = Image.new("RGB", (W, H), BG_COLOR)
        draw   = ImageDraw.Draw(canvas)
        self._draw_topographic_bg(draw)

        # 3. Convert to RGBA for compositing
        canvas = canvas.convert("RGBA")

        # 4. Content slide: drop shadow + rounded image card
        if not is_last:
            # Drop shadow (blurred RGBA layer)
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.rounded_rectangle(
                [CARD_X + 12, CARD_Y + 16, CARD_X + CARD_W + 12, CARD_Y + CARD_H + 16],
                radius=CARD_RADIUS, fill=(0, 0, 0, 210),
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
            canvas = Image.alpha_composite(canvas, shadow)

            # Rounded card image
            img_r = top_img.resize((CARD_W, CARD_H), Image.LANCZOS).convert("RGBA")
            mask  = Image.new("L", (CARD_W, CARD_H), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [0, 0, CARD_W - 1, CARD_H - 1], radius=CARD_RADIUS, fill=255,
            )
            canvas.paste(img_r, (CARD_X, CARD_Y), mask)

        # 5. Refresh draw after compositing
        draw = ImageDraw.Draw(canvas)

        # 6. Load fonts
        headline_font = self._load_font(
            os.path.join(FONTS_DIR, "GoogleSans-Bold.ttf"), 62
        )
        body_font = self._load_font(
            os.path.join(FONTS_DIR, "GoogleSans-Medium.ttf"), 34
        )

        # 7. Gradient headline in header zone (both slides when headline exists)
        if headline:
            lines   = textwrap.wrap(headline.upper(), width=24)
            line_h  = self._text_height(draw, "A", headline_font)
            block_h = len(lines) * line_h + (len(lines) - 1) * 8
            y = max(0, HEADER_H // 2 - block_h // 2)
            for line in lines:
                self._draw_gradient_text(canvas, draw, line, headline_font, y)
                y += line_h + 8

        # 8. Body zone or CTA
        if is_last:
            cta_font = self._load_font(
                os.path.join(FONTS_DIR, "GoogleSans-Bold.ttf"), 54
            )
            self._draw_body_text(
                draw, "Follow @myaiguru9\nfor more AI tips",
                cta_font, BODY_COLOR,
                y_center=IMAGE_ZONE_Y + IMAGE_ZONE_H // 2,
                wrap_chars=30,
                highlights=False
            )
        elif key_point:
            self._draw_body_text(
                draw, key_point, body_font, BODY_COLOR,
                y_center=BODY_ZONE_Y + BODY_ZONE_H // 2,
                wrap_chars=44
            )

        # 9. Save, upload, clean up
        canvas = canvas.convert("RGB")
        temp_path = os.path.join(TEMP_DIR, f"_temp_slide_{idx}.png")
        canvas.save(temp_path, "PNG")
        logger.info(f"  Uploading slide {idx+1} to catbox.moe...")
        try:
            try:
                url = self._upload_to_catbox(temp_path)
            except Exception as e:
                logger.error(f"  Catbox upload failed: {e}")
                url = None
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

        return url

    # ── Background ─────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_topographic_bg(draw):
        """Draw subtle topographic sine-wave line texture across the full canvas."""
        for i in range(45):
            y_base = int(i * H / 45)
            freq   = 0.004 + (i % 7) * 0.001
            amp    = 6 + (i % 4) * 5
            phase  = i * 1.1
            pts    = [(x, y_base + int(amp * math.sin(freq * x + phase)))
                      for x in range(0, W + 1, 4)]
            if len(pts) >= 2:
                draw.line(pts, fill=TOPO_COLOR, width=1)

    # ── Text rendering ──────────────────────────────────────────────────────────

    @staticmethod
    def _draw_gradient_text(canvas, draw, text, font, y):
        """Draw a single line with purple→cyan horizontal gradient, centered."""
        bbox = draw.textbbox((0, 0), text, font=font)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]
        if tw <= 0 or th <= 0:
            return

        # Gradient strip
        grad    = Image.new("RGB", (tw, th))
        grad_d  = ImageDraw.Draw(grad)
        for x in range(tw):
            t = x / max(tw - 1, 1)
            r = int(GRAD_START[0] + (GRAD_END[0] - GRAD_START[0]) * t)
            g = int(GRAD_START[1] + (GRAD_END[1] - GRAD_START[1]) * t)
            b = int(GRAD_START[2] + (GRAD_END[2] - GRAD_START[2]) * t)
            grad_d.line([(x, 0), (x, th - 1)], fill=(r, g, b))

        # Text mask
        mask   = Image.new("L", (tw, th), 0)
        mask_d = ImageDraw.Draw(mask)
        mask_d.text((-bbox[0], -bbox[1]), text, fill=255, font=font)

        x_pos = (W - tw) // 2
        canvas.paste(grad, (x_pos, y), mask)

    @staticmethod
    def _draw_body_text(draw, text, font, color, y_center, wrap_chars=44, highlights=True):
        """Draw wrapped, centered text with the first question (?) highlighted in Red."""
        # Detect the first question for highlighting
        question_part = ""
        answer_part   = text
        if highlights and "?" in text:
            parts = text.split("?", 1)
            question_part = parts[0] + "?"
            answer_part   = parts[1].strip()

        paragraphs = [p for p in [question_part, answer_part] if p]
        all_lines  = []
        line_colors = []

        for i, para in enumerate(paragraphs):
            para_lines = textwrap.wrap(para, width=wrap_chars)
            all_lines.extend(para_lines)
            # If highlights is True, the first 'paragraph' (the question) is Red
            c = (255, 60, 60) if (highlights and i == 0 and question_part) else color
            line_colors.extend([c] * len(para_lines))

        if not all_lines:
            return

        bbox   = draw.textbbox((0, 0), "Ag", font=font)
        line_h = bbox[3] - bbox[1]
        step   = int(line_h * 1.4)
        total  = line_h + (len(all_lines) - 1) * step
        y      = y_center - total // 2

        for line, c in zip(all_lines, line_colors):
            if line:
                b  = draw.textbbox((0, 0), line, font=font)
                tw = b[2] - b[0]
                draw.text(((W - tw) // 2, y), line, fill=c, font=font)
            y += step

    @staticmethod
    def _text_height(draw, text, font):
        b = draw.textbbox((0, 0), text, font=font)
        return b[3] - b[1]

    # ── Image sources ───────────────────────────────────────────────────────────

    @staticmethod
    def _download_imagen_image(image_prompt):
        """Generate image with Gemini Imagen. Returns PIL Image."""
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set")
        client = genai.Client(api_key=GEMINI_API_KEY,
                              http_options={"api_version": "v1beta"})
        response = client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            ),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        return Image.open(BytesIO(image_bytes)).convert("RGB")

    @staticmethod
    def _download_pollinations_image(image_prompt):
        """Download image from Pollinations.ai. Retries 3x."""
        clean_prompt = (
            f"{image_prompt}, cinematic, high quality, professional photography, "
            f"no text, no watermark, sharp focus"
        )
        encoded  = urllib.parse.quote(clean_prompt)
        last_err = None
        for attempt in range(3):
            seed = random.randint(1, 99999)
            url  = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width={CARD_W}&height={CARD_H}&seed={seed}"
            )
            logger.debug(f"  Pollinations attempt {attempt+1}/3 seed={seed}")
            try:
                resp = requests.get(
                    url, timeout=90, stream=True,
                    headers={"User-Agent": "Mozilla/5.0",
                             "Referer": "https://pollinations.ai/"},
                )
                if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
                    return Image.open(BytesIO(resp.content)).convert("RGB")
                last_err = f"HTTP {resp.status_code}"
            except Exception as e:
                last_err = str(e)
        raise RuntimeError(f"Pollinations failed after 3 attempts: {last_err}")

    @staticmethod
    def _make_gradient_fallback():
        """Return a dark gradient image at card dimensions as fallback."""
        img  = Image.new("RGB", (CARD_W, CARD_H))
        draw = ImageDraw.Draw(img)
        tc   = (26, 26, 46)
        bc   = (22, 33, 62)
        for y in range(CARD_H):
            t = y / CARD_H
            r = int(tc[0] + (bc[0] - tc[0]) * t)
            g = int(tc[1] + (bc[1] - tc[1]) * t)
            b = int(tc[2] + (bc[2] - tc[2]) * t)
            draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))
        return img

    # ── Utilities ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_font(filename, size):
        """Try to load a TTF font, fall back to PIL default."""
        try:
            return ImageFont.truetype(filename, size)
        except OSError:
            return ImageFont.load_default()

    @staticmethod
    def _upload_to_catbox(file_path):
        """Upload a file to catbox.moe. Returns direct URL. Retries 3x."""
        import time
        last_err = None
        for attempt in range(3):
            if attempt > 0:
                time.sleep(3)
            try:
                with open(file_path, "rb") as f:
                    resp = requests.post(
                        "https://catbox.moe/user/api.php",
                        data={"reqtype": "fileupload"},
                        files={"fileToUpload": (os.path.basename(file_path), f, "image/png")},
                        timeout=20,
                    )
                if resp.status_code == 200 and resp.text.strip().startswith("https://"):
                    return resp.text.strip()
                last_err = f"{resp.status_code} '{resp.text.strip()[:100]}'"
            except Exception as e:
                last_err = str(e)
        raise RuntimeError(f"Catbox upload failed after 3 attempts: {last_err}")
