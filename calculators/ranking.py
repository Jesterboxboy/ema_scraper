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

import logging
from datetime import date, datetime
from math import ceil

from sqlalchemy import update

from models import Player, Tournament, PlayerTournament, Ruleset, Settings

class PlayerRankingEngine:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def yearsPrior(years: int, toDate: datetime) -> datetime:
        # this is a bit contrived, but it doesn't choke on leap years
        return toDate + (date(toDate.year - years, 1, 1) - date(toDate.year, 1, 1))

    @staticmethod
    def calculate_base_rank(player_count: int, position: int) -> int:
        return round(1000 * (player_count - position) / (player_count - 1))

    @staticmethod
    def weighted_average(ranks, weights):
        return sum([a * b for a, b in zip(ranks, weights)])/ sum(weights)

    def weight_tournaments(self, reckoning_day: datetime):
        """For all tournaments, given reckoning day,
        age the tournament MERS weighting, and apply this aged MERS weighting
        to each tournament result"""
        expiry_day = self.yearsPrior(2, reckoning_day)
        halving_day = self.yearsPrior(1, reckoning_day)
        self.db.execute(update(Tournament).
            where(Tournament.effective_end_date < expiry_day).
            values(age_factor = 0.0))
        self.db.execute(update(Tournament).
            where(Tournament.effective_end_date >= expiry_day).
            where(Tournament.effective_end_date < halving_day).
            values(age_factor = 0.5))
        self.db.execute(update(Tournament).
            where(Tournament.effective_end_date > halving_day).
            values(age_factor = 1.0))

        # this is for when we are retrospectively calculating historic quota
        self.db.execute(update(Tournament).
            where(Tournament.end_date > reckoning_day).
            values(age_factor = 0.0))

        # finally, weight all the results by the aged MERS factors
        self.db.execute(update(PlayerTournament).values(aged_mers =
            Tournament.age_factor * Tournament.mers).
            where(Tournament.id == PlayerTournament.tournament_id))
        self.db.commit()

    def rank_player(self, p):
        ''' calculate both MCR and riichi ranking for a given player '''
        # get all results with a non-zero weighting
        results = [r for r in p.tournaments if r.aged_mers > 0]
        for ruleset in Ruleset:
            self.rank_one_player_for_one_ruleset(p, ruleset, results)


    def rank_one_player_for_one_ruleset(self, player, ruleset, results=None):
        """ this contains the main ranking algorithm """
        # do some argument-parsing to allow this function to be called in
        # different ways. This is very convenient during testing
        if type(player) == str:
            player = self.db.query(Player).filter_by(ema_id=player).first()
        if results is None:
            results = [r for r in player.tournaments if r.aged_mers > 0]

        # filter results to only those for this ruleset
        eligible = self.get_ranked_tournaments_for_player(
            [r for r in results if r.ruleset == ruleset]
            )

        if eligible is None:
            player.rank(ruleset, None)
            return

        # part A is a weighted average of all eligible results
        weights = [t.aged_mers for t in eligible]
        ranks = [round(t.base_rank) for t in eligible]
        partA = self.weighted_average(ranks, weights)

        # part B is a weighted average of the top 4 results, ranked by base rank
        weights = [t.aged_mers for t in eligible[0:4]]
        ranks = [round(t.base_rank) for t in eligible[0:4]]
        partB = self.weighted_average(ranks, weights)

        # final ranking is a straight average of part A and part B
        player.rank(ruleset, 0.5 * partA + 0.5 * partB)

    def get_ranked_tournaments_for_player(self, results):
        """ given a list of results, return the ones that are eligible for
        ranking. If there are fewer than 2 eligible, then the player
        isn't eligible to have a ranking yet.
        Otherwise, if they have 2-4 qualifying results, then pad the list out
        with dummy results that have base rank 0, weight 1.
        And if they have more than 5 results, return the best """
        if len(results) < 2:
            return None
        # sort the results in descending base_rank order (and by highest mers to break ties)
        results.sort(key=lambda s: -s.base_rank - s.aged_mers/1000)
        # pad the list to at least 5 results
        while len(results) < 5:
            results.append(PlayerTournament(
                tournament_id=0,
                aged_mers=1.0,
                base_rank=0.0))

        # cap the eligible number of results at 5 + 80% of the amount over 5
        number_eligible = ceil(5 + 0.8*max(len(results) - 5, 0))
        return results[0:number_eligible]

    # TODO it would be nice to be able to do this for just one ruleset
    def rank_all_players(self, reckoning_day:datetime = None, assess=False):
        """ cycle through all players, and rank each in turn """
        self.weight_tournaments(reckoning_day or datetime.now())
        players = self.db.query(Player).all()
        for p in players:
            self.rank_player(p)
        self.db.commit()
        # now calculate each player's position in the rankings
        for rules in ('mcr', 'riichi'):
            players = self.db.query(Player).filter(
                        Player.ema_id != -1).filter(
                        getattr(Player, f"{rules}_rank") != None).order_by(
                        getattr(Player, f"{rules}_rank").desc()).all()
            self.db.query(Settings).filter_by(
                key=f"player_count_{rules}").update({"value": len(players)})
            i = 1
            for p in players:
                setattr(p, f"{rules}_position", i)
                i += 1
        self.db.commit()

        if assess:
            self.assess_player_ranking()

    def assess_player_ranking(self):
        total = 0
        bad = 0
        acceptable = 0.02
        for p in self.db.query(Player).all():
            total +=1
            for rules in ("mcr", "riichi"):
                official = getattr(p, f"{rules}_official_rank")
                ours = getattr(p, f"{rules}_rank")
                if (official is None and ours is not None) or (
                        official is not None and ours is None):
                    this_bad = True
                elif official is None and ours is None:
                    this_bad = False
                elif abs(official - ours) < acceptable:
                    this_bad = False
                else:
                    this_bad = True

                if this_bad:
                    bad += 1
                    logging.warning(
                        f"mismatch for {p.calling_name} {p.ema_id}: "
                        f"official {rules} rank is {official}. "
                        f"But We calculate {ours}.")

        logging.info(f"{total} player ranks calculated, of which {bad} were bad")
