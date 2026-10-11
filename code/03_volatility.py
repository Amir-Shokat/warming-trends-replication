"""Step 3 - Monthly volatility (SD of daily log returns) from Compustat daily prices.

Input : daily1.csv, daily2.csv, daily3.csv (raw WRDS: gvkey, iid, datadate, prccd, exchg, city)
        daily_1995-2005.csv, daily_2006-2016.csv, daily_2017-2024.csv (thesis intermediates, legacy only)
Output: data/processed/volatility_monthly.parquet

  sd_legacy : the thesis calculation - log(p_t / p_t-1) over the whole file in
              file order (NOT grouped by firm, so each firm's first return uses the
              previous firm's last price), all share classes mixed, unadjusted prices.
  sd        : corrected - returns computed within firm and share class; split days
              dropped (price ratio within 2% of a common split ratio such as 1/2, 2/3,
              4/5, or |log return| > SPLIT_DAY_ABS_LOGRET; the extract has no adjustment
              factors); months with < MIN_TRADING_DAYS
              returns set to missing.
  n_days, n_split_days : diagnostics.

Proper fix (recommended): re-download prccd with ajexdi and trfd from WRDS and
compute adjusted returns; then SPLIT_DAY_ABS_LOGRET is no longer needed.
"""
import numpy as np
import pandas as pd
import config as C

# thesis intermediates (iid already dropped in the last one) -> used only for sd_legacy
LEGACY_FILES = [C.RAW / f for f in ("daily_1995-2005.csv", "daily_2006-2016.csv", "daily_2017-2024.csv")]
# original WRDS downloads (keep iid) -> used for the corrected sd
RAW_FILES = C.COMPUSTAT_DAILY


def legacy_file(path):
    d = pd.read_csv(path, usecols=["gvkey", "datadate", "prccd"],
                    dtype={"gvkey": "int32", "prccd": "float64"}, parse_dates=["datadate"])
    d["month"] = d.datadate.values.astype("datetime64[M]")
    d["r"] = np.log(d.prccd / d.prccd.shift(1))       # whole file, not grouped (thesis)
    return d.groupby(["gvkey", "month"]).r.std().rename("sd_legacy").reset_index()


def raw_file(path):
    d = pd.read_csv(path, usecols=["gvkey", "iid", "datadate", "prccd"],
                    dtype={"gvkey": "int32", "iid": "category", "prccd": "float64"},
                    parse_dates=["datadate"])
    d["month"] = d.datadate.values.astype("datetime64[M]")
    d = d[(d.month >= C.START) & (d.month <= C.END)]
    d = d[d.prccd > 0].sort_values(["gvkey", "iid", "datadate"])
    prev = d.groupby(["gvkey", "iid"], observed=True).prccd.shift(1)
    d["r"] = np.log(d.prccd / prev)
    # split days: price ratio within 2% of a common split ratio, or |r| above the hard cap
    ratio = d.prccd / prev
    near = np.zeros(len(d), dtype=bool)
    for k in C.SPLIT_RATIOS:
        near |= (np.abs(ratio / k - 1) < 0.02).to_numpy()
    priced = ((d.prccd >= 1) & (prev >= 1)).to_numpy()   # tick moves of penny stocks look like ratios
    d["split_day"] = (near & priced & (d.r.abs() > 0.15).to_numpy()) | (d.r.abs() > C.SPLIT_DAY_ABS_LOGRET).to_numpy()
    d.loc[d.split_day, "r"] = np.nan
    g = d.groupby(["gvkey", "iid", "month"], observed=True)
    cor = pd.DataFrame({"sd": g.r.std(), "n_days": g.r.count(), "n_split_days": g.split_day.sum(),
                        "sum_r": g.r.sum()})
    cor.loc[cor.n_days < C.MIN_TRADING_DAYS, "sd"] = np.nan
    return cor.reset_index()


def main():
    legs, cors = [], []
    for p in LEGACY_FILES:
        legs.append(legacy_file(p))
    for p in RAW_FILES:
        c = raw_file(p)
        cors.append(c)
        print(f"{p.name}: firm-months {len(c):,}, split-like days dropped {int(c.n_split_days.sum()):,}")
    leg = pd.concat(legs).drop_duplicates(["gvkey", "month"])
    cor = pd.concat(cors).drop_duplicates(["gvkey", "iid", "month"])
    cor["iid"] = cor.iid.astype(str)
    cor["gvkey"] = cor.gvkey.astype(str).str.zfill(6)
    leg["gvkey"] = leg.gvkey.astype(str).str.zfill(6)
    cor.to_parquet(C.PROCESSED / "volatility_monthly.parquet", index=False)
    leg.to_parquet(C.PROCESSED / "volatility_monthly_legacy.parquet", index=False)
    print(cor[["sd", "n_days"]].describe().T.round(4).to_string())
    print(leg[["sd_legacy"]].describe().T.round(4).to_string())


if __name__ == "__main__":
    main()
