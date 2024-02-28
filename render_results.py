# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from bs4 import BeautifulSoup as bs4
import jinja2
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from models import Player, Tournament, PlayerTournament, Country, RulesetClass
from config import DBPATH, HTMLPATH

def percent_format(val: float):
    return f"{round(val*100)}%"

def datetime_format(value, format="%Y-%m-%d"):
    return value.strftime(format)

jinja = jinja2.Environment()
jinja.filters["date"] = datetime_format
jinja.filters["pc"] = percent_format

engine = create_engine(DBPATH, poolclass=NullPool)


def fill_results_table(zone, tournament, results):

    if not len(results):
        zone.decompose()
        return

    tbody = zone.find("tbody")
    row = tbody.find("tr")
    results.sort(key=lambda pt: pt.position)

    for pt in results:
        j = jinja.from_string(str(row))
        new_row = j.render(pt=pt, t=tournament, p=pt.player)
        tbody.append(bs4(new_row, 'html.parser'))

    # remove the template row, we've finished with it now
    row.decompose()

def one_tournament(db, r, t):
    dom = bs4(r.content, "html.parser")
    print('.', end='')
    pt = db.query(PlayerTournament).filter(
        PlayerTournament.tournament_id == t.id).all()

    zone = dom.find(id="tablepress-3")
    fill_results_table(zone, t, pt)

    results_zone = dom.find(id="main")

    template = jinja.from_string(str(results_zone))
    new_text = template.render(t=t)
    results_zone.replace_with(bs4(new_text, "html.parser"))

    dom.find(id='colophon').replace_with(bs4(
        f'''<footer class="site-footer" role="contentinfo">Page last cached:
        {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')}
        </footer>''',
        features="html.parser"))

    with open(HTMLPATH / "Tournaments" / f"{t.id}.html", "w", encoding='utf-8') as file:
        file.write(str(dom))

    # add a permanent redirect from the old pathname too
    midfix = "RCR_" if t.ruleset == RulesetClass.riichi else ""
    with open(HTMLPATH / "Tournaments" / f"TR_{midfix}_{t.id}.html", "w",
              encoding='utf-8') as file:
        file.write(f'''<?php
                   header("HTTP/1.1 301 Moved Permanently");
                   header("Location: /ranking/Tournament/{t.id}.html");
                   exit();''')


with Session(engine) as db:
    r = requests.get("https://silk.mahjong.ie/template-results")
    t = db.query(Tournament).filter(Tournament.ruleset == RulesetClass.mcr
        ).filter(Tournament.old_id == 373).first()
    one_tournament(db, r, t)

#
