"""Minimal high-dimensional fixed-effects OLS with one-/two-way clustered SEs.

Fixed effects are absorbed by alternating projections (demean by each FE in
turn until convergence). Clustered covariance follows Cameron, Gelbach & Miller
(2011): V = V_a + V_b - V_ab, without small-sample corrections, which matches
linearmodels PanelOLS(cov_type='clustered', cluster_entity=True, cluster_time=True)
as used in the thesis. 05/06 scripts verify it reproduces the thesis tables.
"""
import numpy as np
import pandas as pd


def _demean(M, codes, tol=1e-9, maxit=500):
    M = M.copy()
    counts = [np.bincount(c) for c in codes]
    for _ in range(maxit):
        delta = 0.0
        for c, n in zip(codes, counts):
            for j in range(M.shape[1]):
                means = np.bincount(c, weights=M[:, j]) / n
                adj = means[c]
                M[:, j] -= adj
                delta = max(delta, np.abs(adj).max())
        if delta < tol:
            break
    return M


def _meat(X, u, g):
    codes = pd.factorize(g)[0]
    S = np.zeros((codes.max() + 1, X.shape[1]))
    np.add.at(S, codes, X * u[:, None])
    return S.T @ S


def feols(df, y, xs, fe, cluster):
    """df: DataFrame; y: str; xs: list[str]; fe: list[str]; cluster: list[str] (1 or 2)."""
    cols = list(dict.fromkeys([y] + xs + fe + cluster))  # FE and cluster may share a column
    d = df[cols].dropna()
    codes = [pd.factorize(d[f])[0] for f in fe]
    M = _demean(d[[y] + xs].to_numpy(float), codes)
    Y, X = M[:, 0], M[:, 1:]
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ Y
    u = Y - X @ b
    if len(cluster) == 1:
        meat = _meat(X, u, d[cluster[0]].to_numpy())
    else:
        a, c = d[cluster[0]].to_numpy(), d[cluster[1]].to_numpy()
        inter = pd.factorize(pd.Series(a).astype(str) + "|" + pd.Series(c).astype(str))[0]
        meat = _meat(X, u, a) + _meat(X, u, c) - _meat(X, u, inter)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(V))
    r2_within = 1 - (u @ u) / ((Y - Y.mean()) @ (Y - Y.mean()))
    return pd.DataFrame({"coef": b, "se": se, "t": b / se}, index=xs).assign(
        n=len(d), firms=d[cluster[0]].nunique() if cluster else np.nan, r2_within=r2_within)
