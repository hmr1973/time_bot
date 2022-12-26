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

corpo = corpo.replace("[&#8230;]", "...")

text = '\n\n' + titulo + '\n\n' + corpo + '\n\nfonte: https://sucesso.hmr1973.com/ \n\nFollow me @hmr1973maia \n\n#bigdata #weworklabs #entrepreneur #innovation #cycling #datascience #innovation #technology #tech #design #business #engineering #startup #entrepreneur #science #entrepreneurship #future #marketing #creativity #architecture #sustainability #inspiration #ai #art #gadgets #digital #motivation #automation'

font = ImageFont.truetype("Roboto-Medium.ttf", 100)

textwrapped = textwrap.wrap(titulo, width=24)
draw.text((0,0), '\n'.join(textwrapped), font=font, fill="#FFA500")

img.save('cur_time.jpg')

