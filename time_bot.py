import feedparser
from random import seed
from random import randint
import textwrap

from PIL import Image 
from PIL import ImageFont
from PIL import ImageDraw
from datetime import datetime
import urllib.request
from PIL import Image

W,H = (1080,1080)

urllib.request.urlretrieve(
  'https://source.unsplash.com/1080x1080/?black',
   "gfg.png")
  
img = Image.open("gfg.png")

draw = ImageDraw.Draw(img)

d = feedparser.parse('https://sucesso.hmr1973.com/feed/')

qtde = (len(d['entries']))-1
#seed(1)
value = randint(0, qtde)

titulo = d['entries'][value]['title'] 
corpo = d['entries'][value]['description'] 
corpo1 = d['entries'][value]['description']

corpo1 = corpo1.replace("Quero saber mais sobre como ter sucesso no mundo digital", "")

corpo = corpo.replace("[&#8230;]", "...")

text = '\n\n' + titulo + '\n\n' + corpo + '\n\nfonte: https://sucesso.hmr1973.com/ \n\n#love #instagood #photooftheday #beautiful #followme #happy #picoftheday #instadaily #fun #instalike #likeforlike #follow #selfie #summer #art #fashion #food #travel #nature #fitness #beauty #workout #friends #family #instamood #photography'

font = ImageFont.truetype("Roboto-Medium.ttf", 60)
font1 = ImageFont.truetype("Roboto-Medium.ttf", 40)

textwrapped = textwrap.wrap(titulo, width=35)
draw.text((0,0), '\n'.join(textwrapped), font=font, fill="#FFA500")

textwrapped1 = textwrap.wrap(corpo1, width=50)
draw.text((0,700), '\n'.join(textwrapped1), font=font1, fill="#FFA500")

img.save('cur_time.jpg')

import os

from instauto.api.client import ApiClient
from instauto.api import structs as st
from instauto.api.actions import post as ps


if os.path.isfile('./.instauto.save'):
    client = ApiClient.initiate_from_file('./.instauto.save')
else:
    client = ApiClient(username=os.environ.get("INSTAUTO_USER") or "hmr1973maia", password=os.environ.get("INSTAUTO_PASS") or "Mkonji32!!!?")
    client.log_in()
    client.save_to_disk('./.instauto.save')

post = ps.PostFeed(path='./cur_time.jpg',caption=text)
resp = client.post_post(post, 80)
print("Success: ", resp.ok)