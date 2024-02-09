from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Player, Tournament, PlayerTournament, Country, Ruleset
from scrapers import Tournament_Scraper as TS

engine = create_engine('sqlite:///d:\\zaps\\emarebuild\\ema.sqlite3')

with Session(engine) as session:
    with session.begin():
        session.add(newThing)
