"""Step 2 - Monthly climate anomalies per location (PRISM point time series).

Input : PRISM monthly CSVs (tmean+ppt 1965-2024; tmin/tmax 1995-2024),
        PRISM 1991-2020 daily normals, uscities.csv
Output: data/processed/climate_monthly.parquet  (one row per location x month, 1995-2024)

Each PRISM row carries the query coordinates, so locations are identified by
(lat, lng) and joined to Simplemaps to get the full city name AND state.
Only locations needed by the firm sample (HQ cities + exchange cities) are kept.

Variables
  LEGACY (reproduce the thesis exactly; all absolute values):
    T_mean_legacy = |tmean - MA30(tmean, same month, incl. current year)|
    T_max_legacy  = |tmax  - MA30(tmean ...)|   <- BUG: tmax compared with the *tmean* baseline
    T_min_legacy  = |tmin  - MA30(tmean ...)|   <- BUG: same
    P_legacy      = |ppt   - MA30(ppt ...)|
  CORRECTED (signed, each variable against its own baseline):
    tmean_anom  = tmean - mean(tmean, same month, previous 30 years)   (trailing, excludes current year)
    tmax_anom   = tmax  - PRISM 1991-2020 normal tmax for that month
    tmin_anom   = tmin  - PRISM 1991-2020 normal tmin for that month
    tmean_anom_norm = tmean - 1991-2020 normal (fixed-baseline robustness)
    hot  = max(tmean_anom, 0);  cold = max(-tmean_anom, 0)
    tmean_absanom = |tmean_anom|  (magnitude, as in the thesis but with a clean baseline)
    ppt_anom_z  = (ppt - trailing 30y same-month mean) / trailing 30y same-month SD
"""
import glob
import numpy as np
import pandas as pd
import config as C

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def needed_locations():
    f = pd.read_parquet(C.PROCESSED / "firms_monthly.parquet", columns=["city", "state"])
    pairs = set(map(tuple, f.drop_duplicates().values))
    pairs |= {v for v in C.EXCHANGE_CITY.values()}
    names = set(f.city)  # for the legacy name-only lookup
    u = pd.read_csv(C.USCITIES, usecols=["city", "state_id", "lat", "lng"]).rename(columns={"state_id": "state"})
    u = u[u.lat.between(*C.CONUS["lat"]) & u.lng.between(*C.CONUS["lng"])]
    u = u[[(c, s) in pairs for c, s in zip(u.city, u.state)] | u.city.isin(names)]
    u["lat4"], u["lng4"] = u.lat.round(4), u.lng.round(4)
    return u.drop_duplicates(["lat4", "lng4"])


def read_prism(dirs, keep, cols, file_pattern="*.csv"):
    """Read PRISM files in the original order (1..61), keep needed coordinates."""
    out = []
    for d in dirs:
        files = sorted(glob.glob(str(d / file_pattern)),
                       key=lambda p: int(p.rsplit("(", 1)[1].split(")")[0]))
        for order, p in enumerate(files):
            x = pd.read_csv(p, skiprows=C.PRISM_HEADER_ROWS)
            x["lat4"], x["lng4"] = x.Latitude.round(4), x.Longitude.round(4)
            x = x.merge(keep, on=["lat4", "lng4"])
            x["file_order"] = order
            out.append(x[["lat4", "lng4", "Name", "file_order", "Date"] + cols])
    return pd.concat(out, ignore_index=True)


