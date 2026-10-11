"""Paths and settings shared by every pipeline step.

Raw data is not included (licensed / ~28 GB). Every step reads the raw
downloads read-only from data/raw (or $THESIS_RAW_DATA) and writes its
outputs to data/processed as Parquet.
"""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
# Point THESIS_RAW_DATA at your own downloads; default data/raw.
RAW = Path(os.environ.get("THESIS_RAW_DATA", PROJECT / "data" / "raw"))
RAW_CLIMATE = RAW / "Climate Data"

PROCESSED = PROJECT / "data" / "processed"
TABLES = PROJECT / "output" / "tables"
LOGS = PROJECT / "output" / "logs"

# ---- Raw inputs (original downloads) ---------------------------------------
# Simplemaps US cities (city, state, lat, lng); the PRISM point queries were
# made with these coordinates, so lat/lng is the join key to PRISM.
USCITIES = RAW / "uscities.csv"

# PRISM monthly point time series, 61 files x <=500 locations each.
PRISM_TMEAN_DIRS = [RAW_CLIMATE / d for d in
                    ("1965 - 1979", "1980 - 1994", "1995 - 2009", "2010 - 2024")]
PRISM_MINMAX_DIRS = [RAW_CLIMATE / "min - max" / d for d in ("1995 - 2009", "2010 - 2024")]
PRISM_DAILY_NORMALS_DIR = RAW_CLIMATE / "daily"      # 1991-2020 daily normals
PRISM_HEADER_ROWS = 10

# Compustat (WRDS) extracts
COMPUSTAT_MONTHLY = RAW / "last.csv"                  # gvkey,iid,datadate,tic,trt1m,exchg,city,naics
COMPUSTAT_STATE = RAW_CLIMATE / "state.csv"           # gvkey,iid,datadate,state
COMPUSTAT_MONTHLY_PRICE = RAW_CLIMATE / "monthly price.csv"  # gvkey,iid,datadate,prccm (unadjusted)
COMPUSTAT_DAILY = [RAW / f for f in ("daily1.csv", "daily2.csv", "daily3.csv")]  # gvkey,iid,datadate,prccd,exchg,city
MARKET = RAW_CLIMATE / "SP500 and VIX.csv"                    # date (YYYY-MM), SP500, VIX (monthly % changes)

# The thesis's final regression file, used only to check the rebuild.
LEGACY_FINAL = RAW_CLIMATE / "log-return.csv"

# ---- Sample definition (as in the thesis) -----------------------------------
START, END = "1995-01", "2024-01"
# Compustat exchange codes kept in the thesis -> city of the exchange.
# NOTE: 13 = OTC Bulletin Board and 14 = NASDAQ; both were mapped to New York.
EXCHANGE_CITY = {11: ("New York", "NY"), 12: ("New York", "NY"), 13: ("New York", "NY"),
                 14: ("New York", "NY"), 15: ("New York", "NY"), 16: ("Chicago", "IL"),
                 17: ("New York", "NY"), 18: ("Philadelphia", "PA")}
# Continental-US bounding box used in the thesis to drop AK/HI/territories.
CONUS = dict(lat=(24.396308, 49.384472), lng=(-125.00165, -66.93457))
# Heat-sensitive NAICS 2-digit sectors (Graff Zivin & Neidell 2014; Addoum et al. 2020).
# The code always used 22 for Utilities; the thesis text says 21 by mistake.
HEAT_SENSITIVE_NAICS2 = {11, 21, 22, 23, 31, 32, 33, 48, 49}

# ---- Climate settings --------------------------------------------------------
LEGACY_MA_YEARS = 30           # thesis: 30-year same-month moving average (includes current year)
NORMALS_PERIOD = "1991-2020"   # PRISM official normals used as fixed baseline for tmin/tmax

# ---- Corrections (each documented in AUDIT.md) --------------------------------
SPLIT_DAY_ABS_LOGRET = 0.5     # daily |log return| above this treated as split/data error (no adj. factors downloaded)
# common forward and reverse split ratios (new price / old price)
SPLIT_RATIOS = [1/2, 1/3, 1/4, 1/5, 1/10, 2/3, 3/4, 4/5, 3/5, 2/5,
                2, 3, 4, 5, 10, 3/2, 4/3, 5/4, 5/3, 5/2]
# month-level check: sum of daily log returns vs log(1 + trt1m); larger gap = missed split
MAX_MONTH_GAP = 0.15
MIN_TRADING_DAYS = 15          # minimum daily returns per month to compute a monthly volatility
WINSOR = (0.005, 0.995)        # winsorize returns and volatility at 0.5% / 99.5%

for p in (PROCESSED, TABLES, LOGS):
    p.mkdir(parents=True, exist_ok=True)
