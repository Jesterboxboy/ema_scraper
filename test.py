from datetime import datetime
import sys
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from config import DBPATH
from models import Player, Tournament, PlayerTournament, Country, RulesetClass
from utils.scrapers import Tournament_Scraper, Country_Scraper
from calculators.ranking import PlayerRankingEngine
from calculators.ranking_austria_riichi import PlayerRankingEngine as AustrianPlayerRankingEngine
from calculators.country_ranking import CountryRankingEngine
from calculators.quota import QuotaMaker
from calculators.get_results import results_to_db
from renderers.render_results import Render_Results
from renderers.render_player import Render_Player
from renderers.render_year import Render_Year

logging.basicConfig(
    filename='testpy.log',
    filemode='w', # ensure log file always writes fresh, rather than appending to previous log
    encoding='utf-8',
    level=logging.INFO, # suppress debug messages from imported libraries
    )

logging.info(datetime.now())
engine = create_engine(DBPATH, poolclass=NullPool)

def rank_countries(db):
    '''calculate country rankings, used as a basis for national quotas'''
    r = CountryRankingEngine(db)
    r.rank_countries_for_one_ruleset(RulesetClass.riichi, assess=True)
    r.rank_countries_for_one_ruleset(RulesetClass.mcr, assess=True)

def rank_players(db):
    ''' calculate all player rankings, using today's date as the baseline'''
    PlayerRankingEngine(db).rank_all_players(assess=True,
        reckoning_day=datetime(2024,2,25))

def rank_aut_players(db):
    ''' calculate all player rankings, using today's date as the baseline'''
    AustrianPlayerRankingEngine(db).rank_all_players(assess=True,
        quota_start=(datetime(2020,1,1)),quota_end=(datetime(2024,4,11)))

def scrape_tournaments(db):
    '''scrape the EMA mirror site and put all the data into our database'''
    Tournament_Scraper(db).scrape_all() # start=2023, end=2024

def make_quotas(db):
    '''make the two example quotas that currently appear on the EMA site'''
    QuotaMaker(db, 40, RulesetClass.mcr).make()
    QuotaMaker(db, 90, RulesetClass.riichi).make()

def render_one_results(db):
    '''In production we will render a page for every tournament. However,
    for now, we just render a few samples to test the process'''
    t = db.query(Tournament).filter(Tournament.ruleset == RulesetClass.mcr
        ).filter(Tournament.old_id == 373).first()
    Render_Results(db).one_tournament(t)

def render_players(db):
    '''In production we will render a page for every player. However, for now,
    we just render a few sample players to test the process'''
    r = Render_Player(db)
    for id in (
        "07000155", # lots in each ruleset
        "14990047", # riichi only
        "04390002", # mcr only
        "07000001", # bad rank calc?
        ):
        r.one_player(id)

with Session(engine) as db:
    # scrape_tournaments(db)
    rank_aut_players(db)
    # rank_countries(db)
    # make_quotas(db)
    # Render_Year(db).years(2022, 2023)
    # render_one_results(db)
    # render_players(db)
    # results_to_db(db, 'd:\\zaps\\emarebuild\\fake-tourney.xls', 'rcr220')
    # PlayerRankingEngine(db).rank_one_player_for_one_ruleset("11990143", RulesetClass.riichi)
    pass

print("done")
sys.exit(0)
