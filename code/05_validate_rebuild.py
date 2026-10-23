"""Step 5 - Check the rebuild against the thesis's final regression file (log-return.csv).

If the legacy columns rebuilt here match the thesis's columns, the pipeline is a
faithful reconstruction, and the corrected columns can be trusted to differ only
by the documented fixes. Writes output/logs/validation.txt.
"""
import numpy as np
import pandas as pd
import config as C

PAIRS = [  # (thesis column, rebuilt legacy column)
    ("Temp_City", "T_mean_legacy_hq_nameonly"), ("Max_City", "T_max_legacy_hq_nameonly"),
    ("Min_City", "T_min_legacy_hq_nameonly"), ("Pre_City", "P_legacy_hq_nameonly"),
    ("Temp_EX", "T_mean_legacy_ex"), ("Max_Ex", "T_max_legacy_ex"), ("Min_Ex", "T_min_legacy_ex"),
    ("pre_EX", "P_legacy_ex"), ("SD", "sd_legacy"), ("Return", "trt1m"),
    ("Heat_sensitive", "heat_sensitive"), ("Different_cities", "different_city_legacy"),
]


def main():
    cols = ["gvkey", "Date"] + [a for a, _ in PAIRS] + ["log_return", "City"]
    t = pd.read_csv(C.LEGACY_FINAL, usecols=cols)
    t["gvkey"] = t.gvkey.astype(str).str.zfill(6)
    t["month"] = pd.to_datetime(t.Date)
    p = pd.read_parquet(C.PROCESSED / "panel.parquet")
    m = t.merge(p, on=["gvkey", "month"], how="left", indicator=True)

    lines = [f"thesis rows: {len(t):,}  firms: {t.gvkey.nunique():,}",
             f"found in rebuilt panel: {(m._merge == 'both').mean():.2%}", "",
             f"{'thesis column':<18}{'rebuilt column':<28}{'match(|d|<0.01)':>16}{'corr':>8}{'n':>11}"]
    m = m[m._merge == "both"]
    for a, b in PAIRS:
        ok = m[[a, b]].dropna()
        match = (np.isclose(ok[a], ok[b], atol=0.01)).mean()
        corr = ok[a].corr(ok[b]) if ok[b].std() > 0 else np.nan
        lines.append(f"{a:<18}{b:<28}{match:>16.3f}{corr:>8.3f}{len(ok):>11,}")

    lines += ["", "How often does the city-name-only climate match the city+state climate?"]
    both = m[["T_mean_legacy_hq_nameonly", "T_mean_legacy_hq"]].dropna()
    same = np.isclose(both.iloc[:, 0], both.iloc[:, 1], atol=1e-6).mean()
    lines.append(f"  same location: {same:.1%} of {len(both):,} firm-months "
                 f"-> {1-same:.1%} got another place's weather")
    lines.append(f"  no city+state match at all (e.g. foreign HQ matched to a US name): "
                 f"{m.T_mean_legacy_hq.isna().mean():.1%}")
    out = "\n".join(lines)
    print(out)
    (C.LOGS / "validation.txt").write_text(out + "\n")


def wrong_town_check():
    """Direct test on the thesis's own HQ values: equal to the correct (city, state) location?"""
    t = pd.read_csv(C.LEGACY_FINAL, usecols=["gvkey", "Date", "Temp_City"])
    t["gvkey"] = t.gvkey.astype(str).str.zfill(6)
    t["month"] = pd.to_datetime(t.Date)
    p = pd.read_parquet(C.PROCESSED / "panel.parquet", columns=["gvkey", "month", "T_mean_legacy_hq"])
    m = t.merge(p, on=["gvkey", "month"]).dropna()
    ok = np.isclose(m.Temp_City, m.T_mean_legacy_hq, atol=0.01)
    firm_ok = pd.Series(ok).groupby(m.gvkey.values).mean()
    out = (f"\nThesis HQ temperature equals the correct (city, state) location in {ok.mean():.1%} of "
           f"{len(m):,} firm-months; firms entirely on a wrong town: {(firm_ok < 0.5).sum():,} of {len(firm_ok):,}")
    print(out)
    with open(C.LOGS / "validation.txt", "a") as fh:
        fh.write(out + "\n")


if __name__ == "__main__":
    if not C.LEGACY_FINAL.exists():
        print(f"skipping validation: {C.LEGACY_FINAL.name} (the thesis's final data file) not found; "
              "output/logs/validation.txt keeps the result from the original run")
    else:
        main()
        wrong_town_check()
