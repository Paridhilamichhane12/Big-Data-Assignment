
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine

sns.set_style("whitegrid")

st.set_page_config(page_title="Bus Service Reliability Dashboard", layout="wide")

TABLE_NAME = "trips"


DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "bus_reliability")

CONN_STRING = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
OPERATOR_COL_CANDIDATES = ["agency_name", "operator", "agency_id", "route_short_name", "route_long_name"]


@st.cache_resource
def get_engine():
    return create_engine(CONN_STRING)


@st.cache_data
def load_data():
    engine = get_engine()
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME};", engine)
    return df


@st.cache_data
def query_by_operator(operator_name, operator_col):
   
    engine = get_engine()
    query = f"SELECT * FROM {TABLE_NAME} WHERE {operator_col} = %s;"
    result = pd.read_sql_query(query, engine, params=(operator_name,))
    return result


df = load_data()

st.title("🚌 Bus Service Reliability Dashboard")
st.caption("On-Time vs Delayed — Real BODS GTFS Data (Yorkshire)")


operator_col = next((c for c in OPERATOR_COL_CANDIDATES if c in df.columns), None)

if operator_col is None:
    st.error(
        "No operator/agency column found in the data "
        f"(looked for: {', '.join(OPERATOR_COL_CANDIDATES)}). "
        "Check that the export pipeline joins agency data before writing to MySQL."
    )
    st.stop()

st.sidebar.header("Filters")

operators = sorted(df[operator_col].dropna().unique().tolist())
selected_operators = st.sidebar.multiselect("Operator", operators, default=operators[:5])

if "is_peak_hour" in df.columns:
    peak_filter = st.sidebar.selectbox("Peak Hour", ["All", "Peak Only", "Off-Peak Only"])
else:
    peak_filter = "All"

filtered_df = df[df[operator_col].isin(selected_operators)] if selected_operators else df

if peak_filter == "Peak Only" and "is_peak_hour" in df.columns:
    filtered_df = filtered_df[filtered_df["is_peak_hour"] == 1]
elif peak_filter == "Off-Peak Only" and "is_peak_hour" in df.columns:
    filtered_df = filtered_df[filtered_df["is_peak_hour"] == 0]
