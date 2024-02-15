from datetime import datetime
import sys

from scrapers import Tournament_Scraper
from models import RulesetClass
from ranking import RankingEngine

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
    for year in list(range(2005, 2025)):
        rating = Tournament_Scraper(session)
        rating.scrape_tournaments_by_year(year)

    #ranker = RankingEngine(session)
    #ranker.weight_tournaments(datetime(2024,2,14))

print("done")
sys.exit(0)



#2010-2025 done

# intentionally not running this line, just keeping it for debugging
rating.scrape_tournament_by_id(69, RulesetClass.Riichi)
