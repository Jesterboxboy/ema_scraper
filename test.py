from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# from models import Player, Tournament, PlayerTournament, Country, Ruleset
from scrapers import Tournament_Scraper

engine = create_engine('sqlite:///d:\\zaps\\emarebuild\\ema.sqlite3')

with Session(engine) as session:
    rating = Tournament_Scraper("DEN", session)
    rating.scrape_tournament_by_id(264)

exit()

for year in list(range(2019, 2025)):
    rating.scrape_tournaments_by_year(year)

with session.begin():
    rating.scrape_players_by_country()
