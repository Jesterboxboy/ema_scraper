# -*- coding: utf-8 -*-
import jinja2
import requests
from bs4 import BeautifulSoup as bs
from models import Player, RulesetClass
from config import DBPATH, HTMLPATH
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

def percent_format(val: float):
    return f"{round(val*100)}%"

def datetime_format(value, format="%Y-%m-%d"):
    return value.strftime(format)

jinja = jinja2.Environment()
jinja.filters["date"] = datetime_format
jinja.filters["pc"] = percent_format

engine = create_engine(DBPATH, poolclass=NullPool)

id = "07000155" # lots in each ruleset
# id = "14990047" # riichi only
# id = "07000002" # mcr only

TOGGLER = """<script>
jQuery(function onready() {
    jQuery('.ematoggler').on('click', function displayhiddenresults(e) {
        jQuery('.emahide0', e.target.parentNode).toggle();
        e.target.remove();
    });
});
</script>"""

r = requests.get("https://silk.mahjong.ie/template-player")

def fill_player_tournament_table(rules, results):
    print(rules)
    zone = dom.find(id=f"{rules}_results")
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
        tbody.append(bs(new_row, 'html.parser'))
        if r.tournament.age_factor == 0:
            results_to_hide += 1

    if results_to_hide:
        # TODO add a toggle to show tournaments with age 0
        toggler = bs(
            f"<a class=ematoggler>Show the {results_to_hide} results that no longer contribute to rank</a>",
            "html.parser"
            )
        zone.append(toggler)

    # remove the template row, we've finished with it now
    row.decompose()

with Session(engine) as db:
    p = db.query(Player).filter(Player.ema_id == id).first()
    dom = bs(r.content, "html.parser")
    dom.select_one("style").append('.emahide0 {display: none;}')
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
    player_zone.replace_with(bs(new_text, "html.parser"))

    fill_player_tournament_table('mcr', mcr)
    fill_player_tournament_table('riichi', riichi)
    dom.body.append(bs(TOGGLER, "html.parser"))

with open(HTMLPATH / "Players" / f"{id}.html", "w", encoding='utf-8') as file:
    file.write(str(dom))
