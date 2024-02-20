# ================================================
#
#          COUNTRY QUOTA ALGORITHM
#
# ================================================

# T is the total number of seats to be allocated

# Part A
# A1 = One seat for the 3 best EMA countries in the country ranking list
# A2 = One seat for all EMA countries.
# A3 = One seat for all countries who have players with a ranking > 700 points

# Part B
# B1 = Percent of players in ranking list (country / Total)
# B2 = Percent of players with ranking >700 points (country / Total)
# B3 = Average between B1 and B2

# Quotas before Penalty and Redistribution
# T = Total quota for EMA
# Quotas Q = [A1+A2+A3] + B3*[T-SumAllCountries(PartA)]

# For this part [ B3*[T-SumAllCountries(PartA)] ], we use a recursive method,
# decided by EMA GA 2019

# Limits and Penalty

# Each country can’t get more seats than numbers of players who have
# ranking > global average rank.
# An EMA country can’t have a quota of 0 seats.
# Each EMA country has at least 1 seat.

#
# Redistribution

# One uses the module of redistribution to refine the quotas if need be,
# with the rise or the fall, according the “top ranking country”.

# A country can’t get more seats than numbers of players who have
# ranking > global average rank. So, we will give seats to others if necessary.

#     Example1: before redistribution, we have 2 seats to give.
# So, the 2 best countries (in country ranking list) will have 1 seat more.
#
#     Example2: before redistribution, we have 2 seats to give.
# The 3 best countries have already reached the max (can’t get more than
# average). So, we give seats to countries ranked at 4 and 5 in the ranking
# list.
#

# ================================================
#
#          Code starts here
#
# ================================================

import logging
import sys
from datetime import datetime

from scrapers import Country_Scraper
from models import Player, Country, RulesetClass
from ranking import PlayerRankingEngine


class QuotaMaker(): # doesn't work, nothing here yet
    def __init(self, db, quota: int, ruleset: RulesetClass):
        self.db = db
        self.total = quota
        self.quotas = []
        self.caps = []
        self.rules = "mcr" if ruleset == RulesetClass.mcr else "riichi"

    def seat(self, number: int = 1):
        self.total -= number
        if self.total < 0:
            logging.error(f"allocated {-self.total} more seats than available!")
            print("quota broken")
            sys.exit(-1)
        return number

    def calc_caps(self, countries):
        players = self.db.query(Player).filter(
            Player.ema_id != -1).filter(
            Player.country_id != "??")
        players = players.filter(Player.mcr_rank != None)
        average = sum(p.mcr_rank for p in players) / len(players.all())

        for c in countries:
            self.quotas.append(self.seat()) # ensure at least one seat per country
            self.caps.append(max(1, len(players)))

    def make(self):
        countries = self.db.query(Country).filter(Country.id != "??") # .filter(Country.ema_since > 0)
        for c in countries:
            self.quotas.append(self.seat()) # ensure at least one seat per country


class CountryRankingEngine:
    def __init__(self, db):
        self.db = db

    def rank_countries_for_one_ruleset(
            self,
            ruleset: RulesetClass,
            write_to_db: bool = True,
            reckoning_day: datetime = None,
            assess: bool = False,
            ):
        """ rank the countries
        for a given ruleset. The ranking is based on the average rank for the
        top 3 players in each country. If a country has less than three players
        then the sum of the country's players' rankings is nevertheless divided
        by 3"""

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
            if player_count > 0:
                top3 = c_all.limit(3)
                top3ranks = [
                    p.mcr_rank for p in top3
                    ] if is_mcr else [
                    p.riichi_rank for p in top3
                    ]
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
