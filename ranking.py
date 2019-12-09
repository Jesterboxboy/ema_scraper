#!/usr/bin/python3

import argparse
import bs4
import csv
import urllib3,re

import pdb

#specifying arguments

helptext="Tool to calculate ranking by scraping data from EMA Homepage"
parser=argparse.ArgumentParser("Ranking Calculator", description=helptext)

parser.add_argument("startdate",help="start date of ranking period in YYYYMMDD format" )
parser.add_argument("enddate",help="end date of ranking period in YYYYMMDD format")
parser.add_argument("-n","--nationality",help="nationality for which ranking should be run, default is AUT",default="AUT")
parser.add_argument("-f","--file",help="name of output csv file",default="ranking.csv")
args=parser.parse_args()

#setting variables

startdate=args.startdate
enddate=args.enddate
nationality=args.nationality
ouputfile=args.file
baseurl="http://mahjong-europe.org"
#list holding all emaids of a country
playerlist=[]
##dictionary holding player information with emaid as key
playerinfo={}

debug=True

# function that takes nationality and returns a list of all emaids listed for that nationality on the EMA Site

def get_player_list( nationality ):

    playerlist = []
    url="{}/ranking/Country/{}_RCR.html".format(baseurl,nationality)
    http = urllib3.PoolManager()
    res = http.request('GET',url)
    soup = bs4.BeautifulSoup(res.data, 'html.parser')

    for emaid in soup.find_all('u'):
        if emaid.string.isdigit():
            playerlist.append(emaid.string)    

    return(playerlist)

# function that takes emaid and returns a dictionary with name and Club of the Player

def get_player_information( emaid ):
    
    playerinfo = {'country':nationality}
    #playerinfo = {'emaid': emaid, 'country': AUT}
    url="{}/ranking/Players/{}.html".format(baseurl,emaid)
    http = urllib3.PoolManager()
    res = http.request('GET',url)
    soup = bs4.BeautifulSoup(res.data, 'html.parser')
    results = soup.find_all("td", class_='PlayerBloc_2')

    for i in range(len(results)):
        if results[i].string == "Name :":
            playerinfo['name'] = results[i+1].string

        elif results[i].string == "Club :":
            playerinfo['club'] = results[i+1].string


    return(playerinfo)

# function to collect all tournamentinformation for a given emaid

# helperfunctions for get_tourney_info to parse the tables on website

def rowget_data_text(tr, coltag="td"):
    cols = []
    tr_clean = tr.find_all("tr")
    for td in tr.find_all(coltag):
        cols.append(td.get_text(strip=True))
    return cols

def table_data_text(table):
    rows = []
    trs = table.find_all("tbody") #rows are nested tr in tbody tags
    headerrow = rowget_data_text(trs[0],"th")
    if headerrow:
        trs = trs[1:]
    for tr in trs:
        rows.append(rowget_data_text(tr))
    return rows

def get_tourney_info(emaid):
    tablelist = []
    url="{}/ranking/Players/{}_History.html".format(baseurl,emaid)
    http = urllib3.PoolManager()
    res = http.request('GET',url)
    soup = bs4.BeautifulSoup(res.data, 'html.parser')
    results = soup.find_all("table", {'frame' : "BOX"})

    if debug:
        with open('soup.txt','w') as f:
            f.truncate()
            f.write(soup.prettify())

        with open('results.txt','w') as f:
            f.truncate()
            for i in results:
                f.write(i.text)

    if len(results) == 2:
        tablelist = table_data_text(results[1])
    elif len(results) == 1:
        tablelist = table_data_text(results[0])
    return tablelist




print("Calculating ranking from {0} to {1} for {2}".format(args.startdate, args.enddate,args.nationality))

if debug:
    #playerlist=['01000053','01000013']
    playerlist=['01000013']
else:
    playerlist=get_player_list(nationality)

for id in playerlist:
    playerinfo[id] = get_player_information(id)
    tourneyid = "{}_tourneys".format(id)
    playerinfo[tourneyid ] = get_tourney_info(id)



if debug:
    pdb.set_trace()

#print(*playerlist,sep="\n")

#for keys, values in playerinfo.items():
#    print (keys)
#    print (values)

print("The following players are in the list for {}.".format(nationality))
for x in playerinfo:
    print(x)
    for y in playerinfo[x]:
        print(y,':',playerinfo[x][y])



