# EMA Ranking tool

Tool to scrape ranking data from EMA Homepage http://mahjong-europe.org/

## To install

Requires Python 3.10 or later

Create a virtual environment, and install the requirements:

```
cd project_directory
python -m venv venv
source venv/bin/activate
pip -r requirements.txt
```

## Files

### Configuration

[requirements.txt](requirements.txt) is the list of 3rd-party python packages
required

[models.py](models.py) contains the [SQLAlchemy](https://www.sqlalchemy.org/)
specification for the database that holds all the data on players and
tournaments. SQLAlchemy implements and enforces all the constraints
and checks of a relational database, even if the underlying
database is sqlite3 (as it is here).

[config.py](config.py) contains user-specific configurations. At the moment,
this is the path to the database, and the directory for html output files.

[alembic.ini](alembic.ini) is the control file for the
[alembic](https://pypi.org/project/alembic/) package, which makes it
easier to manage changes to the database structure.

[migrations](migrations) subfolder contains the control files created by
alembic, that change the database structure.

[migrations/env.py](migrations/env.py) sets the environment for alembic to do
its database magic

### Calculation : `calculators/`

[get_results.py](calculators/get_results.py) processes the current results template, and
stores the results in the database (Work in progress)

[ranking.py](calculators/ranking.py) contains the EMA ranking calculation. This has now
been verified for all players, for both rulesets.

[country_ranking.py](calculators/country_ranking.py) contains the EMA country ranking
calculation. This has now been verified for all countries, for both rulesets.

[quota.py](calculators/quota.py) will contain the algorithm to calculate country quotas
for quota tournaments such as WRC, ERMC, and OEMC. This does not yet work. It
runs to completion, but does not match the examples given on the
[mcr](https://silk.mahjong.ie/ranking/quotas_MCR.html)
and
[riichi](https://silk.mahjong.ie/ranking/quotas_RCR.html)
example pages

[ranking_austria_riichi.py](calculators/ranking_austria_riichi.py) contains function to calculate the
ranking for the Austrian Riichi Mahjong Association that is used in deciding who gets quota seats for
ERMC and WRC.


### Page renderers : `renderers/`

[render_player.py](renderers/render_player.py) write a static player profile
page. This downloads the jinja template from
https://silk.mahjong.ie/template-player/ and populates it.

[render_results.py](renderers/render_results.py) writes a static tournament results
page. This downloads the jinja template from
https://silk.mahjong.ie/template-results/ and populates it.

[render_year.py](renderers/render_year.py) writes the static page that lists all the
tournaments for a given year. This downloads the jinja template from
https://silk.mahjong.ie/template-year/ and populates it.

### Other : `utils/`

[scrapers.py](utils/scrapers.py) contains
the code to scrape, parse and store player & tournament info from the existing
web pages

[test.py](test.py) is the file I use to run tests from.
[testpy.log](testpy.log) is the logfile for
the test run, and contains the datetime stamp of when the run began, and any
warnings arising during the run.

[ranking-queries.txt](ranking-queries.txt) lists the historical discrepancies
that I found when trying to reproduce all the rankings.
Note that almost all historic data can be reproduced. Only a small number of
tied places that have non-standard
base-rank calculations remain, and none of these contribute to live rankings.

[httrack.log](httrack.log) is the log file from the httrack scrape of the
original website

[csv_writer.py](utils/csv_writer.py) Simple function that writes out the dict
produced by (calculators/ranking_austria.py) to a csv file.


## To initialise the database

Set the path to your database in [config.py](config.py) and check if the folder
`migrations/versions` exists.

Then, from the command line:
`alembic revision --autogenerate -m "initialise db"`

The `autogenerate` means that alembic will read `models.py`,
compare the implied database structure to the previous version, and create a
database migration file to update the database from the previous version to a
new version that satisfies `models.py`. So you can change the database
structure just by changing the code in `models.py` and running
`alembic revision --autogenerate`.

The first time you run `alembic revision --autogenerate` you will subsequently
need to edit the migration file that this creates in `migrations/versions`.
You must remove the two `metadata=MetaData(),` clauses from the `ruleset` lines
in the definitions of `tournament` and `player_x_tournament`
(this is a known alembic bug, and this is the far-from-satisfactory workaround)

Then:
`alembic upgrade head`
will create the database file.

## Wider environment

Current development of the rendering files assumes a platform of Wordpress with
the Decode theme, (which is no longer supported, but is a lovely clean theme)
and the [Tablepress plugin](https://wordpress.org/plugins/tablepress/). The
Tablepress tables are exported into CSV files, which are tracked in this
repository.

I'm pretty agnostic on this, and adapting it to other platforms should be easy.
