# EMA Ranking tool

Tool to scrape ranking data from EMA Homepage http://mahjong-europe.org/

## To install

Requires Python 3.10 or later

Create a venv, install the requirements and run it.

'''
cd project_directory
python -m venv venv
source venv/bin/activate
pip -r requirements.txt
'''

## Files

[models.py](models.py) contains the sqlalchemy specification for the database that will hold
all the data on players and tournaments. SQLAlchemy implements and enforces
all the constraints and checks of a relational database, even if the underlying
database is sqlite3 (as it is here).

[scrapers.py](scrapers.py) contains some of the ranking calculation, but mostly contains
the code to scrape, parse and store player & tournament info from the existing
web pages

[test.py](test.py) is the file I use to run tests from. `testpy.log` is the logfile for
the test run, and contains the datetime stamp of when the run began, and any warnings arising during the run.

[alembic.ini](alembic.ini) is the control file for the `alembic` package, which makes it
easy to manage changes to the database structure.

[migrations](migrations) subfolder contains the control files created by `alembic`, that change the
database structure.

[httrack.log](httrack.log) is the log file from the httrack scrape of the original website

[requirements.txt](requirements.txt) is the list of 3rd-party python packages required

[data_scraper.py](data_scraper.py) is jesterboxboy's original scraper that showed it could be done,
and *how* it could be done

[ranking-queries.txt](ranking-queries.txt) lists the historical discrepancies I found when trying to reproduce all the rankings.
Note that almost all historic data can be reproduced. Only a small number of tied places that have non-standard
base-rank calculations remain, and none of these contribute to live rankins.

## To initialise the database

From the command line: `alembic --autogenerate -m "initialise db"`
Then edit the migration file in migrations/versions and remove the `metadata=MetaData(),` clause from the `ruleset` line

Then:
`alembic upgrade head`
will create the database file
