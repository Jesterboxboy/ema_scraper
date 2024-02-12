# EMA Ranking tool

Tool to scrape ranking data from EMA Homepage http://mahjong-europe.org/

## To install
Create a venv, install the requirements and run it.
'''
cd project_directory
pyhton -m venv venv
source venv/bin/activate
'''

## To initialse the database
`alembic --autogenerate -m "initialise db"`
Then edit the migration file in migrations/versions and remove the "metadata=MetaData()," clause from the ruleset line
Then:
`alembic upgrade head`
will create the database file

