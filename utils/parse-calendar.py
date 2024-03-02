# -*- coding: utf-8 -*-
"""
Created on Fri Dec 29 15:59:20 2023

@author: workm
"""

# import cchardet
# import lxml
import requests
from bs4 import BeautifulSoup

# The URL of the web page to scrape
url = 'http://mahjong-europe.org/ranking/Calendar.html'

# Make a request to the website
r = requests.get(url)

# Parse the HTML content
soup = BeautifulSoup(r.content, 'lxml')

# Find the div element with the class 'Tableau_CertifiedTournament'
table = soup.find('div', {'class': 'Tableau_CertifiedTournament'})

# Initialize a list to store the table rows
table_rows = soup.find_all('div', {'class': 'TCTT_ligneCalendarG'})
rows = []

# Loop through each child div of the table, which represents a row
for row in table_rows:
    # Initialize a dictionary to store the row data
    row_data = {}

    # Loop through each child p of the row, which represents a cell
    for i, cell in enumerate(row.find_all('p')):
        # Get the cell text
        text = cell.text.strip()

        # Assign the cell text to the corresponding key of the row data dictionary
        if i == 0:
            row_data['date'] = text
        elif i == 1:
            row_data['name'] = text
        elif i == 2:
            row_data['city'] = text
        elif i == 3:
            row_data['country'] = text
        elif i == 4:
            row_data['rules'] = text
        elif i == 5:
            row_data['mers'] = text
        elif i == 6:
            row_data['status'] = text

    # Append the row data dictionary to the rows list
    rows.append(row_data)

# Print the rows list
for row in rows:
    print(row)
