#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 21:30:00 2026

@author: Ojas
"""

import os
import numpy as np
import pandas as pd
from OFI import make_buckets, fit, depth_buckets, cost_check

def load_binance(path):
    # bookTicker archive: one row per change to the best bid or ask.
    cols = ["update_id", "best_bid_price", "best_bid_qty",
            "best_ask_price", "best_ask_qty", "transaction_time", "event_time"]
    head = pd.read_csv(path, nrows=1)
    df = pd.read_csv(path) if "best_bid_price" in head.columns else pd.read_csv(path, header=None, names=cols)

    out = pd.DataFrame({"ts": pd.to_datetime(df["transaction_time"], unit="ms"),
                        "bid_px": df["best_bid_price"].astype(float),
                        "bid_sz": df["best_bid_qty"].astype(float),
                        "ask_px": df["best_ask_price"].astype(float),
                        "ask_sz": df["best_ask_qty"].astype(float)})
    out = out.sort_values("ts")
    out = out[(out["bid_px"] < out["ask_px"]) & (out["bid_sz"] > 0) & (out["ask_sz"] > 0)]
    return out.reset_index(drop=True)

def fake_book(n=200_000, tick=0.01, seed=0):
    # A crude book for checking the code runs before real data arrives.
    # Numbers off this describe the generator, not a market.
    rng = np.random.default_rng(seed)
    bid_px, ask_px, bid_sz, ask_sz = 99.995, 100.005, 500.0, 500.0
    rows = np.empty((n, 4))

    kind = rng.choice(["add", "cancel", "market"], size=n, p=[0.45, 0.40, 0.15])
    side = rng.integers(0, 2, size=n)
    qty = rng.gamma(2.0, 60.0, size=n)

    for i in range(n):
        if kind[i] == "add":
            if side[i] == 0: bid_sz += qty[i]
            else: ask_sz += qty[i]
        elif kind[i] == "cancel":
            if side[i] == 0: bid_sz -= min(qty[i], bid_sz * 0.9)
            else: ask_sz -= min(qty[i], ask_sz * 0.9)
        else:
            if side[i] == 0: ask_sz -= qty[i]
            else: bid_sz -= qty[i]

        if ask_sz <= 0:
            ask_px += tick; bid_px += tick
            ask_sz = max(rng.gamma(2.0, 250.0), 1.0); bid_sz = max(rng.gamma(2.0, 250.0), 1.0)
        if bid_sz <= 0:
            bid_px -= tick; ask_px -= tick
            bid_sz = max(rng.gamma(2.0, 250.0), 1.0); ask_sz = max(rng.gamma(2.0, 250.0), 1.0)

        rows[i] = (bid_px, bid_sz, ask_px, ask_sz)

    gaps = rng.exponential(0.05, size=n)
    out = pd.DataFrame(rows, columns=["bid_px", "bid_sz", "ask_px", "ask_sz"])
    out.insert(0, "ts", pd.Timestamp("2026-01-05 09:30") + pd.to_timedelta(np.cumsum(gaps), unit="s"))
    return out


os.makedirs("results", exist_ok=True)

# swap this for load_binance("data/BTCUSDT-bookTicker-2026-08-15.csv") once you have the file
book = fake_book()
print(len(book), "top of book updates")

rows = []
for freq in ["1s", "10s", "30s"]:
    b = make_buckets(book, freq=freq)
    contemp = fit(b["ofi"], b["d_mid"])
    predict = fit(b["ofi"], b["d_mid_next"])
    costs = cost_check(b, predict)

    rows.append({"freq": freq, "n_buckets": len(b),
                 "contemp_r2_in": contemp["r2_in"], "contemp_r2_out": contemp["r2_out"],
                 "predict_r2_out": predict["r2_out"],
                 "gross_ticks": costs["gross_ticks"], "cost_ticks": costs["cost_ticks"],
                 "net_ticks": costs["net_ticks"]})

df = pd.DataFrame(rows)
print(df.to_string(index=False))
df.to_csv("results/ofi_by_frequency.csv", index=False)

b = make_buckets(book, freq="10s")
dq = depth_buckets(b)
print(dq.to_string(index=False))
dq.to_csv("results/depth_quintiles.csv", index=False)
