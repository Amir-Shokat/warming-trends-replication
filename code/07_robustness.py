"""Step 7 - Robustness checks (corrected versions of thesis Tables A1-A6).

Baseline: corrected spec of 06_regressions.py (firm FE + 6-digit NAICS x year-month FE,
two-way clustered SEs, HQ in continental US). Each check changes one thing:

  lag          : add one-quarter (3-month) lagged anomaly             (thesis Tables A1-A2)
  warmer       : interact hot/cold with a warmer-location dummy        (thesis Tables A3-A4)
                 warmer = location's 1995-2024 mean tmean above the median location
  thesis_fe    : firm + industry x YEAR FE with SP500 / VIX control    (thesis's FE choice;
                 replaces thesis Tables A5-A6 quarter-industry check, now nested in baseline)
  coarse_ind   : 2-digit NAICS x year-month FE
  fixed_normal : anomaly vs fixed PRISM 1991-2020 normal instead of trailing 30-year mean

Output: output/tables/robustness_results.csv, robustness_results.md
"""
from math import erf, sqrt
import numpy as np
import pandas as pd
import config as C
from fe import feols


def load():
    p = pd.read_parquet(C.PROCESSED / "panel.parquet")
    p = p[p.hq_in_conus].sort_values(["gvkey", "month"]).copy()
    p["ind_ym"] = p.naics.astype(str) + "_" + p.month.dt.strftime("%Y-%m")
    p["ind_y"] = p.naics.astype(str) + "_" + p.year.astype(str)
    p["ind2_ym"] = p.naics2.astype(str) + "_" + p.month.dt.strftime("%Y-%m")

    # one-quarter lag within firm, only if the firm-month 3 months earlier exists
    g = p.groupby("gvkey")
    for v in ["tmean_anom_hq", "hot_hq", "cold_hq"]:
        lag = g[v].shift(3)
        gap = (p.month - g.month.shift(3)).dt.days
        p[v + "_lag3"] = lag.where(gap.between(85, 95))

    # warmer locations
    c = pd.read_parquet(C.PROCESSED / "climate_monthly.parquet", columns=["city", "state", "tmean"])
    lm = c.groupby(["city", "state"]).tmean.mean()
    warm = (lm > lm.median()).astype("int8").rename("warmer").reset_index()
    p = p.merge(warm, on=["city", "state"], how="left")
    p["hot_x_warm"] = p.hot_hq * p.warmer
    p["cold_x_warm"] = p.cold_hq * p.warmer
    return p


def main():
    p = load()
    base_fe = ["gvkey", "ind_ym"]
    cl = ["gvkey", "month"]
    ppt = ["ppt_anom_z_hq"]
    specs = [  # (check, regressors, extra controls by outcome, FE)
        ("lag", ["tmean_anom_hq", "tmean_anom_hq_lag3"], {}, base_fe),
        ("lag", ["hot_hq", "cold_hq", "hot_hq_lag3", "cold_hq_lag3"], {}, base_fe),
        ("warmer", ["hot_hq", "cold_hq", "hot_x_warm", "cold_x_warm"], {}, base_fe),
        ("thesis_fe", ["tmean_anom_hq"], {"ret_w": ["SP500"], "sd_w": ["VIX"]}, ["gvkey", "ind_y"]),
        ("thesis_fe", ["hot_hq", "cold_hq"], {"ret_w": ["SP500"], "sd_w": ["VIX"]}, ["gvkey", "ind_y"]),
        ("coarse_ind", ["tmean_anom_hq"], {}, ["gvkey", "ind2_ym"]),
        ("fixed_normal", ["tmean_anom_norm_hq"], {}, base_fe),
    ]
    rows = []
    for y in ["ret_w", "sd_w"]:
        for check, xs, extra, fe in specs:
            r = feols(p, y, xs + ppt + extra.get(y, []), fe, cl).loc[xs]
            r = r.assign(y=y, check=check, spec=" + ".join(xs))
            rows.append(r)
            print(y, check, r[["coef", "t"]].round(5).to_dict("index"), flush=True)
    res = pd.concat(rows).rename_axis("variable").reset_index()
    res["p"] = [2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2)))) for t in res.t]
    order = res.p.rank(method="first")
    res["q_bh"] = (res.p * len(res) / order).sort_values(ascending=False).cummin().reindex(res.index).clip(upper=1)
    res.to_csv(C.TABLES / "robustness_results.csv", index=False)

    def fmt(r):
        star = "***" if r.p < .01 else "**" if r.p < .05 else "*" if r.p < .1 else ""
        return (f"| {r.y} | {r.check} | {r.variable} | {r.coef*1e4:.2f}{star} | {r.t:.2f} | "
                f"[{(r.coef-1.96*r.se)*1e4:.2f}, {(r.coef+1.96*r.se)*1e4:.2f}] | {r.q_bh:.2f} | {int(r.n):,} |")
    md = ["Coefficients x 10,000 per degree F. q = Benjamini-Hochberg adjusted p across all rows of this table.", "",
          "| outcome | check | variable | coef | t | 95% CI | q (BH) | N |", "|---|---|---|---|---|---|---|---|"]
    (C.TABLES / "robustness_results.md").write_text("\n".join(md + [fmt(r) for r in res.itertuples()]) + "\n")


if __name__ == "__main__":
    main()
