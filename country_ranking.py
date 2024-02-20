# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from scrapers import Country_Scraper
from models import Player, Country, RulesetClass
from ranking import PlayerRankingEngine

class CountryRankingEngine:
    """ rank the countries
    for a given ruleset. The ranking is based on the average rank for the
    top 3 players in each country. If a country has less than three players
    then the sum of the country's players' rankings is nevertheless divided
    by 3"""
    def __init__(self, db):
        self.db = db

    def rank_countries_for_one_ruleset(
            self,
            ruleset: RulesetClass,
            write_to_db: bool = True,
            reckoning_day: datetime = None,
            assess: bool = False,
            ):

        if reckoning_day is not None:
            PlayerRankingEngine(self.db).rank_all_players(reckoning_day)

        ema = [] # list of ema countries
        is_mcr = ruleset == RulesetClass.mcr
        rules = str(ruleset).replace("RulesetClass.", "")

        all_players = self.db.query(Player).filter(
            Player.ema_id != -1).filter(Player.country_id != "??").filter(
            getattr(Player, f"{rules}_rank") != None).order_by(
            getattr(Player, f"{rules}_rank").desc())

        all_700plus = all_players.filter(
            getattr(Player, f"{rules}_rank") > 700)

        self.player_count = len(all_players.all())
        self.players700plus = len(all_700plus.all())
        for c in self.db.query(Country).filter(Country.id != "??"): # .filter(Country.ema_since is not None):
            c.ema_since = None if c.id in ("ru", "by") else datetime.now()
            c_all = all_players.filter(Player.country_id == c.id)
            player_count = len(c_all.all())
            c_700plus = len(
                all_700plus.filter(Player.country_id == c.id).all()
                )
            setattr(c, f"player_count_{rules}", player_count)
            setattr(c, f"over700_{rules}", c_700plus)
            setattr(c, f"propn_of_all_players_700plus_{rules}",
                    c_700plus / self.players700plus)
            setattr(c, f"propn_of_all_ranked_players_{rules}",
                    player_count / self.player_count)
            setattr(c, f"country_ranking_{rules}", None)
            if player_count > 0:
                top3 = c_all.limit(3)
                top3ranks = [getattr(p, f"{rules}_rank") for p in top3]
                average_rank_of_top3_players = round(sum(top3ranks)/3, 2)
            else:
                average_rank_of_top3_players = None

            setattr(c, f"average_rank_of_top3_players_{rules}",
                    average_rank_of_top3_players)

            if average_rank_of_top3_players is not None:
                ema.append([c.id, average_rank_of_top3_players, player_count])

        ema.sort(key=lambda x: x[1], reverse=True)

        if assess:
            total = 0
            bad = 0
            suffix = "MCR" if is_mcr else "RCR"
            url = f"https://silk.mahjong.ie/ranking/BestNation_{suffix}.html"
            official = Country_Scraper.scrape_country_rankings(url)


        pos = 1
        logging.info(f"Country rankings for {ruleset}")
        for q in ema:
            c = self.db.query(Country).filter_by(id=q[0]).first()
            setattr(c, f"country_ranking_{rules}", pos)

            if assess:
                test = official[pos-1]
                total += 1
                if q[0] != test['country']:
                    bad += 1
                    logging.warning(f"#{pos} Country mismatch- official {test['country']}, we think {q.id}")
                    continue
                if q[2] != test['player_count']:
                    bad += 1
                    logging.warning(f"#{pos} player count mismatch- official {test['player_count']}, we think {q.player_count}")
                    continue
                if abs(q[1] - test['top3_average']) > 0.02:
                    bad += 1
                    logging.warning(f"#{pos} top3 average mismatch- official {test['top3_average']}, we think {q.average_rank_of_top3_players}")
                    continue

            pos += 1

        if assess:
            logging.info(f"{total} rows tested, {bad} rows bad")

        self.db.commit()
