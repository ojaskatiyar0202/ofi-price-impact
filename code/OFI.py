#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 21:30:00 2026

@author: Ojas
"""

import numpy as np
import pandas as pd

def ofi_events(bid_px, bid_sz, ask_px, ask_sz):
    # Cont, Kukanov and Stoikov (2014), the per-event contribution e_n.
    # Weak inequalities on purpose: if the bid price is unchanged both bid
    # indicators fire and the term collapses to the change in resting size.
    e = np.zeros(len(bid_px))
    e[1:] = ((bid_px[1:] >= bid_px[:-1]) * bid_sz[1:]
             - (bid_px[1:] <= bid_px[:-1]) * bid_sz[:-1]
             - (ask_px[1:] <= ask_px[:-1]) * ask_sz[1:]
             + (ask_px[1:] >= ask_px[:-1]) * ask_sz[:-1])
    return e

def make_buckets(df, freq="10s", tick=0.01):
    # Sum e_n into fixed clock intervals and take the mid change in ticks.
    df = df.copy()
    df["e"] = ofi_events(df["bid_px"].to_numpy(float), df["bid_sz"].to_numpy(float),
                         df["ask_px"].to_numpy(float), df["ask_sz"].to_numpy(float))
    df["mid"] = (df["bid_px"] + df["ask_px"]) / 2
    df["depth"] = (df["bid_sz"] + df["ask_sz"]) / 2
    df["spread"] = (df["ask_px"] - df["bid_px"]) / tick

    g = df.resample(freq, on="ts")
    out = pd.DataFrame({"ofi": g["e"].sum(),
                        "mid": g["mid"].last(),
                        "depth": g["depth"].mean(),
                        "spread": g["spread"].mean(),
                        "n": g["e"].size()})
    out = out[out["n"] > 0]
    out["d_mid"] = out["mid"].diff() / tick
    out["d_mid_next"] = out["d_mid"].shift(-1)
    return out.dropna(subset=["d_mid"])

def ols(x, y):
    # Slope, intercept and White standard error on the slope.
    X = np.column_stack([np.ones(len(x)), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    resid = y - X @ b
    cov = XtX_inv @ (X.T @ np.diag(resid**2) @ X) @ XtX_inv
    return b[1], b[0], np.sqrt(cov[1, 1])

def r_squared(y, y_hat):
    ss_res = ((y - y_hat)**2).sum()
    ss_tot = ((y - y.mean())**2).sum()
    return 1 - ss_res / ss_tot

def fit(x, y, train_frac=0.7):
    # Time-ordered split, no shuffling. Out-of-sample R^2 uses the train
    # coefficients on the test block and measures against the test mean, so a
    # useless model scores at or below zero.
    d = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    cut = int(len(d) * train_frac)
    tr, te = d.iloc[:cut], d.iloc[cut:]

    beta, alpha, se = ols(tr["x"].to_numpy(), tr["y"].to_numpy())
    r2_in = r_squared(tr["y"].to_numpy(), alpha + beta * tr["x"].to_numpy())
    r2_out = r_squared(te["y"].to_numpy(), alpha + beta * te["x"].to_numpy())

    return {"beta": beta, "se": se, "t": beta / se,
            "r2_in": r2_in, "r2_out": r2_out,
            "n_train": len(tr), "n_test": len(te)}

def depth_buckets(b, n_bins=5):
    # The paper claims impact scales like 1 / depth, so beta * depth should be
    # roughly flat across depth quintiles.
    d = b.dropna(subset=["ofi", "d_mid", "depth"]).copy()
    d["bin"] = pd.qcut(d["depth"], n_bins, labels=False, duplicates="drop")

    rows = []
    for i, grp in d.groupby("bin"):
        beta, _, se = ols(grp["ofi"].to_numpy(), grp["d_mid"].to_numpy())
        rows.append({"bin": int(i), "mean_depth": grp["depth"].mean(),
                     "beta": beta, "se": se,
                     "beta_x_depth": beta * grp["depth"].mean(), "n": len(grp)})
    return pd.DataFrame(rows)

def cost_check(b, res, tick=0.01, fee_ticks=0.0, train_frac=0.7):
    # Trade the sign of the predictive forecast on the test block only. Gross
    # edge is the realised move signed by the forecast. Cost is the spread plus
    # fees, paid twice since we cross to get in and cross to get out.
    d = b.dropna(subset=["ofi", "d_mid_next", "spread"])
    te = d.iloc[int(len(d) * train_frac):]

    side = np.sign(res["beta"] * te["ofi"])
    traded = side != 0
    realised = te["d_mid_next"][traded]

    gross = (side[traded] * realised).mean()
    cost = te["spread"][traded].mean() + 2 * fee_ticks

    return {"n_trades": int(traded.sum()),
            "hit_rate": float((side[traded] * realised > 0).mean()),
            "gross_ticks": float(gross),
            "cost_ticks": float(cost),
            "net_ticks": float(gross - cost)}
