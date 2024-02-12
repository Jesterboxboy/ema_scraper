#!/usr/bin/python3

# Based on data_scrapers.py from Jesterboxboy

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from dateutil.parser import parse as du_parse
from dateparser import parse as dp_parse
from daterangeparser import parse as dr_parse
import pycountry
from gettext import translation

from models import Player, Tournament, PlayerTournament, Country, RulesetClass

country_link_pattern = re.compile(r'Country/([A-Z]{3})_')
country_pattern = re.compile(r'/([a-z]{2}).png')
URLBASE = "http://silk.mahjong.ie/ranking/"

class Tournament_Scraper:
    def __init__(self, country, session):
        self.session = session

    def add_country(self, iso2, old3):
        test_exists = self.session.query(Country).filter_by(id=iso2).first()
        if test_exists is not None:
            # already in db, nothing to do
            return test_exists
        if iso2 == "??":
            name_native = "???"
            name = "???"
        else:
            country = pycountry.countries.get(alpha_2=iso2)
            name = country.name
            try:
                # try to get the country's name in its own language. Crude. Works for some countries. Sorry Belgium.
                translator = translation(
                    "iso639-3",
                    pycountry.LOCALES_DIR,
                    languages = [iso2],
                    )
                language = pycountry.languages.get(alpha_2=iso2)
                name_native = translator.gettext(language.name)
            except:
                print(f"WARNING: failed to find language '{iso2}'")
                name_native = name

        c = Country()
        c.id=iso2
        c.old3=old3
        c.name_english=name
        c.name_native=name_native
        self.session.add(c)
        self.session.commit()
        return c

    def parse_dates(self, raw_date, title):
        """we have dates in a bunch of formats, so this tries different tools
        in turn. Some dates don't have a year: but year is in tourney title,
        so we need TODO something clever with that"""
        # TODO get tourney year from tourney title if needed
        start_date = end_date = None
        try:
            start_date, end_date = dr_parse(raw_date)
            if start_date is not None and end_date is None:
                end_date = start_date
        except Exception as e:
            try:
                end_date = start_date = du_parse(raw_date)
            except Exception as e:
                try:
                    end_date = start_date = dp_parse(raw_date)
                except Exception as e:
                    start_date = end_date = None
                    # TODO log failure to parse date
                    print(f"ERROR parsing date '{raw_date}' for '{title}'")
        return start_date, end_date

    def scrape_tournaments_by_year(self, year):
        year_url = f"{URLBASE}Tournament/Tournaments_{year}.html"
        year_page = requests.get(year_url)
        year_soup = BeautifulSoup(year_page.content, "html.parser")

        table_raw = year_soup.findAll(
            "div", {"class": "Tableau_CertifiedTournament"})
        if table_raw is not None and len(table_raw) > 0:
            #grab the riichi table
            table = table_raw[1] # TODO this is forcing selection of the riichi table
            # skip first row because it is a header
            tournaments = table.findAll(
                "div", {"class": re.compile('TCTT_ligne*')})[2:]
            for tourney in tournaments:
                scrape_tournament_by_id() # TODO get id from line

    def get_bs4_tournament_page(self, tournament_id):
        """Get the BeautifulSoup4 object for a tournament web page, given
        its old_id"""
        tournament_url = f"{URLBASE}Tournament/TR_RCR_{tournament_id}.html"
        tournament_page = requests.get(tournament_url)
        return BeautifulSoup(tournament_page.content, "html.parser")


    def scrape_tournament_by_id(self, tournament_id):
        """given an old tournament_id, scrape the webpage, and create
        a database item with the metadata. Then scrape the results"""
        last_scraped = self.session.query(
            Tournament.scraped_on
            ).filter_by(old_id=tournament_id).first()

        if last_scraped is not None:
            print(f"we already scraped this tournament at {last_scraped}")
            return True

        tournament_soup = self.get_bs4_tournament_page(tournament_id)
        tournament_info = tournament_soup.findAll("td")

        # get mers weight
        weight_pattern = re.compile(r'^(\d+,\d+)\(')
        weight_string = tournament_info[12].text.strip().title()
        weight_match = weight_pattern.search(weight_string)
        weight = float(weight_match.group(1).replace(
            ',', '.')) if weight_match else 'NaN'

        t = Tournament()

        place = tournament_info[6].text.lstrip().split("(")[0]
        country_string = tournament_info[6].findAll("a")[0]["href"]
        country_match = country_link_pattern.search(country_string)
        old3 = "???" if country_match is None else \
            country_match.group(1)
        try:
            flag_string = tournament_info[6].find("img").attrs['src']
            matches = country_pattern.search(flag_string)
            iso2 = matches[1]
        except:
            iso2 = "??"
        t.country = self.add_country(old3=old3, iso2=iso2)

        # remove ", {country}" from place before putting it into db
        # Behaves nicely, even if there's more than one comma in place
        # As long as the country name doesn't have a comma in it
        t.place = ", ".join(place.split(",")[0:-1])

        t.raw_date = tournament_info[8].text.strip().title()
        t.title = tournament_info[4].text.strip().title()
        t.start_date, t.end_date = self.parse_dates(t.raw_date, t.title)
        t.effective_end_date = t.end_date

        t.ruleset = RulesetClass.Riichi
        t.player_count = int(tournament_info[10].text.strip())
        t.mers = weight
        t.old_id = tournament_id
        t.scraped_on = datetime.now()

        # add tournament to db
        self.session.add(t)
        self.session.commit()

        # scrape results for tournament
        self.extract_tournament_results_from_page(t, tournament_soup)

    def add_player(self, ema_id):
        # if ema_id is zero, create player with blank ema_id
        p = Player()
        page = requests.get(f"{URLBASE}Players/{ema_id}.html")
        dom = BeautifulSoup(page.content, "html.parser")
        rows = dom.findAll(
            "div", {"class": "contentpaneopen"}
            )[0].find("table").find_all("tr")
        p.ema_id = ema_id
        try:
            flag_string = rows[3].find("img").attrs["src"]
            matches = country_pattern.search(flag_string)
            iso2 = matches[1]
            country_string = rows[3].find("a").attrs["href"]
            country_match = country_link_pattern.search(country_string)
            old3 = "???" if country_match is None else \
                country_match.group(1)
        except:
            iso2 = "??"
            old3 = "???"
        p.country = self.add_country(old3=old3, iso2=iso2)
        try:
            org = rows[4].findAll("td")[1]
            p.country.national_org_name = org.string
            p.country.national_org_url = org.find("a").attrs['href']
        except:
            pass
        try:
            org = rows[5].findAll("td")[1]
            p.local_club = org.string
            p.local_club_url = org.find("a").attrs["href"]
        except:
            pass

        p.calling_name = rows[2].find_all("td")[1].string
        # just guess that the family name is the word after the last space
        names = p.calling_name.split(" ")
        p.sorting_name = names[-1] + ", " + "  ".join(names[0:-1])
        pic = rows[0].find("img").attrs["src"]
        p.profile_pic = None if pic == "photo/Vide.jpg" else pic
        self.session.add(p)
        return p


    def extract_tournament_results_from_page(self, t, tournament_soup):
        """Enter results for tournament. given the Tournament object
        and BS4 web page"""
        results_table = tournament_soup.findAll(
            "div", {"class": "TCTT_lignes"})[0]
        results = results_table.findAll(
            "div", {"class": re.compile('TCTT_ligne*')})[1:]
        for result in results:
            result_content = result.findAll("p")
            position = int(result_content[0].text.strip())
            player_id = 0 if result_content[1].text.strip() == '-' else \
                result_content[1].text.strip()
            score = 0 if result_content[6].text.strip() == '-' else \
                int(result_content[6].text.strip())
            rank = int(
                1000 * (t.player_count - position) / (t.player_count - 1)
                )
            if player_id:
                p = self.session.query(Player).filter_by(ema_id=player_id).first()
                if p is None:
                    p = self.add_player(player_id)
                    # TODO add sorting_name here
                    self.session.commit()
                was_ema = True
            else:
                p = Player()
                p.calling_name = "TBD" # TODO
                p.sorting_name = "TBD" # TODO
                self.session.add(p)
                self.session.commit()
                was_ema = False

            cid = p.country_id
            pt = PlayerTournament()
            pt.player = p
            pt.tournament = t
            pt.score = score
            pt.position = position
            pt.base_rank = rank
            pt.was_ema = was_ema
            pt.country_id = cid
            self.session.add(pt)
            self.session.commit()

    def scrape_players_by_country(self, country):
        # TODO doesn't work yet
        url = f"{URLBASE}Country/{country}_RCR.html"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        table = soup.findAll("div", {"class": "TCTT_lignes"})[0]
        # skip first row because it is a header
        results = table.findAll("div")[1:]
        for result in results:
            data = result.findAll("p")

            ema_id = data[2].text.strip()
            last_name = data[3].text.strip().title()
            first_name = data[4].text.strip().title()

            # TODO create score in db

        url = f"{URLBASE}Players/{country}_History.html"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        results = table.findAll("div")[1:]
