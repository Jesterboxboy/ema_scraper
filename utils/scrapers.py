#!/usr/bin/python3

# Based on data_scrapers.py from Jesterboxboy

import logging
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from dateutil.parser import parse as du_parse
from dateutil.relativedelta import relativedelta
from dateparser import parse as dp_parse
from daterangeparser import parse as dr_parse
import pycountry

from models import Player, Tournament, PlayerTournament, Country, Club, \
                   Ruleset
from calculators.ranking import PlayerRankingEngine

country_link_pattern = re.compile(r'Country/([A-Z]{3})_')
country_pattern = re.compile(r'/([a-z]{2}).png')
URLBASE = "https://silk.mahjong.ie/ranking/"
#URLBASE = "http://mahjong-europe.org/ranking/"

def french_float(number_string):
    return float(number_string.replace(',', '.'))

class Country_Scraper:
    def __init__(self, session):
        self.db = session

    @staticmethod
    def scrape_country_rankings(url: str):
        ranking = []
        best_nation_page = requests.get(url)
        year_soup = BeautifulSoup(best_nation_page.content, "html.parser")
        rows = year_soup.find(
            "div", {"class": "PodiumTB"}).find_all(
            "div", {"class": "TCTT_ligne"})
        # first row is the header, so we skip it
        for row in rows[1:]:
            cells = row.find_all("p")
            matches = country_pattern.search(cells[1].find("img").attrs['src'])
            ranking.append({
                "position": int(cells[0].text),
                "country": matches[1],
                "player_count": int(cells[2].text),
                "top3_average": french_float(cells[3].text),
                })
        return ranking

