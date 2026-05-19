
"""
Instagram RSS Carousel Poster - Premium Curadoria Edition (TEST MODE)
- Lê feed RSS
- Seleciona 5 entradas aleatórias
- Cada slide representa 1 feed diferente
- Destaca título + descrição + complemento
- Sanitiza o texto
- Gera carrossel premium
- Não publica enquanto publish_enabled=False

Dependências:
    pip install feedparser Pillow requests pyotp instagrapi tenacity
"""

import html
import io
import json
import logging
import random
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import feedparser
import pyotp
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tenacity import retry, stop_after_attempt, wait_exponential

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    BadPassword,
    ChallengeRequired,
    TwoFactorRequired,
)

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
@dataclass
class Config:
    username: str = "hmr1973maia"
    password: str = "Mkonji321????1"
    two_factor_seed: str = "BW64LFQ6L54HTGDKMED5E73J7HY46QVH"  # deixe "" se não usar
    session_file: Path = Path("instagrapi_session.json")

    rss_url: str = "https://sucesso.hmr1973.com/feed/"
    fixed_site_text: str = "sucesso.hmr1973.com"

    unsplash_access_key: str = ""
    pexels_api_key: str = ""

    output_dir: Path = Path("carousel_output")
    captions_file: Path = Path("captions.json")

    font_path: str = "Roboto-Medium.ttf"
    font_fallback: str = "arial.ttf"
    bold_font_path: str = "Roboto-Bold.ttf"

    image_width: int = 1080
    image_height: int = 1350

    request_timeout: int = 20
    max_retries: int = 3
    login_delay_seconds: float = 2.0

    title_font_size: int = 60
    body_font_size: int = 34
    small_font_size: int = 24

    title_max_lines: int = 4
    body_max_lines: int = 9
    max_slides: int = 5
    caption_body_limit: int = 700

    publish_enabled: bool = True

    active_theme: str = "sunset"
    brand_themes: dict = None

    hashtags: str = (
        "#marketing #digitalmarketing #sucesso #empreendedorismo "
        "#negocios #motivacao #instagram #conteudo #branding "
        "#marketingdigital #inspiracao #negociosdigitais"
    )

    def __post_init__(self):
        if self.brand_themes is None:
            self.brand_themes = {
                "sunset": {
                    "title_color": (255, 255, 255),
                    "accent_color": (255, 170, 40),
                    "body_color": (245, 245, 245),
                    "muted_color": (220, 220, 220),
                    "shadow_color": (0, 0, 0),
                    "dark_overlay_alpha": 145,
                    "card_overlay": (18, 18, 18, 155),
                    "footer_color": (255, 170, 40),
                },
                "ocean": {
                    "title_color": (255, 255, 255),
                    "accent_color": (0, 200, 255),
                    "body_color": (240, 248, 255),
                    "muted_color": (210, 225, 235),
                    "shadow_color": (0, 0, 0),
                    "dark_overlay_alpha": 150,
                    "card_overlay": (8, 20, 30, 165),
                    "footer_color": (0, 210, 255),
                },
                "forest": {
                    "title_color": (255, 255, 255),
                    "accent_color": (92, 184, 92),
                    "body_color": (240, 250, 240),
                    "muted_color": (215, 230, 215),
                    "shadow_color": (0, 0, 0),
                    "dark_overlay_alpha": 150,
                    "card_overlay": (12, 28, 16, 165),
                    "footer_color": (120, 220, 120),
                },
            }

    @property
    def theme(self):
        return self.brand_themes[self.active_theme]


CFG = Config()

