# ================================================
#
#          RANKING ALGORITHM
#
# ================================================


# 0 <= EMA Ranking <= 1000

# Must have two tournaments with non-zero weighting to have a ranking
# Less than 5 tournaments, each missing one gets score 0, weight 1.
# First = 1000 base rank
# Last = 0 base rank
# NT = total number of players in tournament

# Base rank = Int(1000 * (NT - rank) / (NT - 1)) . This is fixed at end of
# tournament and won't change (possibly unless someone is later disqualified)

# A tournament has a real last day of tournament (for calendar purposes) and a
#  weighting day of tournament (for age-weighting calculation)
# For almost all tournaments, these two days are the same date
# For exactly five tournaments during the covid era, they have a weighting day
# equal to 1 July 2022, regardless of their real last day.

# Age penalty is calculated given a specific day of reckoning (e.g. today, or
# some date set for calculating quora for quorum-based tournaments such as EMA or WRC):
# Tournaments with reckoning day - weighting day <= 1 year: 1.0
# Tornaments with reckoning day - weighting day > 1 year, <= 2 years: 0.5
# Tournaments with reckoning day - weighting day > 2 years: 0

# A tournament weighting on a reckoning day = MERS * age penalty for that
# reckoning day. This will be the same for all players in the tournament.

# Part A = weighted average of the best (based on base rank) NA results from
# the 2 years prior to the reckoning day

# PN is the number of tournaments that player has played in the 2 years
# prior to the reckoning day
# NA is the number of tournaments that Part A accounts for.
# It equals ceil(5+0.8*(Max(PN-5, 0)))

# Part B = weighted averge of the best (based on base rank) NB
# results from the 2 years prior to the reckoning day
# NB = 4

# Final ranking = 0.5 * Part A + 0.5 * Part B

# ================================================
#
#          Code starts here
#
# ================================================

from datetime import date, datetime
from math import ceil

from sqlalchemy import update

from models import Player, Tournament, PlayerTournament, Country, RulesetClass

class PlayerRankingEngine:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def yearsPrior(years: int, toDate: datetime) -> datetime:
        # this is a bit contrived, but it doesn't choke on leap years
        return toDate + (date(toDate.year - years, 1, 1) - date(toDate.year, 1, 1))

    @staticmethod
    def calculate_base_rank(player_count: int, position: int):
        return round(1000 * (player_count - position) / (player_count - 1))

    def weight_tournaments(self, reckoning_day: datetime):
        """For all tournaments, given reckoning day,
        age the tournament MERS weighting, and apply this aged MERS weighting
        to each tournament result"""
        expiry_day = datetime(2019,11,8) # Because of covid freeze. self.yearsPrior(2, reckoning_day)
        halving_day = self.yearsPrior(1, reckoning_day)
        self.db.execute(update(Tournament).
            where(Tournament.effective_end_date < expiry_day).
            values(aged_mers = 0.0))
        self.db.execute(update(Tournament).
            where(Tournament.effective_end_date >= expiry_day).
            where(Tournament.effective_end_date < halving_day).
            values(aged_mers = Tournament.mers * 0.5))
        self.db.execute(update(Tournament).
            where(Tournament.effective_end_date > halving_day).
            values(aged_mers = Tournament.mers))
        self.db.execute(update(PlayerTournament).values(aged_mers =
            Tournament.aged_mers).
            where(Tournament.id == PlayerTournament.tournament_id))
        self.db.commit()

    def get_all_results_for_player(self, player_id):
        """For a given player, get list of all tournament IDs, base rank,
        and tournament weighting, that have a non-zero weight"""
        return self.db.query(PlayerTournament).filter_by(player_id=player_id)

    def get_all_eligible_results_for_player(self, player_id):
        """ for a given player, get all results with a non-zero weighting"""
        all = self.get_all_results_for_player(player_id)
        return all.filter(PlayerTournament.aged_mers > 0)

    @staticmethod
    def weighted_average(ranks, weights):
        return sum([a * b for a, b in zip(ranks, weights)])/ sum(weights)

    def rank_one_player_for_one_ruleset(self, player, ruleset, results):
        """well, this doesn't work yet, but it does do something that
        isn't completely wrong"""
        eligible = self.get_ranked_tournaments_for_player(
            results.filter_by(
            ruleset=ruleset).order_by(
            PlayerTournament.base_rank.desc()).all())

        if eligible is None:
            player.rank(ruleset, None)
            return

        weights = [t.aged_mers for t in eligible]
        ranks = [t.base_rank for t in eligible]
        partA = self.weighted_average(ranks, weights)

        weights = [t.aged_mers for t in eligible[0:4]]
        ranks = [t.base_rank for t in eligible[0:4]]
        partB = self.weighted_average(ranks, weights)
        player.rank(ruleset, 0.5 * partA + 0.5 * partB)

    def get_ranked_tournaments_for_player(self, results):
        """ given a list of results, return the ones that are eligible for
        ranking"""
        if len(results) < 2:
            return None
        while len(results) < 5:
            results.append(PlayerTournament(
                tournament_id=0,
                aged_mers=1.0,
                base_rank=0.0))
        number_eligible = ceil(5 + 0.8*max(len(results) - 5, 0))
        return results[0:number_eligible]

    # ===========================================
    # nothing below here works yet

    def find_all_live_players(self):
        """ """
        players = self.db.query(Player).all()
        for p in players:
            results = self.get_all_eligible_results_for_player(p.id)
            for ruleset in RulesetClass:
                self.rank_one_player_for_one_ruleset(p, ruleset, results)


class CountryRankingEngine:
    pass
