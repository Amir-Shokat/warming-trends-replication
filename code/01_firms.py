"""Step 1 - Firm-month sample from Compustat monthly security file.

Input : last.csv (gvkey, iid, datadate, tic, trt1m, exchg, city, naics), state.csv, uscities.csv
Output: data/processed/firms_monthly.parquet

One row per firm (gvkey) and month with HQ city/state, exchange city, industry,
heat-sensitive dummy and the monthly return.

Differences from the original notebooks (see AUDIT.md):
  * HQ is matched on city AND state (original: city name only; 1 in 3 US city
    names is shared by several places, e.g. Portland OR / Portland ME).
  * One share class per firm-month: primary US issue (iid without 'C' suffix,
    lowest iid). Original dropped iid and kept whichever row came first.
  * Return = log(1 + trt1m/100). trt1m is Compustat's split- and dividend-
    adjusted total return. The thesis used log(prccm_t / prccm_t-1) from
    unadjusted prices, which turns every stock split into a fake crash.
"""
import numpy as np
import pandas as pd
import config as C


def load_cities():
    u = pd.read_csv(C.USCITIES, usecols=["city", "state_id", "lat", "lng"])
    u = u[u.lat.between(*C.CONUS["lat"]) & u.lng.between(*C.CONUS["lng"])]
    return u.rename(columns={"state_id": "state"})


def main():
    cols = ["gvkey", "iid", "datadate", "tic", "trt1m", "exchg", "city", "naics"]
    df = pd.read_csv(C.COMPUSTAT_MONTHLY, usecols=cols,
                     dtype={"gvkey": str, "iid": str, "tic": str, "city": str})
    n0 = len(df)
    df["month"] = pd.to_datetime(df.datadate).dt.to_period("M")
    df = df[(df.month >= C.START) & (df.month <= C.END)]
    df = df[df.exchg.isin(C.EXCHANGE_CITY)]

    # HQ state (constant per firm in this extract)
    st = (pd.read_csv(C.COMPUSTAT_STATE, usecols=["gvkey", "state"], dtype={"gvkey": str})
          .dropna().drop_duplicates("gvkey"))
    df = df.merge(st, on="gvkey", how="left")

    cities = load_cities()
    df["hq_in_conus_name_only"] = df.city.isin(set(cities.city))          # thesis filter
    key = set(zip(cities.city, cities.state))
    df["hq_in_conus"] = [(c, s) in key for c, s in zip(df.city, df.state)]  # corrected filter
    df = df[df.hq_in_conus_name_only | df.hq_in_conus]

    # one share class per firm-month
    df["is_primary_class"] = ~df.iid.str.endswith("C")
    df = (df.sort_values(["gvkey", "month", "is_primary_class", "iid"],
                         ascending=[True, True, False, True])
            .drop_duplicates(["gvkey", "month"]))

    df["exch_city"] = df.exchg.map(lambda e: C.EXCHANGE_CITY[e][0])
    df["exch_state"] = df.exchg.map(lambda e: C.EXCHANGE_CITY[e][1])
    df["different_city"] = ((df.city != df.exch_city) | (df.state != df.exch_state)).astype("int8")
    df["different_city_legacy"] = (df.city != df.exch_city).astype("int8")

    df["naics2"] = pd.to_numeric(df.naics.astype("Int64").astype(str).str[:2], errors="coerce")
    df = df[df.naics2.notna() & (df.naics2 > 0)]
    df["heat_sensitive"] = df.naics2.isin(C.HEAT_SENSITIVE_NAICS2).astype("int8")

    r = df.trt1m / 100.0
    df["ret"] = np.where(r > -1, np.log1p(r.clip(lower=-0.9999)), np.nan)

    out = df[["gvkey", "iid", "month", "tic", "exchg", "exch_city", "exch_state", "city", "state",
              "hq_in_conus", "hq_in_conus_name_only", "different_city", "different_city_legacy",
              "naics", "naics2", "heat_sensitive", "trt1m", "ret"]].reset_index(drop=True)
    out["month"] = out.month.dt.to_timestamp()
    out.to_parquet(C.PROCESSED / "firms_monthly.parquet", index=False)
    print(f"rows read {n0:,} -> firm-months {len(out):,}; firms {out.gvkey.nunique():,}")
    print(f"  HQ city+state in CONUS: {out.hq_in_conus.mean():.1%}; "
          f"name-only match but wrong/absent state: {(~out.hq_in_conus).sum():,}")
    print(out.exch_city.value_counts().to_string())


if __name__ == "__main__":
    main()
