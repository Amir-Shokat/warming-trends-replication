"""Step 8 - Write LaTeX tables for the revised thesis from the regression CSVs.

Output: output/tables/tab_summary.tex, tab_main.tex, tab_heat.tex, tab_robust.tex
All coefficients are multiplied by 10,000 (basis points per degree F for returns).
"""
import pandas as pd
import config as C

LABEL = {"tmean_anom_hq": "Mean anomaly", "hot_hq": "Hot", "cold_hq": "Cold",
         "tmax_anom_hq": "Max anomaly", "tmin_anom_hq": "Min anomaly",
         "tmean_absanom_hq": "$|$Mean anomaly$|$", "hot_x_hs": "Hot $\\times$ Heat sensitive",
         "cold_x_hs": "Cold $\\times$ Heat sensitive", "tmean_anom_hq_lag3": "Mean anomaly ($t-3$)",
         "hot_hq_lag3": "Hot ($t-3$)", "cold_hq_lag3": "Cold ($t-3$)",
         "hot_x_warm": "Hot $\\times$ Warmer", "cold_x_warm": "Cold $\\times$ Warmer",
         "tmean_anom_norm_hq": "Mean anomaly (1991--2020 normal)"}


def star(p):
    return "^{***}" if p < .01 else "^{**}" if p < .05 else "^{*}" if p < .1 else ""


def cell(r):
    return f"${r.coef*1e4:.2f}{star(r.p)}$", f"$({r.t:.2f})$"


def grid(res, cols, rows):
    """cols: list of (y, spec); rows: variable names in order."""
    lines = []
    for v in rows:
        a, b = [LABEL[v]], [""]
        for y, spec in cols:
            hit = res[(res.y == y) & (res.spec == spec) & (res.variable == v)]
            if len(hit):
                c1, c2 = cell(hit.iloc[0]); a.append(c1); b.append(c2)
            else:
                a.append(""); b.append("")
        lines += [" & ".join(a) + r" \\", " & ".join(b) + r" \\"]
    n = []
    for y, spec in cols:
        hit = res[(res.y == y) & (res.spec == spec)]
        n.append(f"{int(hit.n.iloc[0]):,}")
    lines += [r"\midrule", "Observations & " + " & ".join(n) + r" \\"]
    return "\n".join(lines)


def main():
    res = pd.read_csv(C.TABLES / "corrected_results.csv")
    specs = ["signed mean anomaly", "hot / cold split", "tmax / tmin anomalies",
             "|mean anomaly| (thesis concept, fixed)"]
    cols = [("ret_w", s) for s in specs] + [("sd_w", s) for s in specs]
    rows = ["tmean_anom_hq", "hot_hq", "cold_hq", "tmax_anom_hq", "tmin_anom_hq", "tmean_absanom_hq"]
    body = grid(res, cols, rows)
    (C.TABLES / "tab_main.tex").write_text(
        r"\begin{tabular}{@{}lcccccccc@{}}" "\n" r"\toprule" "\n"
        r" & \multicolumn{4}{c}{A. Return} & \multicolumn{4}{c}{B. Volatility} \\" "\n"
        r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}" "\n"
        r" & (1) & (2) & (3) & (4) & (5) & (6) & (7) & (8) \\" "\n" r"\midrule" "\n"
        + body + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")

    hs = [("ret_w", "hot / cold x heat-sensitive"), ("sd_w", "hot / cold x heat-sensitive")]
    body = grid(res, hs, ["hot_hq", "cold_hq", "hot_x_hs", "cold_x_hs"])
    (C.TABLES / "tab_heat.tex").write_text(
        r"\begin{tabular}{@{}lcc@{}}" "\n" r"\toprule" "\n"
        r" & (1) Return & (2) Volatility \\" "\n" r"\midrule" "\n" + body + "\n"
        r"\bottomrule" "\n" r"\end{tabular}" "\n")

    rob = pd.read_csv(C.TABLES / "robustness_results.csv")
    names = {"lag": "One-quarter lag", "warmer": "Warmer locations", "thesis_fe": "Industry $\\times$ year FE + market control",
             "coarse_ind": "2-digit industry $\\times$ month FE", "fixed_normal": "Fixed 1991--2020 baseline"}
    lines = []
    for chk, g in rob.groupby("check", sort=False):
        first = True
        for spec, gg in g.groupby("spec", sort=False):
            for v in gg.variable.unique():
                r = gg[(gg.variable == v) & (gg.y == "ret_w")].iloc[0]
                s = gg[(gg.variable == v) & (gg.y == "sd_w")].iloc[0]
                a1, a2 = cell(r); b1, b2 = cell(s)
                lines.append(f"{names[chk] if first else ''} & {LABEL[v]} & {a1} & {a2} & {b1} & {b2} \\\\")
                first = False
        lines.append(r"\addlinespace")
    (C.TABLES / "tab_robust.tex").write_text(
        r"\begin{tabular}{@{}llcccc@{}}" "\n" r"\toprule" "\n"
        r" & & \multicolumn{2}{c}{Return} & \multicolumn{2}{c}{Volatility} \\" "\n"
        r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}" "\n"
        r"Check & Variable & coef. & $t$ & coef. & $t$ \\" "\n" r"\midrule" "\n"
        + "\n".join(lines) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")

    p = pd.read_parquet(C.PROCESSED / "panel.parquet")
    p = p[p.hq_in_conus].dropna(subset=["ret_w", "tmean_anom_hq", "ppt_anom_z_hq"])
    vars_ = [("ret_w", "Monthly log return"), ("sd_w", "Monthly volatility"),
             ("tmean_anom_hq", "Mean anomaly (\\textdegree F)"), ("hot_hq", "Hot (\\textdegree F)"),
             ("cold_hq", "Cold (\\textdegree F)"), ("tmax_anom_hq", "Max anomaly (\\textdegree F)"),
             ("tmin_anom_hq", "Min anomaly (\\textdegree F)"), ("ppt_anom_z_hq", "Precipitation anomaly (z)"),
             ("heat_sensitive", "Heat sensitive"), ("different_city", "Different city")]
    d = p[[v for v, _ in vars_]].describe(percentiles=[.25, .5, .75]).T
    lines = [f"{lab} & {d.loc[v,'mean']:.3f} & {d.loc[v,'25%']:.3f} & {d.loc[v,'50%']:.3f} & "
             f"{d.loc[v,'75%']:.3f} & {d.loc[v,'std']:.3f} \\\\" for v, lab in vars_]
    (C.TABLES / "tab_summary.tex").write_text(
        r"\begin{tabular}{@{}lccccc@{}}" "\n" r"\toprule" "\n"
        r" & Mean & 25th pct. & Median & 75th pct. & SD \\" "\n" r"\midrule" "\n"
        + "\n".join(lines) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")
    print("tables written; firms", p.gvkey.nunique(), "cities", p[['city','state']].drop_duplicates().shape[0])


if __name__ == "__main__":
    main()
