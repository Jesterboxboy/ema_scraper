# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import xlrd

from models import Player, Tournament, PlayerTournament, RulesetClass, Country
from scrapers import Tournament_Scraper

def results_to_db(db, file):
    book = xlrd.open_workbook(file)
    sh = book.sheet_by_index(0)

    # first create tournament
    title = sh.cell_value(rowx=2, colx=1)
    player_count = sh.cell_value(rowx=2, colx=2)
    country3 = sh.cell_value(rowx=2, colx=12)
    location = sh.cell_value(rowx=2, colx=13)
    mers = sh.cell_value(rowx=2, colx=14)
    rules = sh.cell_value(rowx=2, colx=16)
    raw_date = sh.cell_value(rowx=2, colx=17)
    start_date, end_date = Tournament_Scraper(db).parse_dates(raw_date, title)

    country = db.query(Country).filter(Country.old3 == country3).first()
    if country is None:
        logging.warning(f"{country3} is not on file")

    t = Tournament()
    t.title= location.title()
    t.country = country
    t.place = location
    t.raw_date = raw_date
    t.start_date = start_date
    t.end_date = t.effective_end_date = end_date
    t.mers = mers
    t.player_count = player_count
    t.scraped_on = datetime.now()
    t.ruleset = RulesetClass.riichi if rules.lower() == "riichi" \
        else RulesetClass.mcr
    db.add(t)
    db.commit()

    # cycle through each result in turn
    for rx in range(1,player_count+1):
        position = sh.cell_value(rowx=rx, colx=3)
        first_name = sh.cell_value(rowx=rx, colx=4)
        last_name = sh.cell_value(rowx=rx, colx=5)
        ema_id = sh.cell_value(rowx=rx, colx=6)
        table_points = sh.cell_value(rowx=rx, colx=7)
        score = sh.cell_value(rowx=rx, colx=8)
        is_ema = sh.cell_value(rowx=rx, colx=9)

        country3 = sh.cell_value(rowx=rx, colx=10)
        country = db.query(Country).filter(Country.old3 == country3).first()
        if country is None:
            logging.warning(f"{country3} is not on file")

        # check if player is in db already
        p = db.query(Player).filter(Player.old_id==ema_id).first()

        if p is None:
            # create player
            p = Player()
            p.old_id = ema_id if is_ema else "-1"
            p.calling_name = f"{first_name} {last_name}"
            p.country = country
            db.add(p)
            db.commit()

        # create result
        pt = PlayerTournament()
        pt.tournament = t
        pt.player = p
        pt.position = position
        pt.table_points = table_points
        pt.score = score
        db.add(pt)
        db.commit()


    results_to_db()
