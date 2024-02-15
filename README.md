# EMA Ranking tool

Tool to scrape ranking data from EMA Homepage http://mahjong-europe.org/

## To install

Requires Python 3.10 or later

Create a venv, install the requirements and run it.

```
cd project_directory
python -m venv venv
source venv/bin/activate
pip -r requirements.txt
```

## Files

[models.py](models.py) contains the sqlalchemy specification for the database that will hold
all the data on players and tournaments.
[SQLAlchemy](https://www.sqlalchemy.org/) implements and enforces
all the constraints and checks of a relational database, even if the underlying
database is sqlite3 (as it is here).

[scrapers.py](scrapers.py) contains some of the ranking calculation, but mostly contains
the code to scrape, parse and store player & tournament info from the existing
web pages

[test.py](test.py) is the file I use to run tests from. [testpy.log](testpy.log) is the logfile for
the test run, and contains the datetime stamp of when the run began, and any warnings arising during the run.

[requirements.txt](requirements.txt) is the list of 3rd-party python packages required

[ranking-queries.txt](ranking-queries.txt) lists the historical discrepancies I found when trying to reproduce all the rankings.
Note that almost all historic data can be reproduced. Only a small number of tied places that have non-standard
base-rank calculations remain, and none of these contribute to live rankings.

[alembic.ini](alembic.ini) is the control file for the
[alembic](https://pypi.org/project/alembic/) package, which makes it
easy to manage changes to the database structure.

[migrations](migrations) subfolder contains the control files created by `alembic`, that change the
database structure.

[migrations/env.py](migrations/env.py) sets the environment for alembic to do its database magic

[data_scraper.py](data_scraper.py) is jesterboxboy's original scraper that showed it could be done,
and *how* it could be done

[httrack.log](httrack.log) is the log file from the httrack scrape of the original website

[ranking.py](ranking.py) doesn't do anything yet. I'm using as somewhere to store my
understanding of what the ranking algorithms are. It's got bits of untested code,
bits of pseudo-code, and plain text description of the algos.

## To initialise the database

At the moment, the filepath is hard-coded in
 [test.py](test.py) and [migrations/env.py](migrations/env.py). You must
 change the filepath in both places, to get it working for you.

Then, from the command line: `alembic revision --autogenerate -m "initialise db"`

The `autogenerate` means that alembic will read the (models.py)[models.py] file,
compare the implied database structure to the previous version, and create a
database migration file to update the database from the previous version to a
new version that satisfies `models.py`. So you can change the database structure
just by changing the code in `models.py` and running `alembic --autogenerate`.

The first time you run `alembic --autogenerate` you will need to edit the
migration file that this creates in `migrations/versions`. You must
remove the `metadata=MetaData(),` clause from the `ruleset` line
(this is a known alembic bug, and this is the far-from-satisfactory workaround)

Then:
`alembic upgrade head`
will create the database file.
