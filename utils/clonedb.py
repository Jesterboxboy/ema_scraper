"""
Modified from https://stackoverflow.com/a/76616012 CC-BY-SA 4.0

UNTESTED

Not sure if we're going to use this yet.

It could be useful if we allow web users to run simulations of quotas:
we could clone the db to a db in memory, to run experiments on it without
contaminating the main db
"""

from sqlalchemy import MetaData, create_engine, event

src_engine = create_engine("sqlite:///mydb.sqlite")
src_metadata = MetaData()
exclude_tables = ("sqlite_master", "sqlite_sequence", "sqlite_temp_master")

tgt_engine = engine=create_engine('sqlite://')
tgt_metadata = MetaData()


@event.listens_for(src_metadata, "column_reflect")
def genericize_datatypes(inspector, tablename, column_dict):
    column_dict["type"] = column_dict["type"].as_generic(allow_nulltype=True)


src_conn = src_engine.connect()
tgt_conn = tgt_engine.connect()
tgt_metadata.reflect(bind=tgt_engine)

# drop all tables in target database
for table in reversed(tgt_metadata.sorted_tables):
    if table.name not in exclude_tables:
        print("dropping table =", table.name)
        table.drop(bind=tgt_engine)

tgt_metadata.clear()
tgt_metadata.reflect(bind=tgt_engine)
src_metadata.reflect(bind=src_engine)

# create all tables in target database
for table in src_metadata.sorted_tables:
    if table.name not in exclude_tables:
        table.create(bind=tgt_engine)

# refresh metadata before you can copy data
tgt_metadata.clear()
tgt_metadata.reflect(bind=tgt_engine)

# Copy all data from src to target
for table in tgt_metadata.sorted_tables:
    src_table = src_metadata.tables[table.name]
    stmt = table.insert()
    for index, row in enumerate(src_conn.execute(src_table.select())):
        print("table =", table.name, "Inserting row", index)
        tgt_conn.execute(stmt.values(row))

tgt_conn.commit()
src_conn.close()
tgt_conn.close()
