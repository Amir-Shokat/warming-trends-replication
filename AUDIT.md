# Audit of the original thesis code and data (`raw_project/`)

Date: 2026-10-10. The original folder was read, never modified.

## 1. What is in `raw_project/` (28 GB, 1,216 files)

| Part | Size | What it is |
|---|---|---|
| `papers/` | 169 MB | literature PDFs (not code/data) |
| Root `.docx`/`.pdf`/`.bib` | ~3 MB | thesis drafts, pitch, references |
| **Raw downloads** (keep) | ~12 GB | Compustat `daily1-3.csv`, `last.csv`, `state.csv`, `monthly price.csv`, `GISC.csv`; PRISM folders (`Climate Data/1965 - 1979` … `2010 - 2024`, `min - max/`, `daily/`, `Annually/`, `temp-*`); `uscities.csv` |
| **Intermediate CSVs** (regenerable) | ~16 GB | e.g. `data_lag.csv`, `very new data*.csv`, `Data.csv`, `Data_very newwwwwwwwww.csv`, `data-new.csv`, `Dataframe-new.csv`, `FINAL DATAFRAME.csv`, `Panel - *.csv`, `stata.dta`, `combined_results.csv`, `daily_*.csv`, `monthly_sd_*.csv` … |
| Notebooks | 43 `.ipynb` | 14 named `Untitled*`; several are tutorials/scratch |

`Climate Data/log-return.csv` is the file every thesis table was estimated on. **No notebook
creates it** (nor `Data.csv`): those steps only existed in notebook memory. The new pipeline
rebuilds it from the raw downloads and was checked against it (§3).

### Notebook map (old → new)

| Old notebook(s) | Purpose | New script |
|---|---|---|
| `monthly return - data cleaning`, `Niacs-calssification`, `US-Cities`, `main_df` | firm sample, exchanges, cities, heat-sensitive dummy | `01_firms.py` |
| `temp-1995-2009/*`, `Read climate data`, `Making time series`, `min - max/*` | PRISM loading and anomalies | `02_climate.py` |
| `s.d_Data Cleaning`, `sd_monthly` | daily volatility | `03_volatility.py` |
| `panel without controls`, `attach SP500 and VIX`, `log return - new`, `Add Warmer dummy`, `Untitled4` (lags), `Year - state` | merging, controls, lags | `04_panel.py` |
| `main regressions`, `Heat-sensitive`, `lagged regression`, `Warmer Regression`, `Quarter Industry` | Tables 2–4, A1–A6 | `06_regressions.py` (Tables 2–3 + corrected; others to port) |
| `Untitled*`, `TEST for paper`, `temperature`, `geocode`, `Regression - Casper`, `regression - first draft`, `Data`, `adding the GICS industry codes`, `To Stata` | scratch, tutorials, abandoned versions | not needed |

## 2. Problems found (with evidence)

Severity: **A** = changes results / invalidates a claim; **B** = should fix; **C** = cosmetic.

