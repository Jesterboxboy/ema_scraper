from datetime import datetime
import sys

from scrapers import Tournament_Scraper
from models import Player, RulesetClass
from ranking import PlayerRankingEngine

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
    ranker = PlayerRankingEngine(session)


    #scraper = Tournament_Scraper(session)
    #for year in list(range(2005, 2025)):
    #    scraper.scrape_tournaments_by_year(year)

    # current expiry date is 2019-11-08
    # current halving date is 1 year ago
    ranker.weight_tournaments(datetime(2024,2,16))
    total = 0
    bad = 0
    for p in session.query(Player).all():
        r = ranker.get_all_eligible_results_for_player(p.id)

        ranker.rank_one_player_for_one_ruleset(p, RulesetClass.MCR, r)
        if p.official_mcr_rank is not None:
            total += 1
            delta = p.official_mcr_rank - p.mcr_rank
            if abs(delta) > 0.02:
                bad += 1
                logging.warning(f"mismatch for {p.calling_name} {p.ema_id}")
                logging.warning(f"official MCR rank is {p.official_mcr_rank}.\nWe calculate {p.mcr_rank}\n")

        ranker.rank_one_player_for_one_ruleset(p, RulesetClass.Riichi, r)
        if p.official_riichi_rank is not None:
            total += 1
            delta = p.official_riichi_rank - p.riichi_rank
            if abs(delta) > 0.02:
                bad += 1
                logging.warning(f"mismatch for {p.calling_name} {p.ema_id}")
                logging.warning(f"official riichi rank is {p.official_riichi_rank}.\nWe calculate {p.riichi_rank}\n")

    logging.info(f"{total} calcs done, of which {bad} were bad")

print("done")
sys.exit(0)

if False:

    # 04090055 has a LOT of eligible MCR tournaments, and 2 riichi ones,
    #          so is a good test of the ranking algo

    scraper = Tournament_Scraper(session)
    scraper.add_player(ema_id="04090055")

    ranker = PlayerRankingEngine(session)




# intentionally not running this line, just keeping it for debugging
rating.scrape_tournament_by_id(69, RulesetClass.Riichi)
