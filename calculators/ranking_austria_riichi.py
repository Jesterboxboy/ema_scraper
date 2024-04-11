# ================================================
#
#          RANKING ALGORITHM
#
# ================================================
# A players ranking consists of the sum of all austrian tournaments,
# and the best three foreign tournaments in the period between the quota cutoff date for
# the last WRC or ERMC and the quota cutoff date for the event for which the quota is calculated.
# i.e. for any given WRC, the period stretches from the cutoff date from the last WRC to the
# cutoff date of the next one.

# Points for tournaments are awarded by the following formula where R denotes the rank of the player,
# and A the total number of participants for a tournament.
#
# Playerpoints = (1000/(A/2))*((A/2)-R+1)
#
# This means that a player gets points between 0 and 1000 points if he places in the upper half a
# given tournament.
# ================================================
#
#          Code starts here
#
# ================================================

import logging
from datetime import date, datetime
from math import ceil

from sqlalchemy import update

from models import Player, Tournament, PlayerTournament, RulesetClass, Settings

class PlayerRankingEngine:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def yearsPrior(years: int, toDate: datetime) -> datetime:
        # this is a bit contrived, but it doesn't choke on leap years
        return toDate + (date(toDate.year - years, 1, 1) - date(toDate.year, 1, 1))

    @staticmethod
    def calculate_base_rank(player_count: int, position: int) -> int:
        return round(1000/(player_count/2)*((player_count/2)-position+1))

    def rank_one_player_for_one_ruleset(self, player, ruleset, aut_results=None, foreign_results=None):
        """ this contains the main ranking algorithm """
        # do some argument-parsing to allow this function to be called in
        # different ways. This is very convenient during testing
        if type(player) == str:
            player = self.db.query(Player).filter_by(ema_id=player).first()


        # filter results to only those for this ruleset
        eligible = self.get_ranked_tournaments_for_player(
            [r for r in aut_results if r.ruleset == ruleset]
            )
        rank = round(rank * 100) / 100


        # final ranking is a straight average of part A and part B
        player.rank(ruleset, 0.5 * partA + 0.5 * partB)

    def get_ranked_tournaments_for_player(self, results):
        """ given a list of results, return the ones that are eligible for
        ranking. If there are fewer than 2 eligible, then the player
        isn't eligible to have a ranking yet.
        Otherwise, if they have 2-4 qualifying results, then pad the list out
        with dummy results that have base rank 0, weight 1.
        And if they have more than 5 results, return the best """
        if len(results) < 1:
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

    def rank_all_players(self, quota_start:datetime = None, quota_end:datetime = None, assess=False):
        """ cycle through all players, and rank each in turn """
        players = self.db.query(Player).filter(Player.country_id == 'at').all()
        players_tourneys=[]
        for p in players :
            if p.riichi_rank:
                aut_tourneys=[r for r in p.tournaments if r.ruleset.name == 'riichi' and r.was_ema and r.tournament.country_id == 'at' and r.tournament.end_date >= quota_start and r.tournament.start_date <= quota_end]
                foreign_tourneys=[r for r in p.tournaments if r.ruleset.name == 'riichi' and r.was_ema and r.tournament.country_id != 'at' and r.tournament.end_date >= quota_start and r.tournament.start_date <= quota_end]
                aut_tourney_list=[]
                foreign_tourney_list=[]
                for t in aut_tourneys:
                    tourney_dict={
                        "title" : t.tournament.title,
                        "position" : t.position,
                        "player_count" : t.tournament.player_count,
                        "value": self.calculate_base_rank(t.tournament.player_count,t.position),
                    }
                    if tourney_dict["value"] > 0:
                        aut_tourney_list.append(tourney_dict)

                for t in foreign_tourneys:
                    tourney_dict={
                        "title" : t.tournament.title,
                        "position" : t.position,
                        "player_count" : t.tournament.player_count,
                        "value": self.calculate_base_rank(t.tournament.player_count,t.position),
                    }
                    if tourney_dict["value"] > 0:
                        foreign_tourney_list.append(tourney_dict)
                    sorted_list = sorted(foreign_tourney_list, key=lambda x: x["value"], reverse=True)[:3]
                aut_sum = sum(d['value'] for d in aut_tourney_list)
                foreign_sum = sum(d['value'] for d in sorted_list)
                players_tourneys.append({"sum": aut_sum+foreign_sum,"aut_sum": aut_sum, "foreign_sum": foreign_sum, "name": p.calling_name, "aut_tourneys": aut_tourney_list, "foreign_tourneys": foreign_tourney_list, "foreign_sorted": sorted_list})
                players_sorted = sorted(players_tourneys, key=lambda x: x["sum"], reverse=True)



           # foreign_tourneys=[r for r in p.tournaments if r.ruleset.name == 'riichi' and r.was_ema and r.country_id != 'at' and r.tournament.end_date >= quota_start and r.tournament.start_date <= quota_end ]
            # foreign_results = [r for r in p.tournaments if r.end_date >= quota_start and r.start_date <= quota_end and r.country_id != "at"]
            # self.rank_one_player_for_one_ruleset(p, "riichi", aut_results,foreign_results)
        print("test")
        self.db.commit()

        # now calculate each player's position in the rankings
        for rules in ('riichi'):
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
