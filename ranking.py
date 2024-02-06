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

from math import ceil
from sqlalchemy import sql_execute, sql_query_all

# For all tournaments, given reckoning day, calculate tournament weighting
def weight_tournaments(reckoning_day, exclusion_period, halving_period):
    check1 = sql_execute("UPDATE tournaments SET age = DURATION(:date, effective_end_date)",
                         {"date": reckoning_day})
    limits = {"expiry": exclusion_period, "reducer": halving_period}
    check2 = sql_execute(
        "UPDATE tournaments SET weighting = 0 IF age > :expiry",
        limits)
    check3 = sql_execute(
        "UPDATE tournaments SET weighting = 0.5 IF age > :reducer AND age <= :expiry",
        limits)
    check4 = sql_execute(
        "UPDATE tournaments SET weighting = 1 IF age <= :reducer",
        limits)
    check5 = sql_execute(
        "UPDATE tournaments_x_players JOIN tournaments ON tournament_id SET tournaments_x_players.weighting=tournaments.weighting")


def get_all_tournaments_for_player(player_id):
    results = sql_query_all("SELECT tournament_id, weighting, ruleset, base_rank FROM tournaments_x_players WHERE player_id=$1 SORT BY end_date DESC", player_id)
    return results


# For a given player, get list of all tournament IDs, base rank, and tournament weighting, that they have a tournament weighting > 0 for.
def get_ranked_tournaments_for_player(tournaments):
    if len(tournaments) < 2:
        return []
    while len(tournaments) < 5:
        tournaments.push({'tournament_id': 0, 'weighting': 1, 'base_rank': 0})
    number_eligible = ceil(5 + 0.8*max(len(tournaments) - 5, 0))
    return tournaments[0:number_eligible]


def get_eligible_tournaments_for_player(tournaments, ruleset):
    filtered_tournaments = [t for t in tournaments if t.weighting > 0 and t.ruleset == ruleset]
    results = sorted(filtered_tournaments, key=lambda t: t.base_rank, reverse=True)
    return get_ranked_tournaments_for_player(results)


def calculate_ranking_for_player(player_id, ruleset):
    get_ranked_tournaments_for_player(player_id, ruleset)


# For each player, loop over ranking calculations