# ══════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("poster.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
# SANITIZAÇÃO
# ══════════════════════════════════════════════════════════════════
def sanitize_text(raw: str) -> str:
    if not raw:
        return ""

    text = str(raw)

    for _ in range(2):
        text = html.unescape(text)

    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("[…]", "…")
    text = text.replace(" […]", "…")
    text = text.replace("[...]", "...")
    text = text.replace("&nbsp;", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\[\s*&#\d+;\s*\]", "…", text)
    text = re.sub(r"&#\d+;", " ", text)

    text = "".join(
        ch for ch in text
        if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t")
    )

    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([:])([^\s])", r"\1 \2", text)

    return text.strip()


def smart_truncate(text: str, max_chars: int) -> str:
    text = sanitize_text(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{cut}..."


# ══════════════════════════════════════════════════════════════════
# REDE
# ══════════════════════════════════════════════════════════════════
@retry(
    stop=stop_after_attempt(CFG.max_retries),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def fetch_url_bytes(url: str) -> bytes:
    resp = requests.get(url, timeout=CFG.request_timeout, stream=True)
    resp.raise_for_status()
    return resp.content


# ══════════════════════════════════════════════════════════════════
# RSS
# ══════════════════════════════════════════════════════════════════
def fetch_rss_entries(url: str) -> list:
    log.info("Buscando feed RSS: %s", url)
    feed = feedparser.parse(url)
    if not feed.entries:
        raise ValueError("Feed RSS vazio ou inacessível.")
    log.info("%d entradas encontradas.", len(feed.entries))
    return feed.entries


def pick_random_entries(entries: list, count: int = 5) -> list:
    if len(entries) <= count:
        return entries
    return random.sample(entries, count)


def extract_entry_text(entry) -> dict:
    title = sanitize_text(entry.get("title", "Sem título"))
    summary = sanitize_text(entry.get("summary") or entry.get("description") or "")
    summary = summary.replace("Quero saber mais sobre como ter sucesso no mundo digital", "").strip()

    complement = ""
    if len(summary) > 260:
        summary_short = smart_truncate(summary, 260)
        complement = smart_truncate(summary[260:], 180)
    else:
        summary_short = summary
        complement = ""

    if not complement and entry.get("link"):
        complement = f"Leia mais em nosso site."

    return {
        "title": smart_truncate(title, 120),
        "summary": summary_short,
        "complement": complement,
        "link": entry.get("link", ""),
    }


def build_carousel_data(entries: list) -> dict:
    slides = []
    for entry in entries[:CFG.max_slides]:
        item = extract_entry_text(entry)
        slides.append({
            "title": item["title"],
            "summary": item["summary"],
            "complement": item["complement"],
            "link": item["link"],
        })

    return {
        "slides": slides,
        "caption": build_caption_from_entries(slides),
    }


def build_caption_from_entries(slides: list) -> str:
    lines = ["Confira 5 conteúdos selecionados para você:\n"]
    for idx, slide in enumerate(slides, start=1):
        lines.append(f"{idx}. {slide['title']}")
    lines.append(f"\nAcesse: {CFG.fixed_site_text}\n")
    lines.append(CFG.hashtags)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# IMAGENS
# ══════════════════════════════════════════════════════════════════
def open_image_from_url(url: str) -> Optional[Image.Image]:
    if not url:
        return None
    try:
        return Image.open(io.BytesIO(fetch_url_bytes(url))).convert("RGB")
    except Exception:
        return None


def fetch_image_from_entry(entry) -> Optional[Image.Image]:
    for media in getattr(entry, "media_content", []):
        img = open_image_from_url(media.get("url", ""))
        if img:
            return img

    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image"):
            img = open_image_from_url(enc.get("href", ""))
            if img:
                return img

    html_block = entry.get("summary", "") + (entry.get("content") or [{}])[0].get("value", "")
    match = re.search(r'src=["\']([^"\']+)["\']', html_block)
    if match:
        img = open_image_from_url(match.group(1))
        if img:
            return img

    return None


def fetch_image_from_unsplash(keyword: str) -> Optional[Image.Image]:
    if not CFG.unsplash_access_key:
        return None
    try:
        url = (
            "https://api.unsplash.com/photos/random"
            f"?query={keyword}&orientation=portrait"
            f"&client_id={CFG.unsplash_access_key}"
        )
        data = requests.get(url, timeout=CFG.request_timeout).json()
        return open_image_from_url(data["urls"]["regular"])
    except Exception:
        return None


def fetch_image_from_pexels(keyword: str) -> Optional[Image.Image]:
    if not CFG.pexels_api_key:
        return None
    try:
        data = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": CFG.pexels_api_key},
            params={"query": keyword, "per_page": 10, "orientation": "portrait"},
            timeout=CFG.request_timeout,
        ).json()
        photos = data.get("photos", [])
        if not photos:
            return None
        return open_image_from_url(random.choice(photos)["src"]["large2x"])
    except Exception:
        return None


def fetch_image_picsum(seed_value: int) -> Image.Image:
    url = f"https://picsum.photos/seed/{seed_value}/{CFG.image_width}/{CFG.image_height}"
    return Image.open(io.BytesIO(fetch_url_bytes(url))).convert("RGB")


def get_best_image_for_entry(entry, seed_value: int) -> Image.Image:
    keyword = sanitize_text((entry.get("title") or "marketing").split()[0])

    for source, func, args in [
        ("RSS", fetch_image_from_entry, (entry,)),
        ("Unsplash", fetch_image_from_unsplash, (keyword,)),
        ("Pexels", fetch_image_from_pexels, (keyword,)),
    ]:
        img = func(*args)
        if img:
            log.info("Imagem obtida via: %s", source)
            return img

    log.info("Usando Picsum como fallback.")
    return fetch_image_picsum(seed_value)


# ══════════════════════════════════════════════════════════════════
# FONTES
# ══════════════════════════════════════════════════════════════════
def load_font(size: int, bold: bool = False):
    font_candidates = []
    if bold:
        font_candidates.append(CFG.bold_font_path)
    font_candidates.extend([CFG.font_path, CFG.font_fallback])

    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ══════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════
def smart_crop(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_ratio = image.width / image.height
    tgt_ratio = target_w / target_h

    if src_ratio > tgt_ratio:
        new_h = target_h
        new_w = int(image.width * target_h / image.height)
    else:
        new_w = target_w
        new_h = int(image.height * target_w / image.width)

    image = image.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return image.crop((left, top, left + target_w, top + target_h))


def create_base_slide(background: Image.Image) -> Image.Image:
    bg = smart_crop(background.copy(), CFG.image_width, CFG.image_height)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1.2))

    overlay = Image.new("RGBA", bg.size, (0, 0, 0, CFG.theme["dark_overlay_alpha"]))
    base = Image.alpha_composite(bg.convert("RGBA"), overlay)
    return base.convert("RGB")


def draw_glass_card(base: Image.Image, box: Tuple[int, int, int, int], fill: Tuple[int, int, int, int]):
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(box, radius=36, fill=fill)
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def draw_shadow_text(draw, position, text, font, fill, shadow_fill=None, offset=2):
    if shadow_fill is None:
        shadow_fill = CFG.theme["shadow_color"]
    x, y = position
    draw.text((x + offset, y + offset), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text_to_lines(draw, text, font, max_width) -> List[str]:
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def fit_text_lines(draw, text, font, max_width, max_lines) -> List[str]:
    text = sanitize_text(text)
    lines = wrap_text_to_lines(draw, text, font, max_width)

    if len(lines) <= max_lines:
        return lines

    truncated = text
    while len(lines) > max_lines and len(truncated) > 10:
        truncated = truncated[:-10].rsplit(" ", 1)[0].strip()
        candidate = f"{truncated}..."
        lines = wrap_text_to_lines(draw, candidate, font, max_width)

    return lines[:max_lines]


def draw_lines(draw, lines, font, x, y, line_spacing, fill):
    for line in lines:
        draw_shadow_text(draw, (x, y), line, font, fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def draw_progress_bar(draw, current: int, total: int, x: int, y: int, width: int, height: int):
    gap = 12
    segment_width = int((width - (gap * (total - 1))) / total)

    for i in range(total):
        x1 = x + i * (segment_width + gap)
        x2 = x1 + segment_width
        fill = CFG.theme["accent_color"] if i < current else (255, 255, 255, 80)
        draw.rounded_rectangle([(x1, y), (x2, y + height)], radius=height // 2, fill=fill)


def create_feed_slide(background: Image.Image, slide_data: dict, index: int, total: int) -> Image.Image:
    base = create_base_slide(background)
    base = draw_glass_card(base, (60, 120, 1020, 1180), CFG.theme["card_overlay"])
    draw = ImageDraw.Draw(base)

    w, h = base.size
    margin = 95
    content_width = w - (margin * 2)

    title_font = load_font(CFG.title_font_size, bold=True)
    body_font = load_font(CFG.body_font_size)
    small_font = load_font(CFG.small_font_size)

    draw_progress_bar(draw, index, total, margin, 62, 500, 12)
    draw.rounded_rectangle([(margin, 98), (margin + 190, 108)], radius=5, fill=CFG.theme["accent_color"])

    title_lines = fit_text_lines(draw, slide_data["title"], title_font, content_width, CFG.title_max_lines)

    body_text = slide_data["summary"]
    if slide_data["complement"]:
        body_text = f"{body_text}\n\n{slide_data['complement']}"

    body_lines = fit_text_lines(draw, body_text, body_font, content_width, CFG.body_max_lines)

    y = 160
    y = draw_lines(draw, title_lines, title_font, margin, y, 14, CFG.theme["title_color"])
    y += 30
    draw_lines(draw, body_lines, body_font, margin, y, 16, CFG.theme["body_color"])

    footer = CFG.fixed_site_text
    draw_shadow_text(draw, (margin, h - 105), footer, small_font, CFG.theme["footer_color"])
    draw_shadow_text(draw, (w - 130, h - 105), f"{index}/{total}", small_font, CFG.theme["muted_color"])

    return base


# ══════════════════════════════════════════════════════════════════
# GERAÇÃO
# ══════════════════════════════════════════════════════════════════
def generate_carousel(entries: list) -> tuple[list[Path], str]:
    CFG.output_dir.mkdir(parents=True, exist_ok=True)

    carousel_data = build_carousel_data(entries)
    paths = []

    for idx, entry in enumerate(entries[:CFG.max_slides], start=1):
        bg = get_best_image_for_entry(entry, seed_value=idx * 999)
        slide_data = carousel_data["slides"][idx - 1]
        slide_img = create_feed_slide(bg, slide_data, idx, len(carousel_data["slides"]))
        path = CFG.output_dir / f"slide_{idx}.jpg"
        slide_img.save(path, format="JPEG", quality=93, optimize=True)
        paths.append(path)

    return paths, carousel_data["caption"]


def save_captions_manifest(carousel_paths: list[Path], carousel_caption: str):
    data = {
        "mode": "test_only",
        "site": CFG.fixed_site_text,
        "theme": CFG.active_theme,
        "carousel": {
            "slides": [str(p) for p in carousel_paths],
            "caption": carousel_caption,
        },
    }

    CFG.captions_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log.info("Manifesto salvo em: %s", CFG.captions_file)


# ══════════════════════════════════════════════════════════════════
# LOGIN / PUBLICAÇÃO
# ══════════════════════════════════════════════════════════════════
def build_totp_code() -> Optional[str]:
    seed = (CFG.two_factor_seed or "").strip().upper().replace(" ", "")
    if not seed:
        return None
    try:
        return pyotp.TOTP(seed).now()
    except Exception as exc:
        log.warning("Falha ao gerar TOTP: %s", exc)
        return None


def delete_session_file():
    try:
        CFG.session_file.unlink(missing_ok=True)
    except Exception:
        pass


def create_client() -> Client:
    cl = Client()
    cl.delay_range = [1, 3]
    return cl


def save_session(cl: Client):
    settings = cl.get_settings()
    CFG.session_file.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Sessão salva em: %s", CFG.session_file)


def load_session(cl: Client) -> bool:
    if not CFG.session_file.exists():
        return False
    try:
        settings = json.loads(CFG.session_file.read_text(encoding="utf-8"))
        cl.set_settings(settings)
        cl.login(CFG.username, CFG.password)
        log.info("Sessão restaurada com sucesso.")
        return True
    except Exception as exc:
        log.warning("Falha ao restaurar sessão: %s", exc)
        return False


def fresh_login(cl: Client):
    time.sleep(CFG.login_delay_seconds)

    try:
        cl.login(CFG.username, CFG.password)
        log.info("Login realizado com sucesso.")
        return

    except TwoFactorRequired:
        code = build_totp_code()
        if not code:
            raise RuntimeError("2FA exigido, mas a chave TOTP não está configurada corretamente.")
        cl.login(CFG.username, CFG.password, verification_code=code)
        log.info("Login com 2FA realizado com sucesso.")
        return

    except BadPassword as exc:
        raise RuntimeError("Senha inválida ou recusada pelo Instagram.") from exc

    except ChallengeRequired as exc:
        raise RuntimeError("Instagram exigiu challenge/checkpoint. Resolva no app oficial.") from exc

    except LoginRequired as exc:
        raise RuntimeError("Instagram recusou o login automatizado neste momento.") from exc

    except Exception as exc:
        raise RuntimeError(f"Erro inesperado no login: {type(exc).__name__}: {exc}") from exc


def get_instagram_client() -> Client:
    cl = create_client()

    if load_session(cl):
        try:
            cl.get_timeline_feed()
            return cl
        except Exception as exc:
            log.warning("Sessão inválida/expirada: %s", exc)
            delete_session_file()
            cl = create_client()

    fresh_login(cl)
    save_session(cl)
    return cl


def publish_carousel_to_instagram(paths: List[Path], caption: str) -> bool:
    if not CFG.publish_enabled:
        log.info("Modo teste ativo: publicação desabilitada.")
        return True

    cl = get_instagram_client()
    media = cl.album_upload(paths=[str(p) for p in paths], caption=caption)
    log.info("Carrossel publicado com sucesso. Media PK: %s", getattr(media, "pk", "N/A"))
    return True


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    log.info("═" * 60)
    log.info("Instagram RSS Carousel Curadoria — TEST MODE")
    log.info("═" * 60)
    log.info("Tema ativo: %s", CFG.active_theme)
    log.info("Publicação habilitada? %s", CFG.publish_enabled)

    try:
        entries = fetch_rss_entries(CFG.rss_url)
        selected_entries = pick_random_entries(entries, CFG.max_slides)
    except Exception as exc:
        log.error("Erro ao buscar RSS: %s", exc)
        sys.exit(1)

    try:
        carousel_paths, carousel_caption = generate_carousel(selected_entries)
        save_captions_manifest(carousel_paths, carousel_caption)
    except Exception as exc:
        log.error("Erro ao gerar carrossel: %s", exc)
        sys.exit(1)

    log.info("Carrossel gerado com %d slides.", len(carousel_paths))
    log.info("Arquivos prontos para validação visual.")

    if CFG.publish_enabled:
        try:
            publish_carousel_to_instagram(carousel_paths, carousel_caption)
        except Exception as exc:
            log.error("Erro crítico na publicação: %s", exc)
            sys.exit(1)

    log.info("Processo finalizado com sucesso.")
    sys.exit(0)


if __name__ == "__main__":
    main()