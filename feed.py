import math
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

urllib.request.urlretrieve(
  'https://source.unsplash.com/1080x1080/',
   "gfg.png")
  
img = Image.open("gfg.png")

draw = ImageDraw.Draw(img)

d = feedparser.parse('https://sucesso.hmr1973.com/feed/')
 
w, h = 1080, 300
shape = [(0, 0), (w, h)]
 
# create  rectangleimage
img1 = ImageDraw.Draw(img)  
draw.rectangle(shape, fill ="#000000", outline ="black")

qtde = (len(d['entries']))-1
#seed(1)
value = randint(0, qtde)

titulo = d['entries'][value]['title'] 
corpo = d['entries'][value]['description'] 
corpo1 = d['entries'][value]['description']

corpo1 = corpo1.replace("Quero saber mais sobre como ter sucesso no mundo digital", "")

corpo = corpo.replace("[&#8230;]", "...")

text = '\n\n' + titulo + '\n\n' + corpo + '\n\nfonte: https://sucesso.hmr1973.com/ \n\nFollow me @hmr1973maia \n\n#bigdata #weworklabs #entrepreneur #innovation #cycling #datascience #innovation #technology #tech #design #business #engineering #startup #entrepreneur #science #entrepreneurship #future #marketing #creativity #architecture #sustainability #inspiration #ai #art #gadgets #digital #motivation #automation'

font = ImageFont.truetype("Roboto-Medium.ttf", 65)
font1 = ImageFont.truetype("Roboto-Medium.ttf", 40)

textwrapped = textwrap.wrap(titulo, width=30)
draw.text((0,10), '\n'.join(textwrapped), font=font, fill="#FFA500")

textwrapped1 = textwrap.wrap(corpo1, width=50)
#draw.text((0,700), '\n'.join(textwrapped1), font=font1, fill="#FFA500")

img.save('cur_time.jpg')

