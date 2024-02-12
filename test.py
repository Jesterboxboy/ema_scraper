from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys

# from models import Player, Tournament, PlayerTournament, Country, Ruleset
from scrapers import Tournament_Scraper

engine = create_engine('sqlite:///d:\\zaps\\emarebuild\\ema.sqlite3')

with Session(engine) as session:
    rating = Tournament_Scraper(session)

    rating.scrape_tournament_by_id(365)

print("done")
sys.exit(0)

for year in list(range(2019, 2025)):
    rating.scrape_tournaments_by_year(year)
