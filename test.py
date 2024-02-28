from datetime import datetime
import sys
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from config import DBPATH
from models import Player, Tournament, PlayerTournament, Country, RulesetClass
from scrapers import Tournament_Scraper, Country_Scraper
from ranking import PlayerRankingEngine
from country_ranking import CountryRankingEngine
from quota import QuotaMaker
from get_results import results_to_db

logging.basicConfig(
    filename='testpy.log',
    filemode='w', # ensure log file always writes fresh, rather than appending to previous log
    encoding='utf-8',
    level=logging.INFO, # suppress debug messages from imported libraries
    )

logging.info(datetime.now())
engine = create_engine(DBPATH, poolclass=NullPool)

def rank_countries(db):
    r = CountryRankingEngine(db)
    r.rank_countries_for_one_ruleset(RulesetClass.riichi, assess=True)
    r.rank_countries_for_one_ruleset(RulesetClass.mcr, assess=True)

def rank_players(db):
    PlayerRankingEngine(db).rank_all_players(assess=True)

def scrape_tournaments(db):
    Tournament_Scraper(db).scrape_all()

def make_quotas(db):
    QuotaMaker(db, 40, RulesetClass.mcr).make()
    QuotaMaker(db, 140, RulesetClass.riichi).make()

with Session(engine) as db:
    results_to_db(db, 'd:\\zaps\\emarebuild\\fake-tourney.xls', 'rcr220')
    # scrape_tournaments(db)
    # rank_players(db)
    # rank_countries(db)
    # make_quotas(db)
    # PlayerRankingEngine(session).rank_one_player_for_one_ruleset("11990143", RulesetClass.riichi)
    pass

print("done")
sys.exit(0)
