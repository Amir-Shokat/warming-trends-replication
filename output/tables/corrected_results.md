Coefficients x 10,000 (returns: basis points per degree F; volatility: x1e-4 per degree F).
FE: firm + 6-digit NAICS x year-month. SE: two-way clustered (firm, month). q = Benjamini-Hochberg adjusted p across all rows.

| outcome | spec | variable | coef | t | 95% CI | per 1 SD | q (BH) | N |
|---|---|---|---|---|---|---|---|---|
| ret_w | signed mean anomaly | tmean_anom_hq | -0.94 | -1.22 | [-2.45, 0.57] | -2.84 | 1.00 | 1,864,629 |
| ret_w | hot / cold split | hot_hq | -1.48 | -1.22 | [-3.84, 0.89] | -2.97 | 1.00 | 1,864,629 |
| ret_w | hot / cold split | cold_hq | 0.22 | 0.14 | [-2.72, 3.15] | 0.34 | 0.93 | 1,864,629 |
| ret_w | tmax / tmin anomalies | tmax_anom_hq | -1.25 | -1.35 | [-3.06, 0.57] | -4.10 | 1.00 | 1,864,629 |
| ret_w | tmax / tmin anomalies | tmin_anom_hq | 0.65 | 0.67 | [-1.24, 2.53] | 1.96 | 1.00 | 1,864,629 |
| ret_w | |mean anomaly| (thesis concept, fixed) | tmean_absanom_hq | -0.90 | -0.83 | [-3.02, 1.22] | -1.81 | 1.00 | 1,864,629 |
| ret_w | hot / cold x heat-sensitive | hot_hq | -1.19 | -0.93 | [-3.70, 1.31] | -2.40 | 1.00 | 1,864,629 |
| ret_w | hot / cold x heat-sensitive | cold_hq | -0.27 | -0.19 | [-3.03, 2.49] | -0.43 | 1.00 | 1,864,629 |
| ret_w | hot / cold x heat-sensitive | hot_x_hs | -0.80 | -0.42 | [-4.55, 2.95] | -1.11 | 0.97 | 1,864,629 |
| ret_w | hot / cold x heat-sensitive | cold_x_hs | 1.45 | 0.60 | [-3.26, 6.17] | 1.50 | 1.00 | 1,864,629 |
| sd_w | signed mean anomaly | tmean_anom_hq | -0.06 | -0.65 | [-0.22, 0.11] | -0.17 | 1.00 | 1,772,757 |
| sd_w | hot / cold split | hot_hq | -0.05 | -0.38 | [-0.28, 0.19] | -0.09 | 0.94 | 1,772,757 |
| sd_w | hot / cold split | cold_hq | 0.07 | 0.45 | [-0.23, 0.36] | 0.11 | 1.00 | 1,772,757 |
| sd_w | tmax / tmin anomalies | tmax_anom_hq | 0.07 | 0.67 | [-0.14, 0.28] | 0.23 | 1.00 | 1,772,757 |
| sd_w | tmax / tmin anomalies | tmin_anom_hq | -0.13 | -1.09 | [-0.36, 0.10] | -0.39 | 1.00 | 1,772,757 |
| sd_w | |mean anomaly| (thesis concept, fixed) | tmean_absanom_hq | -0.01 | -0.07 | [-0.21, 0.19] | -0.01 | 0.94 | 1,772,757 |
| sd_w | hot / cold x heat-sensitive | hot_hq | -0.07 | -0.53 | [-0.32, 0.18] | -0.14 | 0.99 | 1,772,757 |
| sd_w | hot / cold x heat-sensitive | cold_hq | 0.08 | 0.56 | [-0.20, 0.36] | 0.13 | 1.00 | 1,772,757 |
| sd_w | hot / cold x heat-sensitive | hot_x_hs | 0.06 | 0.31 | [-0.34, 0.47] | 0.09 | 0.94 | 1,772,757 |
| sd_w | hot / cold x heat-sensitive | cold_x_hs | -0.04 | -0.15 | [-0.53, 0.45] | -0.04 | 0.97 | 1,772,757 |
