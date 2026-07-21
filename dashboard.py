
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

# ------------------------------------------------------------------
# Top-level KPIs
# ------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

total_trips = len(filtered_df)
delay_col = "is_delayed" if "is_delayed" in filtered_df.columns else None

with col1:
    st.metric("Total Trips", f"{total_trips:,}")

if delay_col:
    on_time_rate = 1 - filtered_df[delay_col].mean() if total_trips > 0 else 0
    with col2:
        st.metric("On-Time Rate", f"{on_time_rate:.1%}", delta=f"{on_time_rate - 0.85:.1%} vs 85% target")
    with col3:
        st.metric("Delayed Trips", f"{int(filtered_df[delay_col].sum()):,}")
    with col4:
        st.metric("Operators Shown", f"{len(selected_operators)}")
else:
    st.info("No 'is_delayed' column found — delay-based KPIs are unavailable for this dataset.")

st.divider()



st.subheader(f"Delay Rate by {operator_col.replace('_', ' ').title()}")

if delay_col and total_trips > 0:
    op_agg = (
        filtered_df.groupby(operator_col)[delay_col]
        .agg(["mean", "count"])
        .rename(columns={"mean": "delay_rate", "count": "trips"})
        .query("trips >= 20")
        .sort_values("delay_rate", ascending=False)
    )

    if op_agg.empty:
        st.info("No operator has at least 20 trips in the current filter selection.")
    else:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x=op_agg["delay_rate"], y=op_agg.index, palette="viridis", ax=ax)
        ax.set_xlabel("Delay Rate")
        ax.set_ylabel(operator_col.replace("_", " ").title())
        st.pyplot(fig)

        st.dataframe(op_agg.style.format({"delay_rate": "{:.1%}"}))
elif not delay_col:
    st.info("Delay rate chart unavailable — no 'is_delayed' column in the data.")


hour_col = "hour_of_day" if "hour_of_day" in filtered_df.columns else (
    "arrival_hour" if "arrival_hour" in filtered_df.columns else None
)

if hour_col and delay_col and total_trips > 0:
    st.subheader("Delay Rate by Hour of Day")
    hourly = filtered_df.groupby(hour_col)[delay_col].mean()

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    sns.lineplot(x=hourly.index, y=hourly.values, marker="o", ax=ax2)
    ax2.set_xlabel("Hour")
    ax2.set_ylabel("Delay Rate")
    ax2.set_xticks(range(0, 24))
    st.pyplot(fig2)

st.divider()

st.subheader(f"Explore Trips by {operator_col.replace('_', ' ').title()}")

if operators:
    lookup_operator = st.selectbox("Choose a value to inspect", operators)
    if lookup_operator:
        result = query_by_operator(lookup_operator, operator_col)
        st.write(f"Showing {len(result):,} trips for **{lookup_operator}**")
        st.dataframe(result.head(100))
else:
    st.info("No values available to explore.")

st.divider()
st.caption(
    "Data source: BODS GTFS (Yorkshire) via MySQL. "
    "All queries use parameterised SQL (no string concatenation)."
)