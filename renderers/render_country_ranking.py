# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from bs4 import BeautifulSoup as bs4
import requests

from models import PlayerTournament, Ruleset
from config import HTMLPATH
from utils.ema_jinja import jinja

# TODO these will all go into a css file at some point,
#      but for now, they're easy to edit here
PAGE_STYLES = '''

'''

class Render_Results:

    def __init__(self, db):
        self.db = db
        r = requests.get("https://silk.mahjong.ie/template-country-ranking")
        self.template = r.content


    def one_ruleset(self, rules: Ruleset) -> None:

        for c in self.db.query(Country).filter(Country.id != "??").filter(
                Country.ema_since is not None):


        dom = bs4(self.template, "html.parser")
        dom.select_one("style").append(PAGE_STYLES)
        print('.', end='')
        pt = self.db.query(PlayerTournament).filter(
            PlayerTournament.tournament_id == t.id).all()

        zone = dom.find(id="tablepress-3")
        country_count = self.fill_results_table(zone, t, pt)

        results_zone = dom.find(id="main")

        template = jinja.from_string(str(results_zone))
        new_text = template.render(t=t)
        results_zone.replace_with(bs4(new_text, "html.parser"))

        count_table = dom.new_tag('table')
        count_table['id'] = 'emaflagtable'
        caption = dom.new_tag('caption')
        caption.string = 'Countries represented'
        row1 = dom.new_tag('tr')
        row2 = dom.new_tag('tr')
        row3 = dom.new_tag('tr')

        counts = sorted(country_count.items(), key=lambda x:x[1], reverse=True)
        for pair in counts:
            row1.append(bs4(f'<td>{pair[0]}</td>', features="html.parser"))
            row2.append(bs4(f'<td><img src=/flag/{pair[0]}.png></td>',
                            features="html.parser"))
            row3.append(bs4(f'<td>{pair[1]}</td>', features="html.parser"))

        count_table.insert(0, row3)
        count_table.insert(0, row2)
        count_table.insert(0, row1)
        count_table.insert(0, caption)
        main_area = dom.find('div', {'class': 'entry-content'})
        main_area.insert(len(main_area), count_table)

        dom.find(id='colophon').replace_with(bs4(
            f'''<footer class="site-footer" role="contentinfo">Page last cached:
            {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')}
            </footer>''',
            features="html.parser"))

        with open(HTMLPATH / "Tournaments" / f"{t.id}.html",
                  "w",
                  encoding='utf-8') as file:
            file.write(str(dom))

        # add a permanent redirect from the old pathname too
        midfix = "RCR_" if t.ruleset == Ruleset.riichi else ""
        with open(HTMLPATH / "Tournaments" / f"TR_{midfix}_{t.old_id}.html", "w",
                  encoding='utf-8') as file:
            file.write(f'''<?php
                       header("HTTP/1.1 301 Moved Permanently");
                       header("Location: /ranking/Tournament/{t.id}.html");
                       exit();''')
