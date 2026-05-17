import os
import textwrap
import random
import urllib.request
from io import BytesIO

import feedparser
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from instagrapi import Client

# ============================================
# CONFIGURAÇÕES
# ============================================

load_dotenv()

RSS_FEED_URL = "https://sucesso.hmr1973.com/feed/"
IMAGE_URL = "https://picsum.photos/1080/1080"

OUTPUT_IMAGE = "instagram_post.jpg"
SESSION_FILE = "session.json"

FONT_PATH = "Roboto-Medium.ttf"

FONT_SIZE_TITLE = 55
FONT_SIZE_BODY = 32

TEXT_COLOR = (255, 165, 0)
BODY_COLOR = (255, 255, 255)

RECTANGLE_HEIGHT = 420

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# ============================================
# DOWNLOAD IMAGEM
# ============================================

def download_image(url):
    try:
        response = urllib.request.urlopen(url)
        return Image.open(BytesIO(response.read())).convert("RGBA")

    except Exception as e:
        print(f"Erro ao baixar imagem: {e}")
        return None


# ============================================
# RSS
# ============================================

def fetch_feed(url):
    try:
        feed = feedparser.parse(url)

        if not feed.entries:
            raise Exception("Feed sem entradas")

        return feed.entries

    except Exception as e:
        print(f"Erro RSS: {e}")
        return []


# ============================================
# TEXTO
# ============================================

def prepare_caption(entry):

    titulo = entry.get("title", "")

    corpo = entry.get("summary", "")
    corpo = corpo.replace(
        "Quero saber mais sobre como ter sucesso no mundo digital",
        ""
    )

    corpo = corpo.replace("[…]", "...")

    hashtags = """
#sucesso #marketingdigital #empreendedorismo #negocios
#motivacao #mindset #empreender #instagram
#marketing #business #digital #foco
"""

    caption = f"""
{titulo}

{corpo}

Fonte: {RSS_FEED_URL}

{hashtags}
"""

    return caption.strip()


# ============================================
# DESENHAR TEXTO
# ============================================

def draw_multiline_text(draw, text, font, x, y, color, max_width=28):

    lines = textwrap.wrap(text, width=max_width)

    current_y = y

    for line in lines:

        bbox = draw.textbbox((0, 0), line, font=font)

        text_width = bbox[2] - bbox[0]

        centered_x = (1080 - text_width) / 2

        draw.text(
            (centered_x, current_y),
            line,
            font=font,
            fill=color
        )

        current_y += bbox[3] - bbox[1] + 10

    return current_y


# ============================================
# CRIAR IMAGEM
# ============================================

def create_post_image(background, entry):

    try:

        img = background.resize((1080, 1080)).convert("RGBA")

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))

        overlay_draw = ImageDraw.Draw(overlay)

        overlay_draw.rectangle(
            [(0, 0), (1080, RECTANGLE_HEIGHT)],
            fill=(0, 0, 0, 180)
        )

        img = Image.alpha_composite(img, overlay)

        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype(
                FONT_PATH,
                FONT_SIZE_TITLE
            )

            body_font = ImageFont.truetype(
                FONT_PATH,
                FONT_SIZE_BODY
            )

        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        titulo = entry.get("title", "")

        corpo = entry.get("summary", "")
        corpo = corpo.replace("[…]", "...")

        y = 40

        y = draw_multiline_text(
            draw,
            titulo,
            title_font,
            40,
            y,
            TEXT_COLOR,
            24
        )

        y += 20

        draw_multiline_text(
            draw,
            corpo[:180],
            body_font,
            40,
            y,
            BODY_COLOR,
            40
        )

        final_img = img.convert("RGB")

        final_img.save(
            OUTPUT_IMAGE,
            quality=95
        )

        return True

    except Exception as e:
        print(f"Erro ao criar imagem: {e}")
        return False


# ============================================
# LOGIN INSTAGRAM
# ============================================

def instagram_login():

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise Exception(
            "Defina INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD no .env"
        )

    cl = Client()

    try:

        if os.path.exists(SESSION_FILE):

            print("Carregando sessão existente...")

            cl.load_settings(SESSION_FILE)

        cl.login(
            INSTAGRAM_USERNAME,
            INSTAGRAM_PASSWORD
        )

        cl.dump_settings(SESSION_FILE)

        print("Login realizado com sucesso")

        return cl

    except Exception as e:

        print(f"Erro login Instagram: {e}")

        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)

        return None


# ============================================
# POSTAR
# ============================================

def post_to_instagram(client, image_path, caption):

    try:

        media = client.photo_upload(
            image_path,
            caption
        )

        print("Post publicado com sucesso")
        print(f"Media ID: {media.id}")

        return True

    except Exception as e:

        print(f"Erro ao postar: {e}")

        return False


# ============================================
# MAIN
# ============================================

def main():

    print("Baixando imagem...")
    background = download_image(IMAGE_URL)

    if not background:
        return

    print("Lendo feed RSS...")
    entries = fetch_feed(RSS_FEED_URL)

    if not entries:
        return

    entry = random.choice(entries)

    print("Criando imagem...")
    success = create_post_image(background, entry)

    if not success:
        return

    caption = prepare_caption(entry)

    print("Fazendo login Instagram...")
    client = instagram_login()

    if not client:
        return

    print("Publicando post...")
    post_to_instagram(
        client,
        OUTPUT_IMAGE,
        caption
    )

    print("Finalizado")


# ============================================

if __name__ == "__main__":
    main()