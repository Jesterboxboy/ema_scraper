from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys
from scrapers import Tournament_Scraper

import logging
logging.basicConfig(
    filename='testpy.log',
    filemode='w', # ensure log file always writes fresh, rather than appending to previous log
    encoding='utf-8',
    level=logging.INFO, # suppress debug messages from imported libraries
    )

engine = create_engine('sqlite:///d:\\zaps\\emarebuild\\ema.sqlite3')

with Session(engine) as session:
    rating = Tournament_Scraper(session)
    for year in list(range(2019, 2025)):
        rating.scrape_tournaments_by_year(year)

print("done")
sys.exit(0)

rating.scrape_tournament_by_id(365)
rating.scrape_tournaments_by_year(2019)
