"""Step 6 - Regressions: (A) replicate thesis Tables 2-3 from the thesis data file,
(B) corrected specification on the rebuilt panel.

Corrected specification (pre-specified, small set of tests):
  y_it = b * climate_it + c * precip_z_it + firm FE + industry(6-digit NAICS) x year-month FE + e_it
  y = winsorized monthly log return (from trt1m) or winsorized monthly volatility (SD of daily returns)
  SEs two-way clustered by firm and month.
  Industry x year-month FE absorb all market-wide shocks (so SP500/VIX are not needed) and
  seasonality; identification comes only from firms in different places in the same month.
  The exchange-city channel is NOT estimable: 99.9% of firms list in New York, so exchange
  temperature is a pure time series and is absorbed by the year-month FE.
Sample: firms whose HQ (city, state) is in the continental US.

Outputs: output/tables/replication_thesis.csv, corrected_results.csv, corrected_results.md
"""
import numpy as np
import pandas as pd
import config as C
from fe import feols

CLIM = {  # spec name -> climate regressors (HQ)
    "signed mean anomaly": ["tmean_anom_hq"],
    "hot / cold split": ["hot_hq", "cold_hq"],
    "tmax / tmin anomalies": ["tmax_anom_hq", "tmin_anom_hq"],
    "|mean anomaly| (thesis concept, fixed)": ["tmean_absanom_hq"],
    "hot / cold x heat-sensitive": ["hot_hq", "cold_hq", "hot_x_hs", "cold_x_hs"],
}


def replication():
    t = pd.read_csv(C.LEGACY_FINAL)
    rows = []
    specs = [("Table2 c%d" % i, "log_return", [x, p, "SP500"]) for i, (x, p) in enumerate(
        [("Temp_City", "Pre_City"), ("Max_City", "Pre_City"), ("Min_City", "Pre_City"),
         ("Temp_EX", "pre_EX"), ("Max_Ex", "pre_EX"), ("Min_Ex", "pre_EX")], 1)]
    specs += [("Table3 c%d" % i, "SD", [x, p, "VIX"]) for i, (x, p) in enumerate(
        [("Temp_City", "Pre_City"), ("Max_City", "Pre_City"), ("Min_City", "Pre_City"),
         ("Temp_EX", "pre_EX"), ("Max_Ex", "pre_EX"), ("Min_Ex", "pre_EX")], 1)]
    for name, y, xs in specs:
        r = feols(t, y, xs, ["gvkey", "Year_Industry"], ["gvkey", "Date"])
        rows.append(r.iloc[[0]].assign(table=name, y=y))
        print(name, xs[0], r.iloc[0][["coef", "t"]].round(5).tolist(), flush=True)
    pd.concat(rows).to_csv(C.TABLES / "replication_thesis.csv")


def corrected():
    p = pd.read_parquet(C.PROCESSED / "panel.parquet")
    p = p[p.hq_in_conus]
    p["ind_ym"] = p.naics.astype(str) + "_" + p.month.dt.strftime("%Y-%m")
    p["hot_x_hs"] = p.hot_hq * p.heat_sensitive
    p["cold_x_hs"] = p.cold_hq * p.heat_sensitive
    rows = []
    for y in ["ret_w", "sd_w"]:
        for name, xs in CLIM.items():
            r = feols(p, y, xs + ["ppt_anom_z_hq"], ["gvkey", "ind_ym"], ["gvkey", "month"])
            r = r.drop(index="ppt_anom_z_hq").assign(y=y, spec=name)
            sd_x = p[xs].std()
            r["effect_per_1sd"] = r.coef * sd_x.reindex(r.index).values
            r["ci95_lo"], r["ci95_hi"] = r.coef - 1.96 * r.se, r.coef + 1.96 * r.se
            rows.append(r)
            print(y, name, r[["coef", "t"]].round(5).to_dict("index"), flush=True)
    res = pd.concat(rows).rename_axis("variable").reset_index()

    # Benjamini-Hochberg across all temperature coefficients (two-sided normal p-values)
    from math import erf, sqrt
    res["p"] = [2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2)))) for t in res.t]
    order = res.p.rank(method="first")
    m = len(res)
    q = (res.p * m / order).sort_values(ascending=False).cummin()
    res["q_bh"] = q.reindex(res.index).clip(upper=1)
    res.to_csv(C.TABLES / "corrected_results.csv", index=False)

    def fmt(r):
        unit = "bp" if r.y == "ret_w" else "x1e4"
        star = "***" if r.p < .01 else "**" if r.p < .05 else "*" if r.p < .1 else ""
        return (f"| {r.y} | {r.spec} | {r.variable} | {r.coef*1e4:.2f}{star} | {r.t:.2f} | "
                f"[{r.ci95_lo*1e4:.2f}, {r.ci95_hi*1e4:.2f}] | {r.effect_per_1sd*1e4:.2f} | {r.q_bh:.2f} | {int(r.n):,} |")
    md = ["Coefficients x 10,000 (returns: basis points per degree F; volatility: x1e-4 per degree F).",
          "FE: firm + 6-digit NAICS x year-month. SE: two-way clustered (firm, month). "
          "q = Benjamini-Hochberg adjusted p across all rows.", "",
          "| outcome | spec | variable | coef | t | 95% CI | per 1 SD | q (BH) | N |",
          "|---|---|---|---|---|---|---|---|---|"] + [fmt(r) for r in res.itertuples()]
    (C.TABLES / "corrected_results.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    import sys
    if "--skip-replication" not in sys.argv:
        replication()
    corrected()
