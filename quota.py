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
from datetime import datetime

from sqlalchemy import update, and_

from models import Player, Country, RulesetClass
from ranking import PlayerRankingEngine


class Quota():
    ''' stores contributing variables, and quota, for a specific country
    for a specific ruleset '''
    id: str # iso2
    player_count: int # number of qualifying players
    over700: int # number of players with personal rank over 700
    # number of ranked players / total EMA-wide number of ranked players
    propnOfAllRankedPlayers: float
    # number of 700+ players / total EMA-wide number of 700+ players
    propnOfAllPlayers700plus: float
    averageRankOfTop3Players: float
    countryRanking: int


class CountryRankingEngine: # NONE OF THE BELOW WORKS YET
    def __init__(
            self,
            db,
            ruleset: RulesetClass,
            reckoning_day: datetime = datetime.now()
            ):
        self.db = db
        self.ema = [] # list of ema countries

        self.ruleset = ruleset
        # PlayerRankingEngine(db).rank_all_players(reckoning_day)
        is_mcr = ruleset == RulesetClass.MCR
        if is_mcr:
            all_players = db.query(Player).filter(
                Player.ema_id != -1).filter(Player.mcr_rank != None
                ).order_by(Player.mcr_rank.desc())
            all_700plus = all_players.filter(Player.mcr_rank > 700)
        else:
            all_players = db.query(Player).filter(
                and_(Player.ema_id != -1, Player.riichi_rank != None
                )).order_by(Player.riichi_rank.desc())
            all_700plus = all_players.filter(Player.riichi_rank > 700)

        self.player_count = len(all_players.all())
        self.players700plus = len(all_700plus.all())
        for c in db.query(Country): # .filter(Country.ema_since is not None):
            if c.id == "??":
                continue
            q = Quota()
            q.id = c.id
            c_all = all_players.filter(Player.country_id == c.id)
            q.player_count = len(c_all.all())
            c_700plus = len(
                all_700plus.filter(Player.country_id == c.id).all()
                )
            q.propnOfAllPlayers700plus = c_700plus / self.players700plus
            q.propnOfAllRankedPlayers = q.player_count / self.player_count
            if q.player_count > 0:
                top3 = c_all.limit(3)
                top3ranks = [
                    p.mcr_rank for p in top3
                    ] if is_mcr else [
                    p.riichi_rank for p in top3
                    ]
                # top3ranks = [
                #     p.mcr_rank for p in top3 if p.mcr_rank is not None
                #     ] if is_mcr else [
                #     p.riichi_rank for p in top3 if p.riichi_rank is not None
                #     ]

                q.averageRankOfTop3Players = round(sum(top3ranks)/3, 2)
            else:
                q.averageRankOfTop3Players = None

            if q.averageRankOfTop3Players is not None:
                self.ema.append(q)
        self.ema.sort(
            key=lambda q:q.averageRankOfTop3Players,
            reverse=True,
            )


    def rank_countries(self):
        """ based on average ranking of top 3 players """
        pos = 1
        for q in self.ema:
            q.countryRanking = pos
            logging.info(f"#{pos}  {q.id}  {q.player_count}  {q.averageRankOfTop3Players}")
            pos += 1


class QuotaMaker():
    def __init(self):
        pass
