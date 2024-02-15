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

# Base rank = Int(1000 * (NT - rank) / (NT - 1)) . This is fixed at end of tournament and won't change (possibly unless someone is later disqualified)

# A tournament has a real last day of tournament (for calendar purposes) and a weighting day of tournament (for age-weighting calculation)
# For almost all tournaments, these two days are the same date
# For exactly five tournaments during the covid era, they have a weighting day equal to ZZZ, regardless of their real last day.

# Age penalty is calculated given a specific day of reckoning (e.g. today, or some date set for calculating quora for quorum-based tournaments such as EMA or WRC):
# Tournaments with reckoning day - weighting day <= 1 year: 1.0
# Tornaments with reckoning day - weighting day > 1 year, <= 2 years: 0.5
# Tournaments with reckoning day - weighting day > 2 years: 0

# A tournament weighting on a reckoning day = MERS * age penalty for that reckoning day. This will be the same for all players in the tournament.

# Part A = weighted average of the best (based on base rank) NA results from the 2 years prior to the reckoning day

# PN is the number of tournaments that player has played in the 2 years prior to the reckoning day
# NA is the number of tournaments that Part A accounts for. It equals ceil(5+0.8*(Max(PN-5, 0)))

# Part B = weighted averge of the best (based on base rank) NB results from the 2 years prior to the reckoning day
# NB = 4

# Final ranking = 0.5 * Part A + 0.5 * Part B

# ================================================
#
#          PROGRAM FLOW
#
# ================================================

# Get reckoning day
# Get ruleset
# Get list of players to be updated (default to all who have a number of tournaments for this ruleset >= 1)

# ================================================
#
#          BITS OF CODE
#
# ================================================

from datetime import date, datetime
from math import ceil

from sqlalchemy import update

from models import Player, Tournament, PlayerTournament, Country, RulesetClass

class RankingEngine:
    def __init__(self, db):
        self.db = db

    def yearsPrior(self, years: int, toDate: datetime) -> datetime:
        # this is a bit contrived, but it doesn't choke on leap years
        return toDate + (date(toDate.year - years, 1, 1) - date(toDate.year, 1, 1))

    def calculate_base_rank(self, position: int, player_count: int):
        return round(1000 * (player_count - position) / (player_count - 1))

    # For all tournaments, given reckoning day, age the tournament MERS weighting
    def weight_tournaments(self, reckoning_day: datetime):
        expiry_day = self.yearsPrior(2, reckoning_day)
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
        self.db.execute(update(PlayerTournament).values(aged_rank =
            PlayerTournament.aged_mers * PlayerTournament.base_rank))
        self.db.commit()

def get_all_tournaments_for_player(player_id):
    return "SELECT tournament_id, aged_mers, ruleset, base_rank FROM tournaments_x_players WHERE player_id=$1 SORT BY end_date DESC", player_id


# For a given player, get list of all tournament IDs, base rank, and tournament weighting, that they have a tournament weighting > 0 for.
def get_ranked_tournaments_for_player(tournaments):
    if len(tournaments) < 2:
        return []
    while len(tournaments) < 5:
        tournaments.push({'tournament_id': 0, 'aged_mers': 1, 'base_rank': 0})
    number_eligible = ceil(5 + 0.8*max(len(tournaments) - 5, 0))
    return tournaments[0:number_eligible]


def get_eligible_tournaments_for_player(tournaments, ruleset):
    filtered_tournaments = [t for t in tournaments if t.aged_mers > 0 and t.ruleset == ruleset]
    results = sorted(filtered_tournaments, key=lambda t: t.base_rank, reverse=True)
    return get_ranked_tournaments_for_player(results)


def calculate_ranking_for_player(player_id, ruleset):
    get_ranked_tournaments_for_player(player_id, ruleset)


# For each player, loop over ranking calculations
