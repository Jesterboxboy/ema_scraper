#!/usr/bin/python3

# Based on data_scrapers.py from Jesterboxboy

import requests
from bs4 import BeautifulSoup
import re
from dateutil.parser import parse as dateparse
from daterangeparser import parse as daterangeparse
from pycountry import countries

from models import Player, Tournament, PlayerTournament, Country, Ruleset

class Tournament_Scraper:
    def __init__(self, country):
        self.country = country
        self.date_format = "%Y-%m-%d"
        self.urlbase = "http://silk.mahjong.ie/ranking/
        self.startdate = None
        self.enddate = None


    def parse_dates(self, datetext):
        try:
            self.startdate, self.enddate  = daterangeparse(datetext)
            return
        except Error as e:
            try:
                self.startdate = dateparse(datetext)
                self.enddate = self.startdate
                return
            except Error as e:
                # failed to deal with it
                pass
        self.startdate = self.enddate = None

    def save_tournament(self):
        country_pattern = re.compile(r'/([a-z]{2}).png')
        country_match = country_pattern.search(country_string)
        country_iso2 = country_match.group(
            1) if country_match else 'NaN'
        country_iso3 = countries.get(alpha_2=country_iso2).alpha_3


    def scrape_tournaments_by_year(self, year):
        year_url = f"{self.urlbase}Tournament/Tournaments_{year}.html"
        year_page = requests.get(year_url)
        year_soup = BeautifulSoup(year_page.content, "html.parser")

        table_raw = year_soup.findAll(
            "div", {"class": "Tableau_CertifiedTournament"})
        if table_raw is not None and len(table_raw) > 0:
            table = table_raw[1]
            # skip first row because it is a header
            tournaments = table.findAll(
                "div", {"class": re.compile('TCTT_ligne*')})[2:]
            for tourney in tournaments:
                data = tourney.findAll("p")
                title = data[3].text.strip().title()
                place = data[2].text.strip().title()
                raw_date = data[1].text.strip().title()

                player_number = int(data[5].text.strip())
                weight = float(data[4].text.strip().replace(',', '.'))
                tournament_id = int(data[0].text.strip())
                country_string = data[2].findAll("img")[0]["src"]

                # call method to scrape the tournament results
                self.scrape_tournament_results(tournament_id)

    def scrape_tournament_by_id(self, tournament_id):

        cursor = self.sqlconn.cursor()

        # check if tournament exists
        cursor.execute("SELECT * from tournaments where id = ?",
                       (tournament_id,))

        if cursor.fetchone():
            return True

        tournament_url = f"{self.urlbase}Tournament/TR_RCR_{tournament_id}.html"
        tournament_page = requests.get(tournament_url)
        tournament_soup = BeautifulSoup(tournament_page.content, "html.parser")
        tournament_info = tournament_soup.findAll("td")

        # get data from tourney
        title = tournament_info[4].text.strip().title()
        raw_date = tournament_info[8].text.strip().title()
        # date = parse(tournament_info[8].text.strip().title()).strftime( self.date_format)
        player_number = int(tournament_info[10].text.strip())

        # extract weight
        weight_pattern = re.compile(r'^(\d+,\d+)\(')
        weight_string = tournament_info[12].text.strip().title()
        weight_match = weight_pattern.search(weight_string)
        weight = float(weight_match.group(1).replace(
            ',', '.')) if weight_match else 'NaN'

        # extract_country
        country_string = tournament_info[6].findAll("a")[0]["href"]
        country = country_match.group(1) if country_match else 'NaN'
        place = "NaN"

        tournament_sql = f"INSERT OR IGNORE INTO tournaments VALUES({tournament_id},'{title}','{place}','{country}','{raw_date}',{player_number},{weight});"
        try:
            cursor.execute(tournament_sql)
        except Exception as e:
            print(f"An error occured: {e}")

        self.sqlconn.commit()
        # scrape results for tournament
        self.scrape_tournament_results(tournament_id)

    def scrape_tournament_results(self, tournament_id):

        cursor = self.sqlconn.cursor()

        # check if tournament exists
        cursor.execute(
            f"SELECT fetched_flag from tournaments where id = {tournament_id}")
        fetched_flag = cursor.fetchone()

        if not fetched_flag:
            return "Failure: no entry for that tournament in tournaments table"

        if fetched_flag[0]:
            return "Tournament already scraped"

        tournament_url = f"{self.urlbase}Tournament/TR_RCR_{tournament_id}.html"
        tournament_page = requests.get(tournament_url)
        tournament_soup = BeautifulSoup(tournament_page.content, "html.parser")

        # Enter results for tournament
        results_table = tournament_soup.findAll(
            "div", {"class": "TCTT_lignes"})[0]
        results = results_table.findAll(
            "div", {"class": re.compile('TCTT_ligne*')})[1:]
        for result in results:
            result_content = result.findAll("p")
            position = int(result_content[0].text.strip())
            player_id = result_content[1].text.strip(
            ) if result_content[1].text.strip() != '-' else -1
            score = int(result_content[6].text.strip(
            )) if result_content[6].text.strip() != '-' else -1
            results_sql = f"INSERT OR IGNORE INTO tournament_results(tournament_id,player_id,score,position) VALUES({tournament_id},'{player_id}',{score},{position});"
            set_tourney_to_fetched_sql = f"UPDATE tournaments set fetched_flag = 1 where id = {tournament_id}"
            try:
                cursor.execute(results_sql)
                cursor.execute(set_tourney_to_fetched_sql)
            except Exception as e:
                print(f"An error occured: {e}")

        self.sqlconn.commit()

    def scrape_players_by_country(self):
        country = self.country

        url = f"{self.urlbase}Country/{country}_RCR.html"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        cursor = self.sqlconn.cursor()

        table = soup.findAll("div", {"class": "TCTT_lignes"})[0]
        # skip first row because it is a header
        results = table.findAll("div")[1:]
        for result in results:
            data = result.findAll("p")

            ema_id = data[2].text.strip()
            last_name = data[3].text.strip().title()
            first_name = data[4].text.strip().title()

            sql_insert = f"INSERT OR IGNORE INTO players VALUES({ema_id},'{last_name}','{first_name}','{country}');"
            cursor.execute(sql_insert)

        url = f"{self.urlbase}Players/{country}_History.html"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        results = table.findAll("div")[1:]

        self.sqlconn.commit()
