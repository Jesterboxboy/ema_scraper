# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from bs4 import BeautifulSoup as bs4
import jinja2
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from models import Player, RulesetClass
from config import DBPATH, HTMLPATH

def percent_format(val: float):
    return f"{round(val*100)}%"

def datetime_format(value, format="%Y-%m-%d"):
    return value.strftime(format)

# TODO these will all go into a css file at some point,
#      but for now, they're easy to edit here
PAGE_STYLES = '''
.ematoggler {cursor:pointer;}
.emahide0 {display: none;}
#mcr_results, #riichi_results {
    border-top: 1px solid #aaf;
    padding-top: 1em;
    margin-top: 1em;
}
.dataTables_filter input[type="search"] {color: #060;}
footer.site-footer {
    color: #666;
    font-size: 0.8em;
    text-align: center;
}
'''

jinja = jinja2.Environment()
jinja.filters["date"] = datetime_format
jinja.filters["pc"] = percent_format

engine = create_engine(DBPATH, poolclass=NullPool)

TOGGLER = """<script>
jQuery(function onready() {
    jQuery('.ematoggler').on('click', function displayhiddenresults(e) {
        jQuery('.emahide0', e.target.parentNode).toggle();
        e.target.remove();
    });
});
</script>"""

class Render_Player:
    def __init__(self, db):
        self.db = db
        r = requests.get("https://silk.mahjong.ie/template-player")
        self.template = r.content

    def fill_player_tournament_table(self, dom, rules, results):
        zone = dom.find(id=f"{rules}_results")
        if not(len(results)):
            zone.decompose()
            return
        tbody = zone.find("tbody")
        row = tbody.find("tr")
        row['class'].append(
            '{% if not t.tournament.age_factor %}emahide0{% endif %}')

        results.sort(
                key=lambda t: t.tournament.end_date,
                reverse=True,
                )

        results_to_hide = 0
        for r in results:
            j = jinja.from_string(str(row))
            new_row = j.render(t=r)
            tbody.append(bs4(new_row, 'html.parser'))
            if r.tournament.age_factor == 0:
                results_to_hide += 1

        if results_to_hide:
            # add a toggle to show tournaments with age 0
            toggler = bs4(
                f'''<a class=ematoggler>Show the {results_to_hide} results that
                no longer contribute to rank</a>''',
                "html.parser"
                )
            zone.append(toggler)

        # remove the template row, we've finished with it now
        row.decompose()

    def one_player(self, id):
        print('.', end='')
        p = self.db.query(Player).filter(Player.ema_id == id).first()
        dom = bs4(self.template, "html.parser")
        dom.select_one("style").append(PAGE_STYLES)
        # allocate tournaments to rulesets, most recent first
        riichi = []
        mcr = []
        for r in p.tournaments:
            if r.ruleset == RulesetClass.riichi:
                riichi.append(r)
            else:
                mcr.append(r)

        player_zone = dom.find(id="player_data")

        t = jinja.from_string(str(player_zone))
        new_text = t.render(p=p)
        player_zone.replace_with(bs4(new_text, "html.parser"))

        self.fill_player_tournament_table(dom, 'mcr', mcr)
        self.fill_player_tournament_table(dom, 'riichi', riichi)

        dom.find(id='colophon').replace_with(bs4(
            f'''<footer class="site-footer" role="contentinfo">Updated:
            {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')}
            </footer>''',
            features="html.parser"))
        dom.body.append(bs4(TOGGLER, "html.parser"))
        with open(HTMLPATH / "Players" / f"{id}.html", "w", encoding='utf-8') as file:
            file.write(str(dom))

        with open(HTMLPATH / "Players" / f"{p.ema_id}.html", "w",
                  encoding='utf-8') as file:
            file.write(f'''<?php
                       header("HTTP/1.1 301 Moved Permanently");
                       header("Location: /ranking/Players/{id}.html");
                       exit();''')
