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

    def rank_all_players(self, quota_start:datetime = None, quota_end:datetime = None, assess=False):
        """ cycle through all players, and rank each in turn """
        players = self.db.query(Player).filter(Player.country_id == 'at').all()
        players_tourneys=[]
        for p in players :
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
            best_3_foreign = sorted(foreign_tourney_list, key=lambda x: x["value"], reverse=True)[:3]
            aut_sum = sum(d['value'] for d in aut_tourney_list)
            foreign_sum = sum(d['value'] for d in best_3_foreign)
            players_tourneys.append({"sum": aut_sum+foreign_sum,"aut_sum": aut_sum, "foreign_sum": foreign_sum, "name": p.calling_name, "aut_tourneys": aut_tourney_list, "foreign_tourneys": foreign_tourney_list, "foreign_sorted": best_3_foreign})
            players_sorted = sorted(players_tourneys, key=lambda x: x["sum"], reverse=True)
        return players_sorted
