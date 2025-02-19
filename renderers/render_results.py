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
#emaflagtable {
    width: auto;
    margin:auto;
}
'''

class Render_Results:

    def __init__(self, db):
        self.db = db
        r = requests.get("https://silk.mahjong.ie/template-results")
        self.template = r.content

    def fill_results_table(self, zone, tournament, results) -> dict[str, int]:

        if not len(results):
            zone.decompose()
            return

        tbody = zone.find("tbody")
        row = tbody.find("tr")
        results.sort(key=lambda pt: pt.position)
        country_count = {}

        for pt in results:
            j = jinja.from_string(str(row))
            new_row = j.render(pt=pt, t=tournament, p=pt.player)
            tbody.append(bs4(new_row, 'html.parser'))
            # count players by country
            if pt.country_id is None:
                pass
            elif pt.country_id in country_count:
                country_count[pt.country_id] += 1
            else:
                country_count[pt.country_id] = 1

        # remove the template row, we've finished with it now
        row.decompose()
        return country_count

    def one_tournament(self, t) -> None:
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
