# ========================
# 2b. DATA STORAGE 
# ========================
import os
import pandas as pd
from sqlalchemy import create_engine, text


DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "bus_reliability")


CONN_STRING = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    return create_engine(CONN_STRING)


def create_database_if_not_exists():
    
    root_conn_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/"
    engine = create_engine(root_conn_string)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};"))
        conn.commit()
    print(f"Database '{DB_NAME}' ready.")


def export_to_mysql(df, table_name="trips", sample_fraction=None):
    
    print(f"\nExporting to MySQL table: {table_name}")

    
    expected_cols = ["agency_name"]
    missing = [c for c in expected_cols if c not in df.columns]
    

    create_database_if_not_exists()
    engine = get_engine()

    export_df = df.sample(fraction=sample_fraction, seed=42) if sample_fraction else df
    pdf = export_df.toPandas()

    pdf.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000)
    print(f"Exported {len(pdf):,} rows to table '{table_name}'")

    # Schema (for the "database schema diagram" deliverable — screenshot this)
    schema = pd.read_sql_query(f"DESCRIBE {table_name};", engine)
    print("\nSchema:")
    print(schema[["Field", "Type"]].to_string())

    return engine


def query_trips_by_operator(operator_name, table_name="trips", limit=5, operator_col="agency_name"):
   
    engine = get_engine()
    query = f"SELECT * FROM {table_name} WHERE {operator_col} = %s LIMIT %s;"
    result = pd.read_sql_query(query, engine, params=(operator_name, limit))
    return result


