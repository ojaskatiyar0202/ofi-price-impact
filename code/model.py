#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import statsmodels.api as sm
def ofi_events(bid_px, bid_sz, ask_px, ask_sz):
    e = np.zeros(len(bid_px))
    e[1:] = ((bid_px[1:] >= bid_px[:-1]) * bid_sz[1:]
             - (bid_px[1:] <= bid_px[:-1]) * bid_sz[:-1]
             - (ask_px[1:] <= ask_px[:-1]) * ask_sz[1:]
             + (ask_px[1:] >= ask_px[:-1]) * ask_sz[:-1])
    return e





def make_buckets(df, freq="10s", tick=0.01):

    e = ofi_events(df["bid_px"].to_numpy(float),
                   df["bid_sz"].to_numpy(float),
                   df["ask_px"].to_numpy(float),
                   df["ask_sz"].to_numpy(float))
    df = df.copy()
    df["e"] = e
    df["mid"] = (df["bid_px"] + df["ask_px"]) / 2
    df["depth"] = (df["bid_sz"] + df["ask_sz"]) / 2
    df["spread"] = (df["ask_px"] - df["bid_px"]) / tick
    g = df.resample(freq, on="ts")
    out = pd.DataFrame({ "ofi":    g["e"].sum(), "mid":    g["mid"].last(), "depth":  g["depth"].mean(),
     "spread": g["spread"].mean(), "n":      g["e"].size(),}) 
    out = out[out["n"] > 0]
    out["d_mid"] = out["mid"].diff() / tick
    out["d_mid_next"] = out["d_mid"].shift(-1)
    return out.dropna(subset=["d_mid"])

def r_squared(y, y_hat):
    ss_res = ((y - y_hat)**2).sum()
    ss_tot = ((y - y.mean())**2).sum()
    return 1 - ss_res / ss_tot

def fit(x, y, train_frac=0.7):
    d = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    cut = int(len(d) * train_frac)
    train, test = d.iloc[:cut], d.iloc[cut:]
    res = sm.OLS(train["y"], sm.add_constant(train["x"])).fit(cov_type="HC0")
    alpha, beta = res.params
    standard_error = res.bse.iloc[1]
    pred = alpha + beta * test["x"]
    return {"beta": beta, "se": standard_error, "t": beta / standard_error, "r2_in": res.rsquared,
            "r2_out": r_squared(test["y"], pred), "n_train": len(train), "n_test": len(test)}

def depth_buckets(b, n_bins=5):
    d = b.dropna(subset=["ofi", "d_mid", "depth"]).copy()
    d["bin"] = pd.qcut(d["depth"], n_bins, labels=False)
    rows = []
    for i, grp in d.groupby("bin"):
        res = sm.OLS(grp["d_mid"], sm.add_constant(grp["ofi"])).fit(cov_type="HC0")
        beta = res.params.iloc[1]
        rows.append({"bin": i, "mean_depth": grp["depth"].mean(), "beta": beta,
                     "beta_x_depth": beta * grp["depth"].mean(), "n": len(grp)})
    return pd.DataFrame(rows)

def cost_check(b, res, tick=0.01, fee_ticks=0.0, train_frac=0.7):
    d = b.dropna(subset=["ofi", "d_mid_next", "spread"])
    test = d.iloc[int(len(d) * train_frac):]
    side = np.sign(res["beta"] * test["ofi"])
    traded = side != 0
    realised = test["d_mid_next"][traded]
    gross = (side[traded] * realised).mean()
    cost = test["spread"][traded].mean() + 2 * fee_ticks
    return {"n_trades": int(traded.sum()), "hit_rate": float((side[traded] * realised > 0).mean()),
            "gross_ticks": float(gross), "cost_ticks": float(cost), "net_ticks": float(gross - cost)}
