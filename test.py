from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys

# from models import Player, Tournament, PlayerTournament, Country, Ruleset
from scrapers import Tournament_Scraper

engine = create_engine('sqlite:///d:\\zaps\\emarebuild\\ema.sqlite3')

with Session(engine) as session:
    rating = Tournament_Scraper(session)


    for year in list(range(2019, 2025)):
        rating.scrape_tournaments_by_year(year)

print("done")
sys.exit(0)


rating.scrape_players_by_country()
