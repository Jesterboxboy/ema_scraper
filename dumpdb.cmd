sqlite3 -header -csv ema.sqlite3 "select * from player where ema_id > -1;" > players.csv
sqlite3 -header -csv ema.sqlite3 "select * from tournament;" > tournament.csv
