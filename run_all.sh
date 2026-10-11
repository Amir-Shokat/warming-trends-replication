#!/usr/bin/env bash
# Rebuild everything from the raw downloads in data/raw (or $THESIS_RAW_DATA).
# Total runtime ~30 min on an 8 GB laptop; disk use ~0.4 GB.
set -euo pipefail
cd "$(dirname "$0")/code"
python3 -W ignore 01_firms.py
python3 -W ignore 02_climate.py
python3 -W ignore 03_volatility.py
python3 -W ignore 04_panel.py
python3 -W ignore 05_validate_rebuild.py
python3 -W ignore -u 06_regressions.py | tee ../output/logs/06_regressions.log
python3 -W ignore -u 07_robustness.py | tee ../output/logs/07_robustness.log
python3 -W ignore 08_latex_tables.py
python3 -W ignore 09_figures.py
