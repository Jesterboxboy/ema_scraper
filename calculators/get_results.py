# -*- coding: utf-8 -*-
'''
import from the existing xls results workbook
'''
import logging
from datetime import datetime, timedelta

import xlrd

from models import Player, Tournament, PlayerTournament, RulesetClass, Country
from utils.scrapers import Tournament_Scraper
from calculators.ranking import PlayerRankingEngine

def results_to_db(db, file: str, sheet: str) -> Tournament:
    book = xlrd.open_workbook(file)
    sh = book.sheet_by_name(sheet)

    t = Tournament()
    t.old_id = -1
    t.title = sh.cell_value(rowx=2, colx=0)
    t.place = sh.cell_value(rowx=2, colx=12)
    t.player_count = int(sh.cell_value(rowx=2, colx=1))
    t.scraped_on = datetime.now()
    t.mers = sh.cell_value(rowx=2, colx=13)
    t.raw_date = sh.cell_value(rowx=2, colx=16)

    rules = sh.cell_value(rowx=2, colx=15)
    t.ruleset = RulesetClass.riichi if rules.lower() == "riichi" \
        else RulesetClass.mcr

    t.start_date, t.end_date = Tournament_Scraper.parse_dates(
        t.raw_date, t.title)
    day_count = sh.cell_value(rowx=2, colx=17)
    end_date2 = t.start_date + timedelta(days=day_count)
    t.effective_end_date = t.end_date

    country3 = sh.cell_value(rowx=2, colx=11)
    t.country = db.query(Country).filter(Country.old3 == country3).first()
    db.add(t)
    db.commit()
    if t.country is None:
        logging.warning(f"{country3} is not on file for tournament {t.id}")
    if t.end_date != end_date2:
        logging.warning(
            f'Mismatch between parsed end date {t.end_date} and calculated '
            f'end_date {end_date2} for tournament {t.id}')

    # cycle through each result in turn
    for rx in range(1, t.player_count + 1):
        position = int(sh.cell_value(rowx=rx, colx=2))
        first_name = sh.cell_value(rowx=rx, colx=3)
        last_name = sh.cell_value(rowx=rx, colx=4)
        ema_id = str(int(sh.cell_value(rowx=rx, colx=5)))
        if len(ema_id) == 7:
            ema_id = f'0{ema_id}'
        is_ema = sh.cell_value(rowx=rx, colx=8)

        country3 = sh.cell_value(rowx=rx, colx=9)
        country = db.query(Country).filter(Country.old3 == country3).first()
        if country is None:
            logging.warning(f"{country3} is not on file")

        # check if player is in db already
        p = db.query(Player).filter(Player.ema_id==ema_id).first()

        if p is None:
            # create player
            p = Player()
            p.ema_id = ema_id if is_ema else "-1"
            p.calling_name = f"{first_name} {last_name}"
            p.country = country
            db.add(p)
            db.commit()

        # create result
        pt = PlayerTournament()
        pt.tournament = t
        pt.base_rank = PlayerRankingEngine.calculate_base_rank(
            t.player_count,
            position)
        pt.player = p
        pt.country = country
        pt.position = position
        pt.table_points = sh.cell_value(rowx=rx, colx=6)
        pt.score = int(sh.cell_value(rowx=rx, colx=7))
        pt.ruleset = t.ruleset
        pt.was_ema = p.ema_id == "-1"
        db.add(pt)

    db.commit()

    return t
