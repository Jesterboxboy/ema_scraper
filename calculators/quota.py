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
# Each EMA country has at least 1 seat.


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


# ================================================
#
#          Code starts here
#
# ================================================

import logging

from models import Player, Country, RulesetClass

class QuotaMaker():
    def __init__(self, db, quota: int, ruleset: RulesetClass):
        self.db = db
        self.total = quota
        self.remaining = quota
        self.rules = "mcr" if ruleset == RulesetClass.mcr else "riichi"
        self.quotas = []

    def seat(self, idx: int, seats: int = 1):
        if seats < 0:
            logging.error("Asked to allocate {seats} to country #{idx}")
        seats = min(self.remaining,
                    seats,
                    self.quotas[idx]["cap"] - self.quotas[idx]["quota"],
                    )
        self.remaining -= seats
        self.quotas[idx]["quota"] += seats

    def calc_caps(self):
        self.quotas = []
        self.remaining = self.total
        self.partB_sum = 0

        players = self.db.query(Player).filter(
            Player.ema_id != -1).filter(
            Player.country_id != "??")
        players = players.filter(getattr(Player, f"{self.rules}_rank") != None)
        rank_column = f"{self.rules}_rank"
        player_count = len(players.all())
        self.average = sum(getattr(p, rank_column) for p in players) \
            / player_count

        player700_count = 0
        for c in self.countries:
            player700_count += getattr(c, f"over700_{self.rules}")

        for pos, c in enumerate(self.countries):
            local_players = players.filter(Player.country_id==c.id)
            partB1 = getattr(c, f"player_count_{self.rules}") / player_count
            partB2 = getattr(c, f"over700_{self.rules}") / player700_count
            partB3 = (partB1 + partB2) / 2
            self.partB_sum += partB3

            cap = len(local_players.filter(
                getattr(Player, rank_column) > self.average).all())
            self.quotas.append({
                "cap": max(1, cap),
                "quota": 0,
                "partB2": partB2,
                "partB3": partB3,
                })

            # PART A2

            self.seat(pos) # ensure at least one seat per country

    def make(self):
        self.countries = self.db.query(Country).filter(
            Country.id != "??").filter(
            Country.ema_since != None).order_by(getattr(
            Country, f"average_rank_of_top3_players_{self.rules}").desc())
        self.calc_caps()

        # PART A1 - 1 seat for each of the top 3

        for pos, c in enumerate(self.quotas):
            self.seat(pos)
            if pos > 1:
                break

        # PART A3 - 1 seat for each country with at least one player over 700

        for pos, c in enumerate(self.quotas):
            if c["partB2"] > 0:
                self.seat(pos)

        # redistribution proportional to PART B3

        for pos, c in enumerate(self.quotas):
            self.seat(pos, int(self.remaining * c["partB3"]))

        # Final redistribution based on ranking

        while self.remaining:
            remaining = self.remaining
            for pos, c in enumerate(self.quotas):
                self.seat(pos)
            if remaining == self.remaining:
                logging.error("unable to allocate remaining {remaining} seats")
                break
        self.wrap_up()

    def wrap_up(self):
        """ save our quotas somewhere """ # TODO
        logging.info(f"\n QUOTAS for {self.rules}, total {self.total}\n")
        for pos, c in enumerate(self.quotas):
            logging.info(f"#{pos+1} {self.countries[pos].name_english} {c}") # ['quota']}/{c['cap']
        if self.remaining:
            logging.info(f"{self.remaining} unable to be allocated")
        else:
            logging.info("full quota allocated")
