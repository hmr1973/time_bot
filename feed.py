import feedparser
from random import seed
from random import randint

d = feedparser.parse('https://sucesso.hmr1973.com/feed/')

qtde = (len(d['entries']))-1
#seed(1)
value = randint(0, qtde)

titulo = d['entries'][value]['title'] 
corpo = d['entries'][value]['description'] 

corpo = corpo.replace("[&#8230;]", "...")

text = '\n\n' + titulo + '\n\n' + corpo + '\n\nfonte: https://sucesso.hmr1973.com/ \n\nFollow me @hmr1973maia \n\n#bigdata #weworklabs #entrepreneur #innovation #cycling #datascience #innovation #technology #tech #design #business #engineering #startup #entrepreneur #science #entrepreneurship #future #marketing #creativity #architecture #sustainability #inspiration #ai #art #gadgets #digital #motivation #automation'


print (text)