def main():
    loc = needed_locations()
    keep = loc[["lat4", "lng4"]]
    print(f"locations needed: {len(loc):,}")

    tm = read_prism(C.PRISM_TMEAN_DIRS, keep, ["ppt (inches)", "tmean (degrees F)"])
    tm.columns = ["lat4", "lng4", "Name", "file_order", "Date", "ppt", "tmean"]
    mm = read_prism(C.PRISM_MINMAX_DIRS, keep, ["tmin (degrees F)", "tmax (degrees F)"])
    mm.columns = ["lat4", "lng4", "Name", "file_order", "Date", "tmin", "tmax"]
    for x in (tm, mm):
        x["month"] = pd.to_datetime(x.Date, format="%Y-%m")
    tm = tm.drop_duplicates(["lat4", "lng4", "month"])
    mm = mm.drop_duplicates(["lat4", "lng4", "month"])

    # ---- 1991-2020 normals (daily -> monthly) ----
    nm = read_prism([C.PRISM_DAILY_NORMALS_DIR], keep,
                    ["ppt (inches)", "tmin (degrees F)", "tmean (degrees F)", "tmax (degrees F)"])
    nm.columns = ["lat4", "lng4", "Name", "file_order", "Date", "ppt", "tmin", "tmean", "tmax"]
    nm["moy"] = nm.Date.str.split("-").str[0].map(MONTHS)
    nm = (nm.drop_duplicates(["lat4", "lng4", "Date"])
            .groupby(["lat4", "lng4", "moy"])
            .agg(norm_tmin=("tmin", "mean"), norm_tmean=("tmean", "mean"),
                 norm_tmax=("tmax", "mean"), norm_ppt=("ppt", "sum")).reset_index())

    # ---- moving baselines on tmean / ppt (per location and calendar month) ----
    tm = tm.sort_values(["lat4", "lng4", "month"])
    tm["moy"] = tm.month.dt.month
    g = tm.groupby(["lat4", "lng4", "moy"])
    tm["ma30_incl_t"] = g.tmean.transform(lambda s: s.rolling(C.LEGACY_MA_YEARS, min_periods=1).mean())
    tm["ma30_incl_p"] = g.ppt.transform(lambda s: s.rolling(C.LEGACY_MA_YEARS, min_periods=1).mean())
    tm["ma30_prev_t"] = g.tmean.transform(lambda s: s.shift(1).rolling(30, min_periods=25).mean())
    tm["ma30_prev_p"] = g.ppt.transform(lambda s: s.shift(1).rolling(30, min_periods=25).mean())
    tm["sd30_prev_p"] = g.ppt.transform(lambda s: s.shift(1).rolling(30, min_periods=25).std())

    df = (tm.merge(mm[["lat4", "lng4", "month", "tmin", "tmax"]], on=["lat4", "lng4", "month"], how="left")
            .merge(nm, on=["lat4", "lng4", "moy"], how="left"))
    df = df[(df.month >= C.START) & (df.month <= C.END)]

    # legacy (thesis) variables
    df["T_mean_legacy"] = (df.tmean - df.ma30_incl_t).abs()
    df["T_max_legacy"] = (df.tmax - df.ma30_incl_t).abs()
    df["T_min_legacy"] = (df.tmin - df.ma30_incl_t).abs()
    df["P_legacy"] = (df.ppt - df.ma30_incl_p).abs()
    # corrected variables
    df["tmean_anom"] = df.tmean - df.ma30_prev_t
    df["tmean_absanom"] = df.tmean_anom.abs()
    df["hot"] = df.tmean_anom.clip(lower=0)
    df["cold"] = (-df.tmean_anom).clip(lower=0)
    df["tmean_anom_norm"] = df.tmean - df.norm_tmean
    df["tmax_anom"] = df.tmax - df.norm_tmax
    df["tmin_anom"] = df.tmin - df.norm_tmin
    df["ppt_anom_z"] = (df.ppt - df.ma30_prev_p) / df.sd30_prev_p.where(df.sd30_prev_p > 0.01)  # never-rains months -> NaN

    df = df.merge(loc[["lat4", "lng4", "city", "state"]], on=["lat4", "lng4"], how="left")
    keepcols = ["lat4", "lng4", "city", "state", "Name", "file_order", "month", "tmean", "tmin", "tmax", "ppt",
                "T_mean_legacy", "T_max_legacy", "T_min_legacy", "P_legacy",
                "tmean_anom", "tmean_absanom", "hot", "cold", "tmean_anom_norm",
                "tmax_anom", "tmin_anom", "ppt_anom_z"]
    df[keepcols].to_parquet(C.PROCESSED / "climate_monthly.parquet", index=False)
    print(f"climate rows {len(df):,}; locations {df[['lat4','lng4']].drop_duplicates().shape[0]:,}")
    print(df[["T_mean_legacy", "T_max_legacy", "T_min_legacy", "tmean_anom",
              "tmax_anom", "tmin_anom", "ppt_anom_z"]].describe().T.round(2).to_string())


if __name__ == "__main__":
    main()