class Tournament_Scraper:
    def __init__(self, session):
        self.session = session

    def dash_to_0(self, number_string):
        number_string = number_string.strip()
        match number_string:
            case '-':
                return "0"
            case 'N/A':
                return "-999999"
            case _:
                return number_string

    def add_country(self, iso2, old3):
        test_exists = self.session.query(Country).filter_by(id=iso2).first()
        if test_exists is not None:
            # already in db, nothing to do
            return test_exists
        if iso2 == "??":
            name = "???"
        else:
            country = pycountry.countries.get(alpha_2=iso2)
            name = country.name

        c = Country()
        c.id=iso2
        c.old3=old3
        c.name_english=name
        self.session.add(c)
        self.session.commit()
        return c

    @staticmethod
    def parse_dates(raw_date: str, title: str):
        """we have dates in a bunch of formats, so this tries different tools
        in turn. Some recorded dates are just weird, so there's a bunch of
        one-off handling as the cleanest way to handle them, rather than
        a bunch of convoluted logic which would have the same outcome"""
        match raw_date:
            case "26-27-28 May 2017":
                start_date = datetime(2017, 5, 26)
                end_date = datetime(2017, 5, 28)
            case "30-01 June 2018":
                start_date = datetime(2018, 6, 30)
                end_date = datetime(2018, 7, 1)
            case "31-1 May 2014":
                start_date = datetime(2014, 5, 31)
                end_date = datetime(2014, 6, 1)
            case "29 Mar. 2013": # yes, the year does appear to be wrong!
                start_date = datetime(2014, 3, 29)
                end_date = datetime(2014, 3, 29)
            case "30-01 June 2018":
                start_date = datetime(2018, 6, 30)
                end_date = datetime(2018, 7, 1)
            case "19-20-21 Apr. 2019":
                start_date = datetime(2019, 4, 19)
                end_date = datetime(2019, 4, 21)
            case "23-24 Mars 2019":
                start_date = datetime(2019, 3, 23)
                end_date = datetime(2019, 3, 24)
            case "31.May-2.Jun":
                start_date = datetime(2019, 5, 31)
                end_date = datetime(2019, 6, 2)
            case "31-01 Aug-Sep. 2019":
                start_date = datetime(2019, 8, 31)
                end_date = datetime(2019, 9, 1)
            case "28 Feb. 1Mar. 2015":
                start_date = datetime(2015, 2, 28)
                end_date = datetime(2015, 3, 1)
            case "31 Jan. 1 Feb 2015":
                start_date = datetime(2015, 1, 31)
                end_date = datetime(2015, 2, 1)
            case "26-27-28 May 2017":
                start_date = datetime(2017, 3, 26)
                end_date = datetime(2017, 3, 28)
            case "15-16-17 June 2018":
                start_date = datetime(2018, 6, 15)
                end_date = datetime(2018, 6, 17)
            case "2-3 February":
              start_date = datetime(2019, 2, 3)
              end_date = datetime(2019, 2, 3)
            case "3 February":
              start_date = datetime(2019, 2, 3)
              end_date = datetime(2018, 2, 3)
            case _:
                start_date = end_date = None
                try:
                    start_date, end_date = dr_parse(raw_date)
                    if start_date is not None and end_date is None:
                        end_date = start_date
                except:
                    pass
                if start_date is None:
                    try:
                        end_date = start_date = du_parse(raw_date)
                    except:
                        start_date = end_date = None
                if start_date is None:
                    try:
                        end_date = start_date = dp_parse(raw_date)
                    except:
                        start_date = end_date = None
                if start_date is None or \
                    start_date.hour + start_date.minute > 0:
                    # tournament dates don't have any time specified,
                    # so if we've got a time, we've mis-parsed it
                    start_date = end_date = None
                    if "." in raw_date:
                        start_date, end_date = Tournament_Scraper.parse_dates(
                            raw_date.replace(".", " "),
                            title,
                            )

        if start_date is None:
            logging.error(f"can't date '{raw_date}' for '{title}'")

        return start_date, end_date

    def scrape_tournaments_by_year(self, year):
        print(f"\n getting tournaments for {year}")
        year_url = f"{URLBASE}Tournament/Tournaments_{year}.html"
        year_page = requests.get(year_url)
        year_soup = BeautifulSoup(year_page.content, "html.parser")

        table_raw = year_soup.findAll(
            "div", {"class": "Tableau_CertifiedTournament"})
        if table_raw is not None and len(table_raw) > 0:
            # iterate over each ruleset
            # we need to specify whether it's mcr or RCR,
            # as ids are duplicated between them!!!
            ruleset = Ruleset.mcr
            for table in table_raw:
                tournaments = table.findAll(
                    "div", {"class": re.compile('TCTT_ligne*')})[2:]
                for tourney in tournaments:
                    cells = tourney.find_all("p")
                    tid = int(cells[0].string)
                    self.scrape_tournament_by_id(
                        tid,
                        countries=cells[6].string,
                        ruleset=ruleset,
                        )
                ruleset = Ruleset.riichi

    def get_bs4_tournament_page(self, tournament_id, ruleset):
        """Get the BeautifulSoup4 object for a tournament web page, given
        its old_id"""
        prefix = "TR_" if ruleset == Ruleset.mcr else "TR_RCR_"

        # if id < 10, then a 2-digit number is used in the URL
        if tournament_id < 10:
            prefix += "0"
        tournament_url = f"{URLBASE}Tournament/{prefix}{tournament_id}.html"
        tournament_page = requests.get(tournament_url)
        if not tournament_page.ok:
            # not a riichi tournament, so try mcr
            tournament_url = f"{URLBASE}Tournament/TR_{tournament_id}.html"
            tournament_page = requests.get(tournament_url)
            if not tournament_page.ok:
                logging.error(f"ERROR failed to find page for tournament {tournament_id}")

        return BeautifulSoup(tournament_page.content, "html.parser")


    def scrape_tournament_by_id(self, tournament_id, ruleset, countries=None):
        """given an old tournament_id, scrape the webpage, and create
        a database item with the metadata. Then scrape the results"""

        t = self.session.query(Tournament).filter_by(
            old_id=tournament_id, ruleset=ruleset).first()

        print('.', end='')
        is_new = t is None
        if is_new:
            t = Tournament()

        tournament_soup = self.get_bs4_tournament_page(tournament_id, ruleset)
        tournament_info = tournament_soup.findAll("td")

        # get mers weight
        try:
            weight_string = tournament_info[12].string.strip().split("(")[0]
            weight = french_float(weight_string)
        except:
            weight = 0

        place = tournament_info[6].text.lstrip().split("(")[0].title()
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
        t.ruleset = ruleset
        t.raw_date = tournament_info[8].text.strip().title()
        t.title = tournament_info[4].text.strip().title()
        t.start_date, t.end_date = self.parse_dates(t.raw_date, t.title)

        if tournament_id == 269 and t.ruleset == Ruleset.mcr:
            # the player count on the original web page appears to be wrong
            # for this one tournament VILLEJUIF OPEN 2017 - IN VINO VERITAS I
            t.player_count = 84
        else:
            t.player_count = int(tournament_info[10].text.strip())

        if t.end_date < datetime(2018, 4, 18) or \
                t.end_date >= datetime(2022, 7, 1):
            t.effective_end_date = t.end_date
        else:
            # covid lockdown handling
            t.effective_end_date = t.end_date + relativedelta(months=27)
        # special handling for the 5 tournaments held in lockdown that got
        # extended eligibility periods in the rankings
        if t.ruleset == Ruleset.mcr:
            if tournament_id in (350, 351, 352, 353):
                t.effective_end_date = datetime(2022, 7, 1)
        else:
            if tournament_id == 269:
                t.effective_end_date = datetime(2022, 7, 1)


        t.ema_country_count = countries # TODO if this is none, calculate it manually
        t.mers = weight
        t.old_id = tournament_id
        t.scraped_on = datetime.now()

        if is_new: # add tournament to db if it's new
            self.session.add(t)
        self.session.commit()

        # scrape results for tournament
        self.extract_tournament_results_from_page(t, tournament_soup)

    def add_player(self, ema_id):
        # if ema_id is zero, create player with blank ema_id
        p = self.session.query(Player).filter_by(ema_id=ema_id).first()
        is_new = p is None
        if is_new:
            p = Player()
        page = requests.get(f"{URLBASE}Players/{ema_id}.html")
        p.ema_id = ema_id
        pic = None
        tables = None
        try:
            dom = BeautifulSoup(page.content, "html.parser")
            tables = dom.findAll(
                "div", {"class": "contentpaneopen"})[0].findAll("table")
            rows = tables[0].find_all("tr")
            p.calling_name = rows[2].find_all("td")[1].string.title()
            names = p.calling_name.split(" ")
            p.sorting_name = names[-1] + ", " + "  ".join(names[0:-1])
            pic = rows[0].find("img").attrs["src"]
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
            org = self.db.query(Club).filter(Club.is_the_national_org).filter(
                Club.country_id == iso2)
            new_org = org is None
            if new_org:
                org = Club()
                org.country_id = iso2
                org.is_the_national_org = True
                org.name = org.string
                org.url = org.find("a").attrs['href']
                # TODO logo is on the page
                # f"/ranking/Country/{old3}_Information.html"
                # in div.contentpaneopen > table > tbody > tr[0] > td[0] > img.src
                self.db.add(org)
            p.country.national_org_id = org.id
        except:
            pass
        try:
            org = rows[5].findAll("td")[1]
            # does this club already exist in the db? if not, create it
            club_name = org.string
            club_url = org.find("a").attrs["href"].replace(
                'http://', 'https://')
            club = self.db.query(Club).filter_by(name=club_name).first()
            if club is None:
                club = self.db.query(Club).filter_by(url=club_url).first()
            new_club = club is None
            if new_club:
                club = Club()
                club.name = club_name
            if club.url is None:
                club.url = club_url
            if new_club:
                self.db.add(club)
            p.local_club_id = club.id
            self.db.commit()
        except:
            pass

        if ema_id is not None and ema_id != "-1" and tables is not None:
            # get the official rankings for both rulesets
            rows = tables[1].find_all("tr")
            try:
                rank = french_float(rows[2].find_all("td")[2].text)
            except:
                rank = None
            p.mcr_official_rank = rank
            try:
                rank = french_float(rows[3].find_all("td")[2].text)
            except:
                rank = None
            p.riichi_official_rank = rank

        # just guess that the family name is the word after the last space
        p.profile_pic = None if pic == "photo/Vide.jpg" else pic
        if is_new:
            self.session.add(p)
        return p

    def extract_tournament_results_from_page(self, t, tournament_soup):
        """Enter results for tournament. given the Tournament object
        and BS4 web page"""

        # TODO sometimes there's an image attached to  1st/2nd/3rd that
        #      isn't attached to an individual player acount

        self.session.query(PlayerTournament).filter_by(tournament=t).delete()
        self.session.commit()
        is_mcr = t.ruleset == Ruleset.mcr

        results_table = tournament_soup.findAll(
            "div", {"class": "TCTT_lignes"})[0]
        results = results_table.findAll(
            "div", {"class": re.compile('TCTT_ligne*')})[1:]
        if len(results) != t.player_count:
            logging.error("Discrepancy between number of players "
                f"({t.player_count}) and number of results ({len(results)}) "
                f"for {t.title}, {t.ruleset} {t.old_id}")
        rank_errors = 0
        previous_position = 0
        previous_table_points = 0
        previous_score = 0
        for result in results:
            result_content = result.findAll("p")
            position = int(self.dash_to_0(result_content[0].text)) or \
                t.player_count
            player_id = self.dash_to_0(result_content[1].text)
            score = int(self.dash_to_0(result_content[6].text))

            # if it's mcr, grab table points too
            if is_mcr:
                table_points = french_float(self.dash_to_0(
                    result_content[5].text))
            else:
                table_points = None

            # if ranks are tied, the players will have the same base_rank points,
            # BUT the position shown on the webpage are WRONG
            # eg if the top three places were tied, they'd be shown
            # as position 1,2,3 ! eg mcr 348 has two such ties
            if previous_position > 0 \
                and table_points == previous_table_points \
                and score == previous_score:
                    position = previous_position
            else:
                previous_position = position
                previous_score = score
                previous_table_points = table_points


            pt = None
            if player_id == "0":
                # not an EMA-registered player

                # here, we add on the ruleset, the tournament id, and the
                # ranking position, to ensure that in teh database, this player
                # is unique, and is attached to *this* tournament only
                name = result_content[3].string.title() + \
                    " " + result_content[2].string.title() + \
                    str(t.ruleset).replace("Ruleset.", " (") + \
                    f"{t.old_id} {position}th)"
                was_ema = False
                rank = 0
                p = self.session.query(Player).filter_by(
                    calling_name=name).filter_by(ema_id=-1).first()
                if p is None:
                    p = Player()
                    p.ema_id = "-1"
                    p.calling_name = name
                    p.sorting_name = result_content[2].string.title() + \
                        ", " + result_content[3].string.title()
                    self.session.add(p)
                    self.session.commit()
            else:
                was_ema = True
                rank = PlayerRankingEngine.calculate_base_rank(t.player_count,
                                                         position)
                p = self.session.query(Player).filter_by(
                    ema_id=player_id).first()
                if p is None:
                    p = self.add_player(player_id)
                    if p.calling_name is None:
                        p.calling_name = result_content[3].string.title() + \
                            " " + result_content[2].string.title()

                    p.sorting_name = result_content[2].string.title() + \
                        ", " + result_content[3].string.title()

                    self.session.commit()
                else:
                    # check whether we've already got this score
                    pt = self.session.query(PlayerTournament).filter_by(
                        tournament_id=t.id, player_id=p.id).first()

            # check our base_rank calculation with the official one, log any discrepancies
            official_rank = int(self.dash_to_0(result_content[7].text))
            if rank != official_rank:
                rank_errors += 1
                logging.error(
                    f"""Discrepancy in base-rank calculation for {p.sorting_name}.
                    We calculated {rank}, but the official rank is {official_rank}
                    Tournament is {t.title} {t.ruleset} {t.old_id}
            """)

            is_new = pt is None
            if is_new:
                pt = PlayerTournament()

            cid = p.country_id
            ruleset = t.ruleset

            pt.player = p
            pt.ruleset = ruleset
            pt.tournament = t
            pt.table_points = table_points
            pt.score = score
            pt.position = position
            pt.base_rank = rank
            pt.was_ema = was_ema
            pt.country_id = cid
            if is_new:
                self.session.add(pt)
            self.session.commit()

        if rank_errors > 0:
            print(f"{rank_errors} base-rank discrepancies for {t.title}; logfile has details")

    def scrape_all(self, start:int=2005, end:int=2025):
        for year in list(range(start, end)):
            self.scrape_tournaments_by_year(year)
