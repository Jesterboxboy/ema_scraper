from datetime import datetime
import sys
from models import Player, Tournament, PlayerTournament, Country, RulesetClass
from scrapers import Tournament_Scraper, Country_Scraper
from ranking import PlayerRankingEngine
from quota import CountryRankingEngine

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import logging
logging.basicConfig(
    filename='testpy.log',
    filemode='w', # ensure log file always writes fresh, rather than appending to previous log
    encoding='utf-8',
    level=logging.INFO, # suppress debug messages from imported libraries
    )

logging.info(datetime.now())
engine = create_engine('sqlite:///d:\\zaps\\emarebuild\\ema.sqlite3')

with Session(engine) as session:
    #c = Country_Scraper(session)
    #c.scrape_country_rankings("https://silk.mahjong.ie/ranking/BestNation_RCR.html")
    # PlayerRankingEngine(session).rank_all_players(assess=True)
    r = CountryRankingEngine(session)
    r.rank_countries_for_one_ruleset(RulesetClass.Riichi, assess=True)
    r.rank_countries_for_one_ruleset(RulesetClass.MCR, assess=True)
    #Tournament_Scraper(session).scrape_all()
    #PlayerRankingEngine(session).rank_one_player_for_one_ruleset("11990143", RulesetClass.Riichi)
    pass

print("done")
sys.exit(0)