| # | Sev | Problem | Where | Evidence | Fix in new pipeline |
|---|---|---|---|---|---|
| 1 | A | **Max/min "anomalies" measured against the *mean*-temperature baseline** | `min - max/Max and min calc.ipynb` cell 8: `(final_df - mean).abs()` with `mean = combined_results.csv` (MA of tmean) | Rebuilt with this formula matches thesis `Max_Ex`/`Min_Ex` 99.9%; values average 11°F / 10°F (≈ half the daily temperature range) vs ≈0.2°F for true anomalies | `tmax_anom`, `tmin_anom` vs PRISM 1991–2020 normals of tmax/tmin |
| 2 | A | **HQ weather matched on city name only**; 1 in 3 US city names is shared (Portland OR/ME, ~30 Springfields) | `panel without controls` melt/merge on `City`; PRISM pivot `aggfunc='first'` | Thesis HQ temperature equals the correct (city, state) location in only **55.5%** of firm-months; **7,294 of 16,883 firms** got another town's weather | match on (city, state) using `state.csv` |
| 3 | A | Foreign/non-US HQs kept because a US town shares the name (e.g. London, ON) | `Niacs-calssification`, `monthly return - data cleaning` (city-name filter) | 6.7% of thesis firm-months have no (city, state) match in the continental US | sample filter `hq_in_conus` |
| 4 | A | **Absolute value discards the sign** of anomalies; thesis then interprets signs ("cold shocks reduce volatility") | `.abs()` in every anomaly cell | by construction | signed `tmean_anom`, `hot`/`cold` split |
| 5 | A | Exchange temperature is one time series: 99.94% of observations list in "New York" (NASDAQ=14 and OTC=13 mapped to NY; Chicago 164 obs) | `monthly return - data cleaning` cell 24 | `log-return.csv`: NY 1,961,853 / Phil. 990 / Chicago 164 | channel not estimable with month FE; documented, not estimated |
| 6 | A | **Daily returns computed across firm boundaries** (`shift(1)` on the whole file) and from **unadjusted** prices | `sd_monthly` cell 0 | thesis SD max = 12.36 (1,236% daily); rebuilt legacy SD matches thesis 100% | within firm & share class; split-like days (|r|>0.5) dropped; ≥15 days |
| 7 | A | Monthly `log_return` from **unadjusted** `prccm`, grouped by firm only (share classes interleaved) | `log return - new` cell 3 | thesis `log_return` min −12.9, max +10.7 | use `trt1m` (Compustat adjusted total return) |
| 8 | B | Baseline includes the current year (rolling window ends at t) | `Making time series` cell 18 | — | trailing window ends at t−1 |
| 9 | B | No seasonal / market-wide control beyond industry×year FE; SP500/VIX identified only within year | regressions | — | industry × year-month FE |
| 10 | B | `ppt_City`/`ppt_Ex` are temperature **levels**, not precipitation ("Add pure precipitation" reads the temperature file) | `Max and min calc` cells 17-19 | mean 57, range −7 to 99 | not used; main tables used `Pre_City`/`pre_EX` (correct) |
| 11 | B | Multiple share classes per firm (incl. Canadian `01C` listings) mixed | all Compustat steps drop `iid` | `iid` values 01, 01C, 02, 90 … | primary US class kept |
| 12 | B | Industry×year FE use **6-digit** NAICS (thesis text implies sector) | `Year_Industry` = year + full NAICS | `1995_423860.0` | kept 6-digit, now documented |
| 13 | B | HQ location is today's HQ applied back to 1995 | Compustat header `city`, `state` constant per firm | 0 firms change city/state | not fixable without historical HQ data; disclose |
| 14 | C | Utilities listed as NAICS 21 in thesis text | thesis §3, Table 4 note | code correctly uses 22 | text fix only |
| 15 | C | Hard-coded paths `/Users/.../Desktop/Study/Thesis/...`; duplicated/overwritten files (`combined_results.csv` from annual then monthly data) | many notebooks | — | single `config.py` |

## 3. Validation of the rebuild

`05_validate_rebuild.py` → `output/logs/validation.txt`. Rebuilt legacy columns vs thesis
`log-return.csv` (1,963,007 rows, 100% found):

* Exchange-city `Temp/Max/Min/pre_EX`: 99.9–100% identical → anomaly formula (incl. bug #1) reproduced.
* `SD`, `Return`, `Heat_sensitive`, `Different_cities`: 100% identical.
* HQ climate: differs for ~22–45% of rows only because of the arbitrary same-name town choice (bug #2).
* `fe.py` reproduces thesis coefficients exactly (e.g. Table 2 c1 9.83e-05; Table 3 c3 −0.00112);
  t-statistics within ≈1.5% (linearmodels small-sample factor).

## 4. Still open / needs you

* **Adjusted daily prices**: download `prccd`, `ajexdi`, `trfd` from WRDS (if you still have
  access) to replace the split-day filter (#6) with proper adjustment.
* ~~Port robustness tables~~ done: `07_robustness.py` -> `output/tables/robustness_results.md`
  (lag, warmer locations, thesis-style FE, 2-digit industry FE, fixed 1991-2020 baseline; all null).
* Disk: intermediate CSVs (~16 GB) are regenerable and could be archived/deleted **after** you
  confirm — nothing has been deleted.
