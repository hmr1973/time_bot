

"""
Instagram RSS Carousel Poster - Premium Edition
- Lê feed RSS
- Escolhe uma entrada
- Extrai imagem do post ou usa fallback
- Sanitiza o texto
- Gera carrossel premium com UX/CX writing
- Previne overflow visual
- Usa templates diferentes para capa / conteúdo / CTA
- Publica como álbum no Instagram via instagrapi

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
    unsplash_access_key: str = ""
    pexels_api_key: str = ""

    output_dir: Path = Path("carousel_output")
    font_path: str = "Roboto-Medium.ttf"
    font_fallback: str = "arial.ttf"
    bold_font_path: str = "Roboto-Bold.ttf"

    image_width: int = 1080
    image_height: int = 1350

    request_timeout: int = 20
    max_retries: int = 3
    login_delay_seconds: float = 2.0

    cover_title_font_size: int = 72
    cover_subtitle_font_size: int = 38
    section_title_font_size: int = 54
    body_font_size: int = 34
    cta_title_font_size: int = 58
    small_font_size: int = 24

    title_color: tuple = (255, 255, 255)
    accent_color: tuple = (255, 170, 40)
    body_color: tuple = (245, 245, 245)
    muted_color: tuple = (220, 220, 220)
    shadow_color: tuple = (0, 0, 0)

    dark_overlay_alpha: int = 145
    card_overlay: tuple = (18, 18, 18, 150)
    cta_overlay: tuple = (255, 170, 40, 205)

    caption_body_limit: int = 600
    max_slides: int = 5

    content_max_lines: int = 8
    cover_title_max_lines: int = 4
    cover_subtitle_max_lines: int = 3
    cta_body_max_lines: int = 6

    hashtags: str = (
        "#marketing #digitalmarketing #sucesso #empreendedorismo "
        "#negocios #motivacao #instagram #conteudo #branding "
        "#uxwriting #customerexperience #marketingdigital"
    )


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
# SANITIZAÇÃO DE TEXTO
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


def split_sentences(text: str) -> List[str]:
    text = sanitize_text(text)
    parts = re.split(r'(?<=[\.\!\?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


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


def build_ux_carousel_text(entry) -> dict:
    title = sanitize_text(entry.get("title", "Sem título"))
    raw_body = sanitize_text(entry.get("summary") or entry.get("description") or "")
    raw_body = raw_body.replace("Quero saber mais sobre como ter sucesso no mundo digital", "").strip()

    sentences = split_sentences(raw_body)

    short_intro = sentences[0] if len(sentences) > 0 else smart_truncate(raw_body, 180)
    main_point = sentences[1] if len(sentences) > 1 else smart_truncate(raw_body, 180)
    practical = sentences[2] if len(sentences) > 2 else "Transforme a informação em uma ação simples, objetiva e consistente."
    reflection = sentences[3] if len(sentences) > 3 else "Quando a mensagem é clara, a experiência melhora e a decisão fica mais fácil."

    slides = [
        {
            "type": "cover",
            "title": smart_truncate(title, 110),
            "body": "Deslize e veja a ideia principal de forma rápida, clara e útil."
        },
        {
            "type": "content",
            "title": "O problema",
            "body": smart_truncate(
                f"Muita gente consome conteúdo, mas não transforma isso em ação. {short_intro}",
                280
            )
        },
        {
            "type": "content",
            "title": "O insight",
            "body": smart_truncate(
                f"A ideia central é simples: {main_point}",
                260
            )
        },
        {
            "type": "content",
            "title": "Na prática",
            "body": smart_truncate(
                f"Como aplicar isso no dia a dia: {practical}",
                260
            )
        },
        {
            "type": "cta",
            "title": "Agora é com você",
            "body": smart_truncate(
                f"{reflection} Salve este conteúdo e compartilhe com alguém que pode se beneficiar desta mensagem.",
                240
            )
        },
    ]

    return {
        "title": title,
        "body": raw_body,
        "slides": slides[:CFG.max_slides],
    }


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


def fetch_image_from_rss_entry(entry) -> Optional[Image.Image]:
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


def fetch_image_picsum() -> Image.Image:
    seed = random.randint(1, 99999)
    url = f"https://picsum.photos/seed/{seed}/{CFG.image_width}/{CFG.image_height}"
    return Image.open(io.BytesIO(fetch_url_bytes(url))).convert("RGB")


def get_best_image(entry) -> Image.Image:
    keyword = sanitize_text((entry.get("title") or "marketing").split()[0])

    for source, func, args in [
        ("RSS", fetch_image_from_rss_entry, (entry,)),
        ("Unsplash", fetch_image_from_unsplash, (keyword,)),
        ("Pexels", fetch_image_from_pexels, (keyword,)),
    ]:
        img = func(*args)
        if img:
            log.info("Imagem obtida via: %s", source)
            return img

    log.info("Usando Picsum como fallback.")
    return fetch_image_picsum()


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
# LAYOUT HELPERS
# ══════════════════════════════════════════════════════════════════
def smart_crop(image: Image.Image) -> Image.Image:
    tw, th = CFG.image_width, CFG.image_height
    src_ratio = image.width / image.height
    tgt_ratio = tw / th

    if src_ratio > tgt_ratio:
        new_h = th
        new_w = int(image.width * th / image.height)
    else:
        new_w = tw
        new_h = int(image.height * tw / image.width)

    image = image.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    return image.crop((left, top, left + tw, top + th))


def create_base_slide(background: Image.Image) -> Image.Image:
    bg = smart_crop(background.copy())
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1.2))

    overlay = Image.new("RGBA", bg.size, (0, 0, 0, CFG.dark_overlay_alpha))
    base = Image.alpha_composite(bg.convert("RGBA"), overlay)
    return base.convert("RGB")


def draw_shadow_text(draw, position, text, font, fill, shadow_fill=(0, 0, 0), offset=2):
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
        fill = CFG.accent_color if i < current else (255, 255, 255, 80)
        draw.rounded_rectangle([(x1, y), (x2, y + height)], radius=height // 2, fill=fill)


def draw_glass_card(base: Image.Image, box: Tuple[int, int, int, int], fill: Tuple[int, int, int, int]):
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(box, radius=36, fill=fill)
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


# ══════════════════════════════════════════════════════════════════
# TEMPLATES
# ══════════════════════════════════════════════════════════════════
def create_cover_slide(background: Image.Image, slide_data: dict, index: int, total: int) -> Image.Image:
    base = create_base_slide(background)
    base = draw_glass_card(base, (55, 105, 1025, 1180), (18, 18, 18, 118))
    draw = ImageDraw.Draw(base)

    w, h = base.size
    margin = 90
    content_width = w - (margin * 2)

    title_font = load_font(CFG.cover_title_font_size, bold=True)
    subtitle_font = load_font(CFG.cover_subtitle_font_size)
    small_font = load_font(CFG.small_font_size)

    draw_progress_bar(draw, index, total, margin, 58, 500, 12)

    badge_text = "CARROSSEL"
    draw.rounded_rectangle([(margin, 95), (margin + 190, 145)], radius=20, fill=CFG.accent_color)
    draw_shadow_text(draw, (margin + 26, 106), badge_text, small_font, (20, 20, 20))

    title_lines = fit_text_lines(draw, slide_data["title"], title_font, content_width - 40, CFG.cover_title_max_lines)
    subtitle_lines = fit_text_lines(draw, slide_data["body"], subtitle_font, content_width - 40, CFG.cover_subtitle_max_lines)

    y = 240
    y = draw_lines(draw, title_lines, title_font, margin, y, 18, CFG.title_color)
    y += 36
    y = draw_lines(draw, subtitle_lines, subtitle_font, margin, y, 16, CFG.body_color)

    footer = "Deslize para continuar"
    draw_shadow_text(draw, (margin, h - 120), footer, small_font, CFG.accent_color)
    draw_shadow_text(draw, (w - 130, h - 120), f"{index}/{total}", small_font, CFG.muted_color)

    return base


def create_content_slide(background: Image.Image, slide_data: dict, index: int, total: int) -> Image.Image:
    base = create_base_slide(background)
    base = draw_glass_card(base, (60, 120, 1020, 1180), CFG.card_overlay)
    draw = ImageDraw.Draw(base)

    w, h = base.size
    margin = 95
    content_width = w - (margin * 2)

    title_font = load_font(CFG.section_title_font_size, bold=True)
    body_font = load_font(CFG.body_font_size)
    small_font = load_font(CFG.small_font_size)

    draw_progress_bar(draw, index, total, margin, 62, 500, 12)

    draw.rounded_rectangle([(margin, 98), (margin + 170, 108)], radius=5, fill=CFG.accent_color)

    title_lines = fit_text_lines(draw, slide_data["title"], title_font, content_width, 2)
    body_lines = fit_text_lines(draw, slide_data["body"], body_font, content_width, CFG.content_max_lines)

    y = 155
    y = draw_lines(draw, title_lines, title_font, margin, y, 14, CFG.title_color)
    y += 32

    y = draw_lines(draw, body_lines, body_font, margin, y, 16, CFG.body_color)

    footer = "Leitura rápida, clara e útil"
    draw_shadow_text(draw, (margin, h - 105), footer, small_font, CFG.accent_color)
    draw_shadow_text(draw, (w - 130, h - 105), f"{index}/{total}", small_font, CFG.muted_color)

    return base


def create_cta_slide(background: Image.Image, slide_data: dict, index: int, total: int) -> Image.Image:
    base = create_base_slide(background)
    base = draw_glass_card(base, (70, 190, 1010, 1160), CFG.cta_overlay)
    draw = ImageDraw.Draw(base)

    w, h = base.size
    margin = 110
    content_width = w - (margin * 2)

    title_font = load_font(CFG.cta_title_font_size, bold=True)
    body_font = load_font(CFG.body_font_size)
    small_font = load_font(CFG.small_font_size)

    draw_progress_bar(draw, index, total, margin, 72, 500, 12)

    title_lines = fit_text_lines(draw, slide_data["title"], title_font, content_width, 2)
    body_lines = fit_text_lines(draw, slide_data["body"], body_font, content_width, CFG.cta_body_max_lines)

    y = 320
    y = draw_lines(draw, title_lines, title_font, margin, y, 16, (18, 18, 18))
    y += 34
    y = draw_lines(draw, body_lines, body_font, margin, y, 18, (28, 28, 28))

    draw.rounded_rectangle(
        [(margin, h - 185), (margin + 420, h - 115)],
        radius=24,
        fill=(28, 28, 28)
    )
    draw_shadow_text(draw, (margin + 28, h - 166), "Salve e compartilhe este post", body_font, (255, 255, 255))
    draw_shadow_text(draw, (w - 130, h - 105), f"{index}/{total}", small_font, (28, 28, 28))

    return base


def create_slide(background: Image.Image, slide_data: dict, index: int, total: int) -> Image.Image:
    slide_type = slide_data["type"]

    if slide_type == "cover":
        return create_cover_slide(background, slide_data, index, total)
    if slide_type == "cta":
        return create_cta_slide(background, slide_data, index, total)
    return create_content_slide(background, slide_data, index, total)


# ══════════════════════════════════════════════════════════════════
# CAROUSEL BUILD
# ══════════════════════════════════════════════════════════════════
def build_caption(carousel_data: dict) -> str:
    title = sanitize_text(carousel_data["title"])
    body = smart_truncate(carousel_data["body"], CFG.caption_body_limit)

    return (
        f"{title}\n\n"
        f"{body}\n\n"
        "Salve este carrossel para revisar depois.\n\n"
        f"{CFG.hashtags}"
    )


def generate_carousel(background: Image.Image, carousel_data: dict) -> tuple[list[Path], str]:
    CFG.output_dir.mkdir(parents=True, exist_ok=True)

    slides = carousel_data["slides"][:CFG.max_slides]
    paths = []

    for idx, slide in enumerate(slides, start=1):
        slide_img = create_slide(background, slide, idx, len(slides))
        path = CFG.output_dir / f"slide_{idx}.jpg"
        slide_img.save(path, format="JPEG", quality=93, optimize=True)
        paths.append(path)

    caption = build_caption(carousel_data)
    return paths, caption


# ══════════════════════════════════════════════════════════════════
# LOGIN INSTAGRAM
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


# ══════════════════════════════════════════════════════════════════
# PUBLICAÇÃO
# ══════════════════════════════════════════════════════════════════
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=3, min=10, max=30),
    reraise=True,
)
def publish_carousel_to_instagram(paths: List[Path], caption: str) -> bool:
    cl = get_instagram_client()
    media = cl.album_upload(paths=[str(p) for p in paths], caption=caption)
    log.info("Carrossel publicado com sucesso. Media PK: %s", getattr(media, "pk", "N/A"))
    return True


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    log.info("═" * 60)
    log.info("Instagram RSS Carousel Poster Premium — iniciando")
    log.info("═" * 60)

    try:
        entries = fetch_rss_entries(CFG.rss_url)
    except Exception as exc:
        log.error("Erro ao buscar RSS: %s", exc)
        sys.exit(1)

    entry = random.choice(entries)
    log.info("Entrada selecionada: %s", sanitize_text(entry.get("title", "N/A")))

    try:
        background = get_best_image(entry)
    except Exception as exc:
        log.error("Erro ao obter imagem: %s", exc)
        sys.exit(1)

    try:
        carousel_data = build_ux_carousel_text(entry)
        paths, caption = generate_carousel(background, carousel_data)
    except Exception as exc:
        log.error("Erro ao gerar carrossel: %s", exc)
        sys.exit(1)

    try:
        ok = publish_carousel_to_instagram(paths, caption)
        sys.exit(0 if ok else 1)
    except Exception as exc:
        log.error("Erro crítico na publicação: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()