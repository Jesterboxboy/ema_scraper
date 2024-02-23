# -*- coding: utf-8 -*-
import jinja2
import requests
from bs4 import BeautifulSoup as bs
import re
from models import Player

jinja = jinja2.Environment()

r = requests.get("https://silk.mahjong.ie/template-player")
dom = bs(r.content, "html.parser")

p_fields = dom.find_all(string=re.compile("{{p."))
p = Player()
p.calling_name = 'test person 1'
p.country_id = 'ie'

for pf in p_fields:
    f = pf.string
    t = jinja.from_string(f)
    new_text = t.render(p=p)
    pf.replace_with(new_text)

with open("p1.html", "w", encoding='utf-8') as file:
    file.write(str(dom))
