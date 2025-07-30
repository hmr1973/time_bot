import math
import feedparser
from random import randint
import textwrap
from PIL import Image, ImageFont, ImageDraw
import urllib.request
import os
from instauto.api.client import ApiClient
from instauto.api.actions import post as ps
import pyotp
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Constantes
IMAGE_URL = 'https://picsum.photos/1080/1080'
FONT_PATH = "Roboto-Medium.ttf"  # Certifique-se de que esta fonte existe no sistema
OUTPUT_IMAGE = 'cur_time.jpg'
RSS_FEED_URL = 'https://sucesso.hmr1973.com/feed/'
TEXT_COLOR = "#FFA500"  # Laranja
FONT_SIZE_TITLE = 65
RECTANGLE_HEIGHT = 300

def download_image(url, output_path):
    """Baixa uma imagem de uma URL e a salva localmente."""
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"Erro ao baixar imagem: {e}")
        return False

def fetch_rss_feed(url):
    """Obtém e analisa o feed RSS."""
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            raise ValueError("Nenhuma entrada encontrada no feed RSS")
        return feed
    except Exception as e:
        print(f"Erro ao obter feed RSS: {e}")
        return None

def create_image_with_text(background_path, feed_entry):
    """Cria uma imagem com texto sobreposto do feed RSS."""
    try:
        # Abre a imagem de fundo
        img = Image.open(background_path)
        draw = ImageDraw.Draw(img)

        # Desenha um retângulo preto semitransparente no topo
        w, h = img.size
        shape = [(0, 0), (w, RECTANGLE_HEIGHT)]
        draw.rectangle(shape, fill=(0, 0, 0, 180))  # Preto semitransparente

        # Carrega a fonte
        try:
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE_TITLE)
        except IOError:
            print("Arquivo de fonte não encontrado, usando fonte padrão")
            font = ImageFont.load_default()

        # Prepara o texto
        titulo = feed_entry['title']
        corpo = feed_entry['description'].replace(
            "Quero saber mais sobre como ter sucesso no mundo digital", ""
        ).replace("[…]", "...")

        caption = f"\n\n{titulo}\n\n{corpo}\n\nfonte: {RSS_FEED_URL}\n\n#love #instagood #photooftheday #beautiful #followme #happy #picoftheday #instadaily #fun #instalike #likeforlike #follow #selfie #summer #art #fashion #food #travel #nature #fitness #beauty #workout #friends #family #instamood #photography"

        # Quebra e desenha o título
        textwrapped = textwrap.wrap(titulo, width=30)
        draw.text((10, 10), '\n'.join(textwrapped), font=font, fill=TEXT_COLOR)

        # Salva a imagem
        img.save(OUTPUT_IMAGE)
        return caption
    except Exception as e:
        print(f"Erro ao criar imagem: {e}")
        return None

def post_to_instagram(image_path, caption, username, password, two_factor_seed):
    """Posta a imagem no Instagram usando instauto."""
    try:
        # Valida a chave 2FA e gera o código para depuração
        if two_factor_seed:
            try:
                totp = pyotp.TOTP(two_factor_seed)
                two_factor_code = totp.now()
                print(f"Código 2FA gerado: {two_factor_code} (insira manualmente se solicitado)")
            except Exception as e:
                print(f"Erro ao gerar código 2FA: {e}")

        if os.path.isfile('./.instauto.save'):
            client = ApiClient.initiate_from_file('./.instauto.save')
        else:
            if not username or not password:
                raise ValueError("Credenciais do Instagram não fornecidas")
            # Configura o cliente
            client = ApiClient(
                username=username,
                password=password
            )
            # Faz login sem passar two_factor_code diretamente
            client.log_in()
            client.save_to_disk('./.instauto.save')

        post = ps.PostFeed(path=image_path, caption=caption)
        resp = client.post_post(post, quality=80)
        print("Sucesso: ", resp.ok)
        return resp.ok
    except Exception as e:
        print(f"Erro ao postar no Instagram: {e}")
        return False

def main():
    # Baixa a imagem de fundo
    if not download_image(IMAGE_URL, "background.png"):
        return

    # Obtém o feed RSS
    feed = fetch_rss_feed(RSS_FEED_URL)
    if not feed:
        return

    # Seleciona uma entrada aleatória
    entry = feed.entries[randint(0, len(feed.entries) - 1)]

    # Cria a imagem com texto
    caption = create_image_with_text("background.png", entry)
    if not caption:
        return

    # Posta no Instagram com as credenciais fornecidas
    username = os.getenv("INSTAGRAM_USERNAME") or "hmr1973maia"  # Substitua pelo seu nome de usuário
    password = os.getenv("INSTAGRAM_PASSWORD") or "Mkonji321????"  # Substitua pela sua senha
    two_factor_seed = os.getenv("INSTAGRAM_2FA_SEED") or "BW64LFQ6L54HTGDKMED5E73J7HY46QVH"  # Substitua pela chave 2FA
    post_to_instagram(OUTPUT_IMAGE, caption, username, password, two_factor_seed)

if __name__ == "__main__":
    main()
