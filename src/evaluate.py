"""
Regression and evaluation.

Two regressions are run and they answer different questions.

Contemporaneous   d_mid_k ~ ofi_k
                  This is the CKS replication. It asks how much of the mid
                  move inside a bucket is explained by the order flow inside
                  the same bucket. R^2 is usually high. It is NOT a trading
                  signal, because by the time you have measured ofi_k the
                  move has already happened.

Predictive        d_mid_{k+1} ~ ofi_k
                  This is the question a trader actually cares about. R^2 here
                  is small, often close to zero. Reporting the contemporaneous
                  number as though it were predictive is the standard way these
                  projects get taken apart in an interview.

OLS is done by hand rather than through statsmodels so every number is
traceable. Standard errors are White HC0, since bucketed order flow data is
strongly heteroskedastic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Fit:
    label: str
    alpha: float
    beta: float
    se_beta: float
    t_beta: float
    r2_in: float
    r2_out: float
    n_train: int
    n_test: int

    def __str__(self) -> str:
        return (
            f"{self.label:<18} beta={self.beta:+.4f} (se {self.se_beta:.4f}, "
            f"t {self.t_beta:+.1f})  R2 in {self.r2_in:.4f}  "
            f"out {self.r2_out:.4f}  n {self.n_train}/{self.n_test}"
        )


def _ols_hc0(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coefficients and White HC0 standard errors. X must include a constant."""
    XtX_inv = np.linalg.inv(X.T @ X)
    coef = XtX_inv @ X.T @ y
    resid = y - X @ coef
    meat = X.T @ np.diag(resid**2) @ X
    cov = XtX_inv @ meat @ XtX_inv
    return coef, np.sqrt(np.diag(cov))


def _r2(y: np.ndarray, y_hat: np.ndarray) -> float:
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan


def fit_split(
    x: pd.Series,
    y: pd.Series,
    label: str,
    train_frac: float = 0.7,
) -> Fit:
    """
    Time-ordered split. No shuffling, no k-fold. Out-of-sample R^2 applies the
    train-fitted coefficients to the test block and measures against the test
    mean, so a useless model scores at or below zero rather than near zero.
    """
    frame = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    n = len(frame)
    if n < 100:
        raise ValueError(f"only {n} usable buckets, need at least 100")

    cut = int(n * train_frac)
    tr, te = frame.iloc[:cut], frame.iloc[cut:]

    X_tr = np.column_stack([np.ones(len(tr)), tr["x"].to_numpy()])
    X_te = np.column_stack([np.ones(len(te)), te["x"].to_numpy()])
    y_tr, y_te = tr["y"].to_numpy(), te["y"].to_numpy()

    coef, se = _ols_hc0(X_tr, y_tr)

    return Fit(
        label=label,
        alpha=float(coef[0]),
        beta=float(coef[1]),
        se_beta=float(se[1]),
        t_beta=float(coef[1] / se[1]) if se[1] > 0 else np.nan,
        r2_in=_r2(y_tr, X_tr @ coef),
        r2_out=_r2(y_te, X_te @ coef),
        n_train=len(tr),
        n_test=len(te),
    )


def depth_stability(buckets: pd.DataFrame, n_bins: int = 5) -> pd.DataFrame:
    """
    CKS argue the impact coefficient scales like 1 / depth. Split buckets into
    depth quintiles and refit inside each. If the claim holds, beta falls as
    depth rises and beta * depth is roughly flat.
    """
    frame = buckets.dropna(subset=["ofi", "d_mid", "depth"]).copy()
    frame["bin"] = pd.qcut(frame["depth"], n_bins, labels=False, duplicates="drop")

    rows = []
    for b, grp in frame.groupby("bin"):
        if len(grp) < 50:
            continue
        X = np.column_stack([np.ones(len(grp)), grp["ofi"].to_numpy()])
        coef, se = _ols_hc0(X, grp["d_mid"].to_numpy())
        rows.append(
            {
                "depth_bin": int(b),
                "mean_depth": grp["depth"].mean(),
                "beta": coef[1],
                "se": se[1],
                "beta_x_depth": coef[1] * grp["depth"].mean(),
                "n": len(grp),
            }
        )
    return pd.DataFrame(rows)


def cost_check(
    buckets: pd.DataFrame,
    fit: Fit,
    tick_size: float = 0.01,
    fee_ticks: float = 0.0,
    train_frac: float = 0.7,
) -> dict:
    """
    Take the predictive fit at face value and ask whether it survives costs.

    Trade the sign of the forecast in the test block only. Gross edge per trade
    is the realised mid move in ticks, signed by the forecast. Cost per round
    trip is the spread plus fees, because you cross to get in and cross to get
    out. Net edge below zero is the expected outcome and is the finding, not a
    failure.
    """
    frame = buckets.dropna(subset=["ofi", "d_mid_fwd", "spread"]).copy()
    te = frame.iloc[int(len(frame) * train_frac) :]
    if te.empty:
        raise ValueError("empty test block")

    forecast = fit.alpha + fit.beta * te["ofi"]
    side = np.sign(forecast)
    traded = side != 0

    realised = te["d_mid_fwd"][traded]
    gross = (side[traded] * realised).mean()
    round_trip = te["spread"][traded].mean() + 2 * fee_ticks

    return {
        "n_trades": int(traded.sum()),
        "hit_rate": float((side[traded] * realised > 0).mean()),
        "gross_edge_ticks": float(gross),
        "round_trip_cost_ticks": float(round_trip),
        "net_edge_ticks": float(gross - round_trip),
        "gross_edge_currency": float(gross * tick_size),
        "net_edge_currency": float((gross - round_trip) * tick_size),
    }
