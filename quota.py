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
from datetime import date, datetime
from math import ceil

from sqlalchemy import update

from models import Player, Country, RulesetClass
from ranking import PlayerRankingEngine


class Quota():
    id: str # iso2
    over700: int # number of players with personal rank over 7000
    # number of ranked players / total EMA-wide number of ranked players
    propnOfAllRankedPlayers: float
    propnOfAllPlayers700plus: float
    averageRankOfTop3Players: float
    countryRanking: int


class CountryRankingEngine: # NONE OF THE BELOW WORKS YET
    def __init__(self, db, reckoning_day: datetime = datetime.now()):
        self.dummy = Country()
        self.db = db
        PlayerRankingEngine().rank_all_players(reckoning_day)
        # TODO count how many players are ranked over 700
        self.players700plus = 1
        # TODO count how many ranked players there are
        self.playerCount = 1

    def rank_countries(self):
        """ based on average ranking of top 3 players """
        # TODO
        for c in self.db.query(Country):
            pass


class QuotaMaker():
    def __init(self):
        pass
