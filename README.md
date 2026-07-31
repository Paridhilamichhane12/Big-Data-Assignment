# Bus Service Reliability Classification (On-Time vs Delayed)

A PySpark Big Data Analytics pipeline that classifies individual scheduled bus stops as On-Time
or Delayed, using real GTFS static data from the ITM Yorkshire bus network (~6.48 million
`stop_times` records, 138,436 trips, 1,243 routes).

Built for **ST5011CEM — Big Data Programming Project**, Softwarica College of IT & E-Commerce,
in collaboration with Coventry University.

---

## Project Overview

The pipeline ingests raw GTFS files, cleans and joins them in PySpark, engineers a leakage-checked
feature set, trains and compares three classification models (Logistic Regression, Random Forest,
Gradient-Boosted Trees), and persists results to both MySQL (trip-level data, powering an
interactive dashboard) and SQLite (summary results). A Streamlit dashboard provides a
stakeholder-facing view of delay rates by operator and time of day.

**Best model (current run):** Logistic Regression — Accuracy 0.8001, F1 0.7504, ROC-AUC 0.6656.

---

## Repository Structure

```
.
├── notebooks/              # Main analysis notebook (data loading -> EDA -> ML -> export)
├── src/
│   ├── mysql_storage.py    # MySQL export + parameterised queries
│   └── dashboard.py        # Streamlit dashboard (reads from MySQL)
├── docs/                   # Report, architecture diagram, ER diagram
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.10+
- Java (JDK 8, 11, or 17) — required by PySpark
- MySQL Server (running locally or remotely)
- ~8GB+ RAM recommended (16GB preferred for the full, unsampled dataset)

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/Paridhilamichhane12/Big-Data-Assignment.git
cd Big-Data-Assignment
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up MySQL
Ensure MySQL Server is running, then set your credentials as environment variables
(**never hard-code these in code**):

```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password_here
export DB_NAME=bus_reliability
```

On Windows (Command Prompt): use `set` instead of `export`.
On Windows (PowerShell): use `$env:DB_HOST="localhost"`, etc.

The export script (`src/mysql_storage.py`) will raise an explicit error if `DB_PASSWORD` is not
set — it will not silently fall back to an empty password.

### 4. Obtain the GTFS data
Raw GTFS files are **not included in this repository** (excluded via `.gitignore` due to size).
Download the ITM Yorkshire GTFS feed from the
[Bus Open Data Service](https://data.bus-data.dft.gov.uk/) and place the following files in a
`gtfs_yorkshire/` folder at the project root:

```
agency.txt, calendar.txt, calendar_dates.txt, routes.txt,
stops.txt, stop_times.txt, trips.txt, frequencies.txt
```

---

## Running the Pipeline

Run the notebook in `notebooks/` cell by cell, in this order:

1. **SparkSession setup** — configures memory/partitions for your machine
2. **`load_gtfs_data()`** — loads raw GTFS files into PySpark DataFrames
3. **`clean_gtfs_data()`** — fills missing values, converts overnight timestamps
4. **`engineer_features()`** — joins tables, builds `is_delayed` label, applies broadcast joins,
   caching, and repartitioning
5. **MySQL export** (`src/mysql_storage.py` code) — exports the feature-engineered dataset
6. **`perform_eda()`** — exploratory analysis and visualisations
7. **`statistical_profile()`** — mean/median/std/skewness/kurtosis, outlier detection
8. **`prepare_ml_data()`** — feature vector assembly (leakage-checked: excludes
   `travel_time_to_prev_stop`, `route_avg_travel_time`, and `stop_avg_travel_time`)
9. **`train_and_compare_models()`** — trains and evaluates all 3 models

### Running the dashboard
Once the MySQL export (step 5) has completed successfully:
```bash
streamlit run src/dashboard.py
```
Opens automatically at `http://localhost:8501`.

---

## Configuration Notes

- **Spark session**: configured with 32–64 shuffle partitions (tuned up from an initial 8 after
  `OutOfMemoryError` failures on the full dataset), Kryo serialization, and adaptive query
  execution enabled.
- **Memory constraints**: Random Forest and GBT are trained on a 20% stratified subsample of the
  training set due to local hardware limits; Logistic Regression trains on the full set. This is a
  documented trade-off, not a bug — see the report's Critical Reflection section.
- **Database credentials**: read exclusively from environment variables at runtime. Never commit a
  `.env` file or hard-code a password — check `.gitignore` includes `.env` and `*.db` before
  committing.

---

## Known Limitations

- The `is_delayed` label is derived from scheduled travel-time deviation, not genuine real-time
  GTFS-RT/SIRI-VM observations, since those feeds were only available as single point-in-time
  snapshots during development (see report Section 4.6).
- Delay rates for hours 00:00–04:00 are based on very low trip counts (43–9,259 trips, versus
  400,000+ during peak daytime hours) and should be interpreted cautiously — flagged automatically
  by a relative-threshold check in `perform_eda()`.
- Two rounds of target leakage were identified and corrected during feature engineering — see
  report Section 5.1 for the full leakage-check methodology and results.

---

## Author

Paridhi Lamichhane

## License / Data Attribution

GTFS data sourced from the UK Department for Transport's
[Bus Open Data Service](https://data.bus-data.dft.gov.uk/), used under its open data terms. This
repository contains only code and documentation — raw GTFS data files are excluded from version
control.
