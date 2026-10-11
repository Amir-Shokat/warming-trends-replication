"""Step 4 - Merge firms, returns, volatility, climate and market controls into one panel.

Output: data/processed/panel.parquet  (one row per firm-month)

Climate is attached twice:
  * corrected: HQ climate matched on (city, state); exchange-city climate on (city, state)
  * legacy   : matched on city NAME only, picking the first PRISM location with that
               name in file order (what pivot_table(aggfunc='first') did in the thesis)
Columns with suffix _hq / _ex are headquarters / exchange-city climate.
"""
import numpy as np
import pandas as pd
import config as C

CORR = ["tmean_anom", "tmean_absanom", "hot", "cold", "tmean_anom_norm", "tmax_anom", "tmin_anom", "ppt_anom_z"]
LEG = ["T_mean_legacy", "T_max_legacy", "T_min_legacy", "P_legacy"]


def winsor(s, lo=C.WINSOR[0], hi=C.WINSOR[1]):
    a, b = s.quantile([lo, hi])
    return s.clip(a, b)


def main():
    f = pd.read_parquet(C.PROCESSED / "firms_monthly.parquet")
    vol = pd.read_parquet(C.PROCESSED / "volatility_monthly.parquet")
    leg_vol = pd.read_parquet(C.PROCESSED / "volatility_monthly_legacy.parquet")
    clim = pd.read_parquet(C.PROCESSED / "climate_monthly.parquet")

    p = f.merge(vol[["gvkey", "iid", "month", "sd", "n_days", "sum_r"]], on=["gvkey", "iid", "month"], how="left")
    # trt1m is split-adjusted; daily prices are not. A big gap between the two means a
    # split (or data error) the daily filter missed -> drop that month's volatility.
    p["month_gap"] = (p.sum_r - p.ret).abs()
    p["vol_flagged"] = p.month_gap > C.MAX_MONTH_GAP
    p.loc[p.vol_flagged, "sd"] = np.nan
    p = p.merge(leg_vol, on=["gvkey", "month"], how="left")

    # corrected climate: (city, state)
    cc = clim[["city", "state", "month"] + CORR + LEG].drop_duplicates(["city", "state", "month"])
    p = p.merge(cc.rename(columns={c: c + "_hq" for c in CORR + LEG}), on=["city", "state", "month"], how="left")
    ex = cc.rename(columns={"city": "exch_city", "state": "exch_state", **{c: c + "_ex" for c in CORR + LEG}})
    p = p.merge(ex, on=["exch_city", "exch_state", "month"], how="left")

    # legacy climate: first location by name (file order), name-only match
    first = (clim.sort_values(["file_order"]).drop_duplicates(["city", "month"])
                 [["city", "month"] + LEG])
    p = p.merge(first.rename(columns={c: c + "_hq_nameonly" for c in LEG}), on=["city", "month"], how="left")

    m = pd.read_csv(C.MARKET)
    m["month"] = pd.to_datetime(m.date, format="%Y-%m")
    p = p.merge(m[["month", "SP500", "VIX"]], on="month", how="left")

    p["year"] = p.month.dt.year
    p["ret_w"] = winsor(p.ret)
    p["sd_w"] = winsor(p.sd)
    p.to_parquet(C.PROCESSED / "panel.parquet", index=False)

    print(f"panel rows {len(p):,}, firms {p.gvkey.nunique():,}; volatility months dropped by split check: "
          f"{int(p.vol_flagged.sum()):,} ({p.vol_flagged.mean():.2%})")
    need = ["ret", "sd", "tmean_anom_hq", "tmean_anom_ex", "ppt_anom_z_hq", "SP500"]
    print("non-missing share:\n" + p[need].notna().mean().round(3).to_string())
    print(f"HQ climate differs between name-only and city+state match: "
          f"{(p.T_mean_legacy_hq_nameonly.round(6) != p.T_mean_legacy_hq.round(6)).mean():.1%} of firm-months")


if __name__ == "__main__":
    main()
