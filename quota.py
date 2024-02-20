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
        self.is_mcr = ruleset == RulesetClass.MCR

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
        if self.is_mcr:
            players = players.filter(Player.mcr_rank != None)
            average = sum(p.mcr_rank for p in players) / len(players.all())
        else:
            players = players.filter(Player.riichi_rank != None)
            average = sum(p.riichi_rank for p in players) / len(players.all())

        for c in countries:
            self.quotas.append(self.seat()) # ensure at least one seat per country
            self.caps.append(max(1, len(players)))

    def make(self):
        countries = self.db.query(Country).filter(Country.id != "??") # .filter(Country.ema_since > 0)
        for c in countries:
            self.quotas.append(self.seat()) # ensure at least one seat per country


class Quota():
    ''' stores contributing variables, and quota, for a specific country
    for a specific ruleset '''
    id: str # iso2
    player_count: int # number of qualifying players
    over700: int # number of players with personal rank over 700
    # number of ranked players / total EMA-wide number of ranked players
    propn_of_all_ranked_players: float
    # number of 700+ players / total EMA-wide number of 700+ players
    propn_of_all_players_700plus: float
    average_rank_of_top3_players: float
    country_ranking: int


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
        """ this has become a big sprawly function which ranks the countries
        for a given ruleset. The ranking is based on the average rank for the
        top 3 players in each country. If a country has less than three players
        then the sum of the country's players' rankings is divided by 3"""

        if reckoning_day is not None:
            PlayerRankingEngine(self.db).rank_all_players(reckoning_day)

        ema = [] # list of ema countries

        is_mcr = ruleset == RulesetClass.MCR
        if is_mcr:
            all_players = self.db.query(Player).filter(
                Player.ema_id != -1).filter(Player.mcr_rank != None
                ).order_by(Player.mcr_rank.desc())
            all_700plus = all_players.filter(Player.mcr_rank > 700)
        else:
            all_players = self.db.query(Player).filter(
                Player.ema_id != -1).filter(Player.riichi_rank != None
                ).order_by(Player.riichi_rank.desc())
            all_700plus = all_players.filter(Player.riichi_rank > 700)

        self.player_count = len(all_players.all())
        self.players700plus = len(all_700plus.all())
        for c in self.db.query(Country): # .filter(Country.ema_since is not None):
            if c.id == "??":
                continue
            q = Quota()
            q.id = c.id
            c_all = all_players.filter(Player.country_id == c.id)
            q.player_count = len(c_all.all())
            c_700plus = len(
                all_700plus.filter(Player.country_id == c.id).all()
                )
            q.propn_of_all_players_700plus = c_700plus / self.players700plus
            q.propn_of_all_ranked_players = q.player_count / self.player_count
            if q.player_count > 0:
                top3 = c_all.limit(3)
                top3ranks = [
                    p.mcr_rank for p in top3
                    ] if is_mcr else [
                    p.riichi_rank for p in top3
                    ]
                q.average_rank_of_top3_players = round(sum(top3ranks)/3, 2)
            else:
                q.average_rank_of_top3_players = None

            if q.average_rank_of_top3_players is not None:
                ema.append(q)
        ema.sort(
            key=lambda q:q.average_rank_of_top3_players,
            reverse=True,
            )

        if assess:
            total = 0
            bad = 0
            if is_mcr:
                url = "https://silk.mahjong.ie/ranking/BestNation_MCR.html"
            else:
                url = "https://silk.mahjong.ie/ranking/BestNation_RCR.html"

            official = Country_Scraper.scrape_country_rankings(url)

        pos = 1
        logging.info(f"Country rankings for {ruleset}")
        for q in ema:
            c = self.db.query(Country).filter_by(id=q.id).first()
            # yes, I know this is ugly. It works. There must be a cleaner way
            # to do it. Please make it cleaner. Please make the mess go away.
            if is_mcr:
                c.country_ranking_MCR = pos
                c.player_count_MCR = q.player_count
                c.over700_MCR = c_700plus
                c.average_rank_of_top3_players_MCR = q.average_rank_of_top3_players
                c.propn_of_all_ranked_players_MCR = q.propn_of_all_ranked_players
                c.propn_of_all_players_700plus_MCR = q.propn_of_all_players_700plus
            else:
                c.country_ranking_riichi = pos
                c.player_count_riichi = q.player_count
                c.over700_riichi = c_700plus
                c.average_rank_of_top3_players_riichi = q.average_rank_of_top3_players
                c.propn_of_all_ranked_players_riichi = q.propn_of_all_ranked_players
                c.propn_of_all_players_700plus_riichi = q.propn_of_all_players_700plus

            if assess:
                test = official[pos-1]
                total += 1
                if q.id != test['country']:
                    bad += 1
                    logging.warning(f"#{pos} Country mismatch- official {test['country']}, we think {q.id}")
                    continue
                if q.player_count != test['player_count']:
                    bad += 1
                    logging.warning(f"#{pos} player count mismatch- official {test['player_count']}, we think {q.player_count}")
                    continue
                if abs(q.average_rank_of_top3_players - test['top3_average']) > 0.02:
                    bad += 1
                    logging.warning(f"#{pos} top3 average mismatch- official {test['top3_average']}, we think {q.average_rank_of_top3_players}")
                    continue

            pos += 1

        if assess:
            logging.info(f"{total} rows tested, {bad} rows bad")

        self.db.commit()
